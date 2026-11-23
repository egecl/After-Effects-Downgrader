#!/usr/bin/env python3
"""
AE Project Downgrader - GUI Version
Drag & drop .aep files, select target version, click Downgrade.
Compiles to standalone .exe with PyInstaller.
"""

import sys
import os
import struct
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple, List
import queue

# ============================================================
# CORE LOGIC (same as aep_binary_downgrader.py)
# ============================================================

MAJOR_VERSION_BYTE = {
    2025: 0x60, 2024: 0x5F, 2023: 0x5E, 2022: 0x5D,
    2021: 0x5C, 2020: 0x5B, 2019: 0x5A, 2018: 0x59,
}
BYTE_TO_VERSION = {v: k for k, v in MAJOR_VERSION_BYTE.items()}

KNOWN_SIGNATURES = {
    0x60: bytes([0x60, 0x01, 0x0F, 0x08, 0x86, 0x44]),
    0x5F: bytes([0x5F, 0x05, 0x0F, 0x02, 0x86, 0x34]),
    0x5E: bytes([0x5E, 0x09, 0x0B, 0x3B, 0x06, 0x37]),
    0x5D: bytes([0x5D, 0x2B, 0x0B, 0x33, 0x06, 0x3B]),
    0x5C: bytes([0x5C, 0x00, 0x00, 0x00, 0x00, 0x00]),
    0x5B: bytes([0x5B, 0x00, 0x00, 0x00, 0x00, 0x00]),
    0x5A: bytes([0x5A, 0x00, 0x00, 0x00, 0x00, 0x00]),
}


@dataclass
class AEPInfo:
    file_path: str
    file_size: int
    rifx_offset: Optional[int] = None
    egg_offset: Optional[int] = None
    head_offset: Optional[int] = None
    head_size: Optional[int] = None
    major_version_byte: Optional[int] = None
    detected_version: Optional[int] = None
    signature: Optional[bytes] = None
    signature_known: bool = False
    is_riff: bool = False


def find_rifx_egg(data: bytes) -> Tuple[Optional[int], Optional[int]]:
    rifx_pos = data.find(b"RIFX")
    if rifx_pos >= 0:
        if rifx_pos + 12 <= len(data):
            form_type = data[rifx_pos + 8:rifx_pos + 12]
            if form_type == b"Egg!":
                return rifx_pos, rifx_pos + 8

    riff_pos = data.find(b"RIFF")
    if riff_pos >= 0:
        if riff_pos + 12 <= len(data):
            form_type = data[riff_pos + 8:riff_pos + 12]
            if form_type == b"Egg!":
                return riff_pos, riff_pos + 8

    return None, None


def find_head_chunk(data: bytes, start_offset: int) -> Tuple[Optional[int], Optional[int]]:
    search_start = start_offset + 4
    head_pos = data.find(b"head", search_start)
    if head_pos < 0:
        return None, None

    if head_pos + 8 <= len(data):
        chunk_size = struct.unpack(">I", data[head_pos + 4:head_pos + 8])[0]
        data_start = head_pos + 8
        data_end = data_start + chunk_size
        if data_end <= len(data):
            return head_pos, chunk_size

    return None, None


def analyze_aep(filepath: str) -> AEPInfo:
    with open(filepath, "rb") as f:
        data = f.read()

    info = AEPInfo(file_path=filepath, file_size=len(data))

    rifx_offset, egg_offset = find_rifx_egg(data)
    if rifx_offset is None:
        return info

    info.rifx_offset = rifx_offset
    info.egg_offset = egg_offset
    info.is_riff = data[rifx_offset:rifx_offset + 4] == b"RIFF"

    head_offset, head_size = find_head_chunk(data, egg_offset)
    if head_offset is None:
        return info

    info.head_offset = head_offset
    info.head_size = head_size

    head_data_start = head_offset + 8
    head_data = data[head_data_start:head_data_start + head_size]

    if len(head_data) >= 8:
        info.major_version_byte = head_data[1]
        info.detected_version = BYTE_TO_VERSION.get(head_data[1])
        info.signature = head_data[2:8]
        info.signature_known = head_data[1] in KNOWN_SIGNATURES

    return info


def patch_aep_version(input_path: str, output_path: str, target_year: int) -> Tuple[bool, str]:
    if target_year not in MAJOR_VERSION_BYTE:
        return False, f"Unsupported target year: {target_year}"

    target_byte = MAJOR_VERSION_BYTE[target_year]

    with open(input_path, "rb") as f:
        data = bytearray(f.read())

    info = analyze_aep(input_path)

    if info.rifx_offset is None:
        return False, "Not a valid RIFX/RIFF Egg! file"
    if info.head_offset is None:
        return False, "'head' chunk not found"
    if info.major_version_byte is None:
        return False, "Could not read major version byte"

    current_byte = info.major_version_byte
    current_version = info.detected_version

    if current_version == target_year:
        return False, f"Already target version {target_year}"

    # Patch version byte
    patch_offset = info.head_offset + 9
    data[patch_offset] = target_byte

    # Patch signature
    if target_byte in KNOWN_SIGNATURES:
        target_sig = KNOWN_SIGNATURES[target_byte]
        sig_offset = info.head_offset + 10
        data[sig_offset:sig_offset + 6] = target_sig

    with open(output_path, "wb") as f:
        f.write(data)

    return True, f"Patched to AE {target_year} (byte 0x{target_byte:02X})"


# ============================================================
# GUI
# ============================================================

class AEDowngraderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AE Project Downgrader v1.0")
        self.root.geometry("700x550")
        self.root.minsize(600, 450)

        # Set icon if available
        try:
            self.root.iconbitmap(default="")  # placeholder
        except:
            pass

        # State
        self.files_queue: List[str] = []
        self.log_queue = queue.Queue()
        self.is_processing = False
        self.has_dnd = False

        self.setup_ui()
        self.setup_drag_drop()
        self.process_log_queue()

    def setup_ui(self):
        # Style
        style = ttk.Style()
        style.theme_use('clam')

        # Main frame
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(main, text="After Effects Project Downgrader",
                          font=('Segoe UI', 14, 'bold'))
        title.pack(pady=(0, 5))

        subtitle = ttk.Label(main,
                             text="Patches RIFX header version byte — does NOT convert features",
                             font=('Segoe UI', 8), foreground='gray')
        subtitle.pack(pady=(0, 15))

        # --- File List ---
        file_frame = ttk.LabelFrame(main, text="Files to Downgrade", padding=10)
        file_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Listbox with scrollbar
        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.file_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED,
                                        font=('Consolas', 9), height=8)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                  command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=scrollbar.set)

        # File buttons
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="Add Files...",
                   command=self.add_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Add Folder...",
                   command=self.add_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Remove Selected",
                   command=self.remove_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Clear All",
                   command=self.clear_all).pack(side=tk.LEFT, padx=2)

        # Drag-drop hint
        dnd_text = "💡 Tip: Drag & drop .aep files here from Explorer" if self.has_dnd else "💡 Drag & drop requires: pip install tkinterdnd2"
        hint = ttk.Label(file_frame, text=dnd_text,
                         font=('Segoe UI', 8), foreground='gray')
        hint.pack(anchor=tk.W, pady=(5, 0))

        # --- Options ---
        opt_frame = ttk.LabelFrame(main, text="Options", padding=10)
        opt_frame.pack(fill=tk.X, pady=(0, 10))

        # Target version
        ttk.Label(opt_frame, text="Target AE Version:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.target_var = tk.StringVar(value="2023")
        target_combo = ttk.Combobox(opt_frame, textvariable=self.target_var,
                                     values=[str(y) for y in sorted(MAJOR_VERSION_BYTE.keys(), reverse=True)],
                                     state='readonly', width=10)
        target_combo.grid(row=0, column=1, sticky=tk.W)

        # Output folder
        ttk.Label(opt_frame, text="Output Folder:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.output_var = tk.StringVar(value="Same as input")
        ttk.Entry(opt_frame, textvariable=self.output_var, width=40).grid(row=1, column=1, sticky=tk.EW, pady=(10, 0))
        ttk.Button(opt_frame, text="Browse...",
                   command=self.browse_output).grid(row=1, column=2, padx=(5, 0), pady=(10, 0))

        # Options checkboxes
        self.backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="Keep original files (create _vYYYY.aep)",
                        variable=self.backup_var).grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))

        self.signature_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="Also patch signature bytes (recommended)",
                        variable=self.signature_var).grid(row=3, column=0, columnspan=3, sticky=tk.W)

        opt_frame.columnconfigure(1, weight=1)

        # --- Action Buttons ---
        action_frame = ttk.Frame(main)
        action_frame.pack(fill=tk.X, pady=(0, 10))

        self.analyze_btn = ttk.Button(action_frame, text="Analyze Only",
                                       command=self.analyze_files)
        self.analyze_btn.pack(side=tk.LEFT, padx=2)

        self.downgrade_btn = ttk.Button(action_frame, text="Downgrade",
                                         command=self.start_downgrade,
                                         style='Accent.TButton')
        self.downgrade_btn.pack(side=tk.LEFT, padx=2)

        # Progress bar
        self.progress = ttk.Progressbar(action_frame, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(action_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=5)

        # --- Log ---
        log_frame = ttk.LabelFrame(main, text="Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8,
                                                   font=('Consolas', 9),
                                                   state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Configure accent button style
        style = ttk.Style()
        style.configure('Accent.TButton', font=('Segoe UI', 10, 'bold'))

    def setup_drag_drop(self):
        # Enable drag & drop for file listbox (if tkinterdnd2 available)
        try:
            self.file_listbox.drop_target_register(tk.DND_FILES)
            self.file_listbox.dnd_bind('<<Drop>>', self.on_drop)
            self.has_dnd = True
        except AttributeError:
            self.has_dnd = False

    def on_drop(self, event):
        # Parse dropped files (Windows format: {path1} {path2} ...)
        files = self.root.tk.splitlist(event.data)
        aep_files = [f for f in files if f.lower().endswith('.aep')]
        for f in aep_files:
            if f not in self.files_queue:
                self.files_queue.append(f)
                self.file_listbox.insert(tk.END, os.path.basename(f))
        self.log(f"Added {len(aep_files)} file(s) via drag & drop")

    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Select .aep files",
            filetypes=[("After Effects Projects", "*.aep"), ("All Files", "*.*")]
        )
        for f in files:
            if f not in self.files_queue:
                self.files_queue.append(f)
                self.file_listbox.insert(tk.END, os.path.basename(f))
        self.log(f"Added {len(files)} file(s)")

    def add_folder(self):
        folder = filedialog.askdirectory(title="Select folder with .aep files")
        if folder:
            count = 0
            for f in Path(folder).glob("*.aep"):
                f_str = str(f)
                if f_str not in self.files_queue:
                    self.files_queue.append(f_str)
                    self.file_listbox.insert(tk.END, f.name)
                    count += 1
            self.log(f"Added {count} file(s) from folder")

    def remove_selected(self):
        selection = list(self.file_listbox.curselection())
        for idx in reversed(selection):
            self.file_listbox.delete(idx)
            del self.files_queue[idx]

    def clear_all(self):
        self.file_listbox.delete(0, tk.END)
        self.files_queue.clear()

    def browse_output(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_var.set(folder)

    def analyze_files(self):
        if not self.files_queue:
            messagebox.showwarning("No Files", "Add .aep files first")
            return

        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

        for f in self.files_queue:
            self.analyze_single(f)

    def analyze_single(self, filepath):
        info = analyze_aep(filepath)
        name = os.path.basename(filepath)

        self.log(f"\n=== {name} ===")
        self.log(f"  Size: {info.file_size:,} bytes")
        self.log(f"  Format: {'RIFF (big-endian)' if info.is_riff else 'RIFX (little-endian)'}")
        self.log(f"  RIFX/RIFF header: {f'0x{info.rifx_offset:X}' if info.rifx_offset else 'NOT FOUND'}")
        self.log(f"  head chunk: {f'0x{info.head_offset:X} (size: {info.head_size})' if info.head_offset else 'NOT FOUND'}")
        if info.major_version_byte:
            self.log(f"  Version byte: 0x{info.major_version_byte:02X}")
            self.log(f"  Detected AE: {info.detected_version or 'Unknown'}")
            self.log(f"  Signature: {info.signature.hex().upper() if info.signature else 'N/A'} "
                     f"{'(known)' if info.signature_known else '(unknown)'}")
        else:
            self.log(f"  Version byte: NOT FOUND")

    def start_downgrade(self):
        if not self.files_queue:
            messagebox.showwarning("No Files", "Add .aep files first")
            return

        if self.is_processing:
            return

        target_year = int(self.target_var.get())
        output_folder = self.output_var.get()
        if output_folder == "Same as input":
            output_folder = None

        self.is_processing = True
        self.downgrade_btn.config(state=tk.DISABLED)
        self.analyze_btn.config(state=tk.DISABLED)
        self.progress['maximum'] = len(self.files_queue)
        self.progress['value'] = 0

        thread = threading.Thread(target=self.downgrade_worker,
                                   args=(target_year, output_folder),
                                   daemon=True)
        thread.start()

    def downgrade_worker(self, target_year: int, output_folder: Optional[str]):
        success_count = 0
        fail_count = 0

        for i, filepath in enumerate(self.files_queue):
            self.root.after(0, lambda: self.status_var.set(f"Processing {i+1}/{len(self.files_queue)}..."))

            try:
                if output_folder:
                    out_path = os.path.join(output_folder,
                                             f"{Path(filepath).stem}_v{target_year}.aep")
                else:
                    out_path = f"{os.path.splitext(filepath)[0]}_v{target_year}.aep"

                success, msg = patch_aep_version(filepath, out_path, target_year)

                if success:
                    success_count += 1
                    self.log_queue.put(("success", filepath, msg))
                else:
                    fail_count += 1
                    self.log_queue.put(("error", filepath, msg))

            except Exception as e:
                fail_count += 1
                self.log_queue.put(("error", filepath, str(e)))

            self.root.after(0, lambda v=i+1: self.progress.config(value=v))

        self.root.after(0, lambda: self.finish_downgrade(success_count, fail_count))

    def finish_downgrade(self, success: int, failed: int):
        self.is_processing = False
        self.downgrade_btn.config(state=tk.NORMAL)
        self.analyze_btn.config(state=tk.NORMAL)
        self.status_var.set(f"Done: {success} success, {failed} failed")
        self.log(f"\n=== Complete: {success} succeeded, {failed} failed ===")

        if failed > 0:
            messagebox.showwarning("Done with Errors",
                                   f"{success} file(s) downgraded\n{failed} file(s) failed\n\nCheck log for details")
        else:
            messagebox.showinfo("Success", f"All {success} file(s) downgraded to AE {self.target_var.get()}!")

    def process_log_queue(self):
        try:
            while True:
                level, filepath, msg = self.log_queue.get_nowait()
                name = os.path.basename(filepath)
                if level == "success":
                    self.log(f"  ✓ {name}: {msg}")
                else:
                    self.log(f"  ✗ {name}: {msg}")
        except queue.Empty:
            pass
        self.root.after(100, self.process_log_queue)

    def log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)


def main():
    # Check for tkinterdnd2 (drag & drop support)
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except ImportError:
        root = tk.Tk()
        # Note printed in GUI instead

    app = AEDowngraderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()