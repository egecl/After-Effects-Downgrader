#!/usr/bin/env python3
"""
AE Project Downgrader - Modern CustomTkinter GUI
Drag & drop .aep files, select target version, click Downgrade.
Compiles to standalone .exe with PyInstaller.
"""

import sys
import os
import struct
import threading
import queue
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple, List

import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES

# ============================================================
# LANGUAGE SYSTEM
# ============================================================

TRANSLATIONS = {
    "en": {
        # Header
        "app_title": "AE Project Downgrader",
        "subtitle": "Patch RIFX header version - open newer projects in older AE",
        # Drop zone
        "drop_title": "Drop .aep files here",
        "drop_subtitle": "or click to browse",
        # File list
        "files_title": "Files to Downgrade",
        "clear_all": "Clear All",
        "file_count": "{count} file(s)",
        # Options
        "options_title": "Options",
        "target_version": "Target AE Version",
        "output_folder": "Output Folder",
        "same_as_input": "Same as input folder",
        "browse": "Browse",
        "keep_backup": "Keep original files (create _vYYYY.aep)",
        "patch_signature": "Patch signature bytes (recommended)",
        # Actions
        "analyze": "Analyze Files",
        "downgrade": "Downgrade Projects",
        "processing": "Processing...",
        "status_ready": "Ready",
        "status_processing": "Processing {current}/{total}...",
        "status_done": "Done: {success} success, {failed} failed",
        # Log
        "log_title": "Activity Log",
        "log_entries": "{count} entries",
        # Analysis
        "no_files_analyze": "No files to analyze",
        "no_files_downgrade": "No files to downgrade",
        "starting_analysis": "Starting analysis...",
        "analyzing": "Analyzing: {name}",
        "start_downgrade": "Starting downgrade to AE {year}...",
        "complete_header": "Complete: {success} succeeded, {failed} failed",
        "failed_details": "{failed} file(s) failed - check log for details",
        "all_success": "All {success} file(s) downgraded to AE {year}!",
        # Analysis details
        "file_size": "Size: {size:,} bytes",
        "file_format": "Format: {format} (Egg!)",
        "version_byte": "Version byte: 0x{byte:02X}",
        "detected_ae": "Detected AE: {version}",
        "detected_ae_unknown": "Detected AE: Unknown",
        "signature": "Signature: {sig} ({status})",
        "version_not_found": "Version byte: NOT FOUND",
        # Dialogs
        "done_with_errors_title": "Done with Errors",
        "done_with_errors_msg": "{success} file(s) downgraded\n{failed} file(s) failed\n\nCheck log for details",
        "success_title": "Success",
        "success_msg": "All {success} file(s) downgraded to AE {year}!",
        # Theme
        "dark_mode": "Dark Mode",
        "light_mode": "Light Mode",
        # Language
        "language": "Language",
    },
    "tr": {
        # Header
        "app_title": "AE Proje Sürümü Düşürücü",
        "subtitle": "RIFX versiyon numarası değiştir - daha yeni projeleri eski AE'de aç",
        # Drop zone
        "drop_title": ".aep dosyalarını buraya sürükleyin",
        "drop_subtitle": "veya gözatmak için tıklayın",
        # File list
        "files_title": "Acılacak Dosyalar",
        "clear_all": "Temizle",
        "file_count": "{count} dosya",
        # Options
        "options_title": "Seçenekler",
        "target_version": "Hedef AE Versiyonu",
        "output_folder": "Çikti Klasörü",
        "same_as_input": "Girdi klasörü ile aynı",
        "browse": "Gözat",
        "keep_backup": "Orijinal dosyaları koru (_vYYYY.aep oluştur)",
        "patch_signature": "İmza baytlarını değiştir (tavsiye edilir)",
        # Actions
        "analyze": "Analiz Et",
        "downgrade": "Versiyon Düşür",
        "processing": "İşleniyor...",
        "status_ready": "Hazır",
        "status_processing": "{current}/{total} işleniyor...",
        "status_done": "{success} başarılı, {failed} başarısız",
        # Log
        "log_title": "Aktivite Günlüğü",
        "log_entries": "{count} kayıt",
        # Analysis
        "no_files_analyze": "Analiz edilecek dosya yok",
        "no_files_downgrade": "Düşürülecek dosya yok",
        "starting_analysis": "Analiz başlıyor...",
        "analyzing": "Analiz ediliyor: {name}",
        "start_downgrade": "AE {year} versiyonuna düşürülüyor...",
        "complete_header": "Tamamlandı: {success} başarılı, {failed} başarısız",
        "failed_details": "{failed} dosya başarısız - detaylar için logu kontrol edin",
        "all_success": "Tüm {success} dosya AE {year}'ye düşürüldü!",
        # Analysis details
        "file_size": "Boyut: {size:,} bayt",
        "file_format": "Format: {format} (Egg!)",
        "version_byte": "Versiyon baytı: 0x{byte:02X}",
        "detected_ae": "Tespit edilen AE: {version}",
        "detected_ae_unknown": "Tespit edilen AE: Bilinmiyor",
        "signature": "İmza: {sig} ({status})",
        "version_not_found": "Versiyon baytı: BULUNAMADI",
        # Dialogs
        "done_with_errors_title": "Hatalarla Tamamlandı",
        "done_with_errors_msg": "{success} dosya düşürüldü\n{failed} dosya başarısız\n\nDetaylar için logu kontrol edin",
        "success_title": "Başarılı",
        "success_msg": "Tüm {success} dosya AE {year}'ye düşürüldü!",
        # Theme
        "dark_mode": "Karanlık Mod",
        "light_mode": "Aydınlık Mod",
        # Language
        "language": "Dil",
    },
}

DEFAULT_LANG = "en"


class LanguageManager:
    def __init__(self, default_lang=DEFAULT_LANG):
        self.current_lang = default_lang
        self.callbacks = []

    def set_language(self, lang_code: str):
        if lang_code in TRANSLATIONS:
            self.current_lang = lang_code
            for cb in self.callbacks:
                cb(lang_code)

    def get(self, key: str, **kwargs) -> str:
        lang = TRANSLATIONS.get(self.current_lang, TRANSLATIONS[DEFAULT_LANG])
        text = lang.get(key, TRANSLATIONS[DEFAULT_LANG].get(key, key))
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

    def register(self, callback):
        self.callbacks.append(callback)

    def get_available_languages(self):
        return list(TRANSLATIONS.keys())


LANG = LanguageManager()


def t(key: str, **kwargs) -> str:
    """Shortcut for translation."""
    return LANG.get(key, **kwargs)


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
# CUSTOM UI COMPONENTS
# ============================================================

class AnimatedProgressBar(ctk.CTkProgressBar):
    """Animated progress bar with smooth transitions."""

    def __init__(self, master, height=8, corner_radius=4, **kwargs):
        super().__init__(master, height=height, corner_radius=corner_radius, **kwargs)
        self._target_value = 0
        self._animating = False
        self.configure(mode="determinate")

    def set_progress(self, value: float, animate=True):
        """Set progress value (0.0 to 1.0) with optional animation."""
        self._target_value = max(0.0, min(1.0, value))
        if animate and not self._animating:
            self._animate()
        else:
            self.set(self._target_value)

    def _animate(self):
        self._animating = True

        def step():
            current = self.get()
            diff = self._target_value - current
            if abs(diff) < 0.005:
                self.set(self._target_value)
                self._animating = False
                return
            self.set(current + diff * 0.15)
            self.after(16, step)

        step()


class DraggableDropZone(ctk.CTkFrame):
    """Animated drag-and-drop zone with visual feedback."""

    def __init__(self, master, on_drop_callback, **kwargs):
        super().__init__(master, **kwargs)
        self.on_drop_callback = on_drop_callback

        self._is_drag_over = False
        self._file_count = 0

        self.configure(corner_radius=16, border_width=2)
        self._update_border_color()

        # Content
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Icon
        self.icon_label = ctk.CTkLabel(
            self.content_frame,
            text="\U0001F4C1",
            font=("Segoe UI Emoji", 48),
        )
        self.icon_label.pack(pady=(0, 12))

        # Main text
        self.main_label = ctk.CTkLabel(
            self.content_frame,
            text=t("drop_title"),
            font=("Segoe UI", 18, "bold"),
        )
        self.main_label.pack()

        # Sub text
        self.sub_label = ctk.CTkLabel(
            self.content_frame,
            text=t("drop_subtitle"),
            font=("Segoe UI", 12),
            text_color="gray",
        )
        self.sub_label.pack(pady=(4, 0))

        # File count badge
        self.badge = ctk.CTkLabel(
            self.content_frame,
            text="",
            font=("Segoe UI", 11, "bold"),
            text_color="#00D4AA",
            fg_color=("green", "darkgreen"),
            corner_radius=12,
            height=24,
        )

        # Register for drag and drop
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self._on_drop)
        self.dnd_bind("<<DragEnter>>", self._on_drag_enter)
        self.dnd_bind("<<DragLeave>>", self._on_drag_leave)

        # Click to browse
        self.bind("<Button-1>", self._on_click)
        self.content_frame.bind("<Button-1>", self._on_click)
        self.icon_label.bind("<Button-1>", self._on_click)
        self.main_label.bind("<Button-1>", self._on_click)
        self.sub_label.bind("<Button-1>", self._on_click)

        # Register for language changes
        LANG.register(self._on_language_change)

    def _on_language_change(self, lang_code):
        self.main_label.configure(text=t("drop_title"))
        self.sub_label.configure(text=t("drop_subtitle"))

    def _update_border_color(self):
        if self._is_drag_over:
            self.configure(border_color="#00D4AA")
        else:
            self.configure(border_color=("gray70", "gray30"))

    def _on_drag_enter(self, event):
        self._is_drag_over = True
        self._update_border_color()

    def _on_drag_leave(self, event):
        self._is_drag_over = False
        self._update_border_color()

    def _on_drop(self, event):
        self._is_drag_over = False
        self._update_border_color()

        files = self.tk.splitlist(event.data)
        aep_files = [f for f in files if f.lower().endswith(".aep")]
        if aep_files:
            self.on_drop_callback(aep_files)

    def _on_click(self, event):
        files = filedialog.askopenfilenames(
            title=t("browse"),
            filetypes=[(t("drop_title")[:20], "*.aep"), (t("drop_title")[:20], "*.*")]
        )
        if files:
            self.on_drop_callback(list(files))

    def set_file_count(self, count: int):
        self._file_count = count
        if count > 0:
            self.badge.configure(text=t("file_count", count=count))
            self.badge.pack(pady=(16, 0))
        else:
            self.badge.pack_forget()


class FileListItem(ctk.CTkFrame):
    """Individual file item in the list with animated status."""

    def __init__(self, master, filepath: str, index: int, on_remove_callback, **kwargs):
        super().__init__(master, **kwargs)
        self.filepath = filepath
        self.index = index
        self.on_remove_callback = on_remove_callback

        self.configure(height=56, corner_radius=8, fg_color="transparent")

        # Left: file info
        self.left_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.left_frame.pack(side="left", fill="y", padx=12, pady=8)

        # Status indicator
        self.status_indicator = ctk.CTkLabel(
            self.left_frame,
            text="⏳",
            font=("Segoe UI Emoji", 16),
        )
        self.status_indicator.pack(side="left", padx=(0, 12))

        # File name and path
        self.name_label = ctk.CTkLabel(
            self.left_frame,
            text=Path(filepath).name,
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        )
        self.name_label.pack(anchor="w")

        self.path_label = ctk.CTkLabel(
            self.left_frame,
            text=str(Path(filepath).parent),
            font=("Segoe UI", 10),
            text_color="gray",
            anchor="w",
        )
        self.path_label.pack(anchor="w")

        # Right: remove button
        self.remove_btn = ctk.CTkButton(
            self,
            text="✕",
            width=32,
            height=32,
            corner_radius=16,
            font=("Segoe UI", 11),
            fg_color="transparent",
            text_color="gray",
            hover_color=("red", "darkred"),
            command=self._on_remove,
        )
        self.remove_btn.pack(side="right", padx=12)

        # Hover effect
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.name_label.bind("<Enter>", self._on_enter)
        self.name_label.bind("<Leave>", self._on_leave)
        self.path_label.bind("<Enter>", self._on_enter)
        self.path_label.bind("<Leave>", self._on_leave)

    def _on_enter(self, event):
        self.configure(fg_color=("gray85", "gray20"))

    def _on_leave(self, event):
        self.configure(fg_color="transparent")

    def _on_remove(self):
        self.on_remove_callback(self.index)

    def set_status(self, status: str):
        status_map = {
            "pending": ("⏳", "gray"),
            "processing": ("\U0001F504", "#3B82F6"),
            "success": ("✓", "#10B981"),
            "error": ("✗", "#EF4444"),
        }
        emoji, color = status_map.get(status, ("⏳", "gray"))
        self.status_indicator.configure(text=emoji)
        self.status_indicator.configure(text_color=color)


class LogPanel(ctk.CTkFrame):
    """Log panel with color-coded entries and auto-scroll."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.entries = []
        self._max_entries = 1000

        self.configure(corner_radius=12)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 8))

        self.log_title = ctk.CTkLabel(
            header,
            text=t("log_title"),
            font=("Segoe UI", 14, "bold"),
        )
        self.log_title.pack(side="left")

        self.count_label = ctk.CTkLabel(
            header,
            text=t("log_entries", count=0),
            font=("Segoe UI", 10),
            text_color="gray",
        )
        self.count_label.pack(side="right")

        # Log display
        self.textbox = ctk.CTkTextbox(
            self,
            font=("Consolas", 10),
            wrap="word",
            corner_radius=8,
        )
        self.textbox.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.textbox.configure(state="disabled")

        # Configure tags - use simple color strings
        self.textbox.tag_config("timestamp", foreground="gray50")
        self.textbox.tag_config("info", foreground="gray")
        self.textbox.tag_config("success", foreground="green")
        self.textbox.tag_config("error", foreground="red")
        self.textbox.tag_config("warning", foreground="orange")
        self.textbox.tag_config("header", foreground="#00D4AA")

        # Register for language changes
        LANG.register(self._on_language_change)

    def _on_language_change(self, lang_code):
        self.log_title.configure(text=t("log_title"))
        self.count_label.configure(text=t("log_entries", count=len(self.entries)))

    def add_entry(self, message: str, level: str = "info"):
        self.entries.append(message)
        if len(self.entries) > self._max_entries:
            self.entries.pop(0)

        self.textbox.configure(state="normal")
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.textbox.insert("end", f"[{timestamp}] ", "timestamp")
        self.textbox.insert("end", f"{message}\n", level)
        self.textbox.configure(state="disabled")
        self.textbox.see("end")
        self.count_label.configure(text=t("log_entries", count=len(self.entries)))

    def clear(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
        self.entries.clear()
        self.count_label.configure(text=t("log_entries", count=0))


class ModernAEDowngraderGUI:
    """Main application class with modern CustomTkinter UI."""

    def __init__(self):
        # Initialize CustomTkinter
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("green")

        # Create root with drag & drop support
        self.root = TkinterDnD.Tk()
        self.root.title(t("app_title"))
        self.root.geometry("900x720")
        self.root.minsize(800, 600)

        # Set icon if available
        try:
            self.root.iconbitmap("icon.ico")
        except Exception:
            pass

        # State
        self.files_queue: List[str] = []
        self.log_queue = queue.Queue()
        self.is_processing = False
        self.processing_index = -1

        # UI Components
        self.drop_zone = None
        self.file_list_frame = None
        self.target_var = None
        self.target_selector = None
        self.output_var = None
        self.backup_var = None
        self.signature_var = None
        self.downgrade_btn = None
        self.analyze_btn = None
        self.progress_bar = None
        self.status_label = None
        self.log_panel = None
        self.theme_switch = None
        self.lang_selector = None
        self.subtitle_label = None
        self.files_title_label = None
        self.clear_btn = None
        self.options_title_label = None
        self.target_label = None
        self.output_label = None
        self.browse_btn = None
        self.backup_switch = None
        self.signature_switch = None

        self.setup_ui()
        self.process_log_queue()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        main = ctk.CTkScrollableFrame(self.root, corner_radius=0)
        main.pack(fill="both", expand=True)
        main._parent_canvas.configure(highlightthickness=0)

        self._build_header(main)
        self._build_drop_zone(main)
        self._build_file_list(main)
        self._build_options(main)
        self._build_actions(main)
        self._build_log(main)

    def _build_header(self, parent):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left")

        ctk.CTkLabel(
            title_frame,
            text=t("app_title"),
            font=("Segoe UI", 28, "bold"),
        ).pack(anchor="w")

        self.subtitle_label = ctk.CTkLabel(
            title_frame,
            text=t("subtitle"),
            font=("Segoe UI", 12),
            text_color="gray",
        )
        self.subtitle_label.pack(anchor="w")

        # Language selector
        self.lang_var = ctk.StringVar(value=LANG.current_lang)
        self.lang_selector = ctk.CTkComboBox(
            header,
            values=["en", "tr"],
            variable=self.lang_var,
            width=60,
            font=("Segoe UI", 10),
            corner_radius=8,
            command=self._on_language_selected,
        )
        self.lang_selector.pack(side="right", padx=(10, 0))

        # Theme toggle
        self.theme_switch = ctk.CTkSwitch(
            header,
            text=t("dark_mode"),
            font=("Segoe UI", 11),
            command=self._toggle_theme,
            progress_color="#00D4AA",
        )
        self.theme_switch.pack(side="right", padx=10)

        is_dark = ctk.get_appearance_mode() == "Dark"
        if is_dark:
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()

    def _on_language_selected(self, lang_code):
        LANG.set_language(lang_code)
        self._on_global_language_change(lang_code)

    def _on_global_language_change(self, lang_code):
        self.root.title(t("app_title"))
        self.subtitle_label.configure(text=t("subtitle"))
        self.theme_switch.configure(text=t("light_mode") if self.theme_switch.get() else t("dark_mode"))
        self.drop_zone._on_language_change(lang_code)
        self.log_panel._on_language_change(lang_code)
        self._refresh_all_texts()

    def _refresh_all_texts(self):
        # File list
        self.files_title_label.configure(text=t("files_title"))
        self.clear_btn.configure(text=t("clear_all"))
        self.file_count_label.configure(text=t("file_count", count=len(self.files_queue)))

        # Options
        self.options_title_label.configure(text=t("options_title"))
        self.target_label.configure(text=t("target_version"))
        self.output_label.configure(text=t("output_folder"))
        self.output_entry.configure(state="normal")
        self.output_entry.configure(state="readonly")
        if self._output_same_as_input:
            self.output_var.set(t("same_as_input"))
        self.browse_btn.configure(text=t("browse"))
        self.backup_switch.configure(text=t("keep_backup"))
        self.signature_switch.configure(text=t("patch_signature"))

        # Actions
        self.analyze_btn.configure(text=t("analyze"))
        self.downgrade_btn.configure(text=t("downgrade"))
        self.status_label.configure(text=t("status_ready") if not self.is_processing else t("status_processing", current=self.processing_index + 1 if self.processing_index >= 0 else 1, total=len(self.files_queue)))

        # Log
        self.log_panel._on_language_change(LANG.current_lang)

    def _toggle_theme(self):
        is_dark = self.theme_switch.get()
        ctk.set_appearance_mode("dark" if is_dark else "light")
        self.theme_switch.configure(text=t("light_mode") if is_dark else t("dark_mode"))

    def _build_drop_zone(self, parent):
        self.drop_zone = DraggableDropZone(
            parent,
            on_drop_callback=self._on_files_dropped,
            fg_color=("gray95", "gray10"),
        )
        self.drop_zone.pack(fill="x", pady=(0, 20))

    def _build_file_list(self, parent):
        section = ctk.CTkFrame(parent, corner_radius=12)
        section.pack(fill="x", pady=(0, 20))

        header = ctk.CTkFrame(section, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))

        self.files_title_label = ctk.CTkLabel(
            header,
            text=t("files_title"),
            font=("Segoe UI", 14, "bold"),
        )
        self.files_title_label.pack(side="left")

        self.file_count_label = ctk.CTkLabel(
            header,
            text=t("file_count", count=0),
            font=("Segoe UI", 12),
            text_color="gray",
        )
        self.file_count_label.pack(side="right")

        self.clear_btn = ctk.CTkButton(
            header,
            text=t("clear_all"),
            width=72,
            height=24,
            font=("Segoe UI", 10),
            corner_radius=6,
            fg_color="transparent",
            text_color=("red", "red"),
            hover_color=("pink", "darkred"),
            command=self._clear_all_files,
        )
        self.clear_btn.pack(side="right", padx=(0, 8))

        self.file_list_frame = ctk.CTkScrollableFrame(
            section,
            height=180,
            corner_radius=8,
            fg_color=("gray90", "gray15"),
        )
        self.file_list_frame.pack(fill="x", padx=16, pady=(0, 16))

    def _build_options(self, parent):
        section = ctk.CTkFrame(parent, corner_radius=12)
        section.pack(fill="x", pady=(0, 20))

        self.options_title_label = ctk.CTkLabel(
            section,
            text=t("options_title"),
            font=("Segoe UI", 14, "bold"),
        )
        self.options_title_label.pack(anchor="w", padx=16, pady=(16, 12))

        grid = ctk.CTkFrame(section, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 16))
        grid.columnconfigure(1, weight=1)

        # Target Version
        self.target_label = ctk.CTkLabel(
            grid,
            text=t("target_version"),
            font=("Segoe UI", 12),
        )
        self.target_label.grid(row=0, column=0, sticky="w", pady=12)

        self.target_var = ctk.StringVar(value="2023")
        self.target_selector = ctk.CTkSegmentedButton(
            grid,
            values=["2025", "2024", "2023", "2022", "2021", "2020", "2019"],
            variable=self.target_var,
            font=("Segoe UI", 11),
            selected_color="#00D4AA",
            unselected_color=("gray80", "gray30"),
            text_color=("black", "white"),
            corner_radius=8,
            height=36,
        )
        self.target_selector.grid(row=0, column=1, sticky="ew", padx=(12, 0))

        # Divider
        self._add_divider(grid, 1)

        # Output Folder
        self.output_label = ctk.CTkLabel(
            grid,
            text=t("output_folder"),
            font=("Segoe UI", 12),
        )
        self.output_label.grid(row=2, column=0, sticky="w", pady=12)

        output_frame = ctk.CTkFrame(grid, fg_color="transparent")
        output_frame.grid(row=2, column=1, sticky="ew", padx=(12, 0))
        output_frame.columnconfigure(0, weight=1)

        self._output_same_as_input = True
        self.output_var = ctk.StringVar(value=t("same_as_input"))
        self.output_entry = ctk.CTkEntry(
            output_frame,
            textvariable=self.output_var,
            font=("Segoe UI", 11),
            height=36,
            corner_radius=8,
            state="readonly",
        )
        self.output_entry.grid(row=0, column=0, sticky="ew")

        self.browse_btn = ctk.CTkButton(
            output_frame,
            text=t("browse"),
            width=72,
            height=36,
            font=("Segoe UI", 11),
            corner_radius=8,
            command=self._browse_output,
        )
        self.browse_btn.grid(row=0, column=1, padx=(8, 0))

        # Divider
        self._add_divider(grid, 3)

        # Switches
        switches_frame = ctk.CTkFrame(grid, fg_color="transparent")
        switches_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=8)

        self.backup_var = ctk.BooleanVar(value=True)
        self.backup_switch = ctk.CTkSwitch(
            switches_frame,
            text=t("keep_backup"),
            variable=self.backup_var,
            font=("Segoe UI", 11),
            progress_color="#00D4AA",
        )
        self.backup_switch.pack(anchor="w", pady=4)

        self.signature_var = ctk.BooleanVar(value=True)
        self.signature_switch = ctk.CTkSwitch(
            switches_frame,
            text=t("patch_signature"),
            variable=self.signature_var,
            font=("Segoe UI", 11),
            progress_color="#00D4AA",
        )
        self.signature_switch.pack(anchor="w", pady=4)

    def _add_divider(self, parent, row):
        div = ctk.CTkFrame(parent, height=1, fg_color=("gray70", "gray30"))
        div.grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)

    def _build_actions(self, parent):
        section = ctk.CTkFrame(parent, corner_radius=12)
        section.pack(fill="x", pady=(0, 20))

        content = ctk.CTkFrame(section, fg_color="transparent")
        content.pack(fill="x", padx=16, pady=16)

        self.analyze_btn = ctk.CTkButton(
            content,
            text=t("analyze"),
            height=44,
            font=("Segoe UI", 12),
            corner_radius=10,
            fg_color=("gray80", "gray30"),
            text_color=("black", "white"),
            hover_color=("gray70", "gray40"),
            command=self._analyze_files,
        )
        self.analyze_btn.pack(side="left", padx=(0, 12))

        self.downgrade_btn = ctk.CTkButton(
            content,
            text=t("downgrade"),
            height=44,
            font=("Segoe UI", 13, "bold"),
            corner_radius=10,
            fg_color="#00D4AA",
            text_color="darkgreen",
            hover_color="#00B896",
            command=self._start_downgrade,
        )
        self.downgrade_btn.pack(side="left", padx=(0, 12))

        self.progress_bar = AnimatedProgressBar(content, height=6)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 12))

        self.status_label = ctk.CTkLabel(
            content,
            text=t("status_ready"),
            font=("Segoe UI", 11),
            text_color="gray",
        )
        self.status_label.pack(side="left")

    def _build_log(self, parent):
        self.log_panel = LogPanel(parent, height=180)
        self.log_panel.pack(fill="both", expand=True)

    # ============================================================
    # Event Handlers
    # ============================================================

    def _on_files_dropped(self, files: List[str]):
        added_count = 0
        for f in files:
            if f not in self.files_queue:
                self.files_queue.append(f)
                self._add_file_to_list(f)
                added_count += 1

        self.drop_zone.set_file_count(len(self.files_queue))
        self.file_count_label.configure(text=t("file_count", count=len(self.files_queue)))

        if added_count > 0:
            self.log_panel.add_entry(f"Added {added_count} file(s)", "success")
            self.status_label.configure(text=t("status_ready"))

    def _add_file_to_list(self, filepath: str):
        index = len(self.files_queue) - 1
        item = FileListItem(
            self.file_list_frame,
            filepath,
            index,
            on_remove_callback=self._remove_file,
            fg_color="transparent",
        )
        item.pack(fill="x", padx=8, pady=4)

    def _remove_file(self, index: int):
        if 0 <= index < len(self.files_queue):
            self.files_queue.pop(index)
            self._rebuild_file_list()
            self.drop_zone.set_file_count(len(self.files_queue))
            self.file_count_label.configure(text=t("file_count", count=len(self.files_queue)))

    def _clear_all_files(self):
        self.files_queue.clear()
        self._rebuild_file_list()
        self.drop_zone.set_file_count(0)
        self.file_count_label.configure(text=t("file_count", count=0))
        self._output_same_as_input = True
        self.output_var.set(t("same_as_input"))
        self.log_panel.add_entry("Cleared all files", "info")

    def _rebuild_file_list(self):
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        for i, f in enumerate(self.files_queue):
            item = FileListItem(
                self.file_list_frame,
                f,
                i,
                on_remove_callback=self._remove_file,
                fg_color="transparent",
            )
            item.pack(fill="x", padx=8, pady=4)

    def _browse_output(self):
        folder = filedialog.askdirectory(title=t("browse"))
        if folder:
            self._output_same_as_input = False
            self.output_var.set(folder)

    def _analyze_files(self):
        if not self.files_queue:
            self.log_panel.add_entry(t("no_files_analyze"), "warning")
            return

        self.log_panel.clear()
        self.log_panel.add_entry(t("starting_analysis"), "info")

        def analyze_thread():
            for filepath in self.files_queue:
                self.root.after(0, lambda f=filepath: self.log_panel.add_entry(f"Analyzing: {Path(f).name}", "info"))
                info = analyze_aep(filepath)
                name = Path(filepath).name
                self.root.after(0, lambda n=name, i=info: self._log_analysis(n, i))

        threading.Thread(target=analyze_thread, daemon=True).start()

    def _log_analysis(self, name: str, info: AEPInfo):
        self.log_panel.add_entry(f"=== {name} ===", "header")
        self.log_panel.add_entry(f"  Size: {info.file_size:,} bytes", "info")
        self.log_panel.add_entry(f"  Format: {'RIFF' if info.is_riff else 'RIFX'} (Egg!)", "info")

        if info.major_version_byte:
            self.log_panel.add_entry(f"  Version byte: 0x{info.major_version_byte:02X}", "info")
            self.log_panel.add_entry(
                f"Detected AE: {info.detected_version or 'Unknown'}",
                "success" if info.detected_version else "warning"
            )
            self.log_panel.add_entry(
                f"  Signature: {info.signature.hex().upper() if info.signature else 'N/A'} {'(known)' if info.signature_known else '(unknown)'}",
                "success" if info.signature_known else "warning"
            )
        else:
            self.log_panel.add_entry("  Version byte: NOT FOUND", "error")

    def _start_downgrade(self):
        if not self.files_queue:
            self.log_panel.add_entry(t("no_files_downgrade"), "warning")
            return

        if self.is_processing:
            return

        target_year = int(self.target_var.get())
        if self._output_same_as_input:
            output_folder = None
        else:
            output_folder = self.output_var.get()

        self.is_processing = True

        self.downgrade_btn.configure(state="disabled", text=t("processing"))
        self.analyze_btn.configure(state="disabled")
        self.progress_bar.set_progress(0)
        self.status_label.configure(text=t("status_processing", current=1, total=len(self.files_queue)))

        self.log_panel.add_entry(f"Starting downgrade to AE {target_year}...", "header")

        self.downgrade_thread = threading.Thread(
            target=self._downgrade_worker,
            args=(target_year, output_folder),
            daemon=True
        )
        self.downgrade_thread.start()

    def _downgrade_worker(self, target_year: int, output_folder: Optional[str]):
        success_count = 0
        fail_count = 0
        self.processing_index = -1

        for i, filepath in enumerate(self.files_queue):
            self.processing_index = i
            self.root.after(0, lambda idx=i, total=len(self.files_queue): self._update_progress(idx, total))
            self.root.after(0, lambda f=filepath: self._set_file_status(f, "processing"))

            try:
                if output_folder:
                    out_path = os.path.join(output_folder, f"{Path(filepath).stem}_v{target_year}.aep")
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

        self.root.after(0, lambda: self._finish_downgrade(success_count, fail_count))

    def _update_progress(self, current: int, total: int):
        self.progress_bar.set_progress((current + 1) / total)
        self.status_label.configure(text=t("status_processing", current=current + 1, total=total))

    def _set_file_status(self, filepath: str, status: str):
        index = self.files_queue.index(filepath) if filepath in self.files_queue else -1
        if index >= 0:
            for widget in self.file_list_frame.winfo_children():
                if isinstance(widget, FileListItem) and widget.index == index:
                    widget.set_status(status)
                    break

    def _finish_downgrade(self, success: int, failed: int):
        self.is_processing = False
        self.processing_index = -1

        self.downgrade_btn.configure(state="normal", text=t("downgrade"))
        self.analyze_btn.configure(state="normal")
        self.status_label.configure(text=t("status_done", success=success, failed=failed))

        for widget in self.file_list_frame.winfo_children():
            if isinstance(widget, FileListItem):
                if widget.status_indicator.cget("text") == "\U0001F504":
                    widget.set_status("pending")

        self.log_panel.add_entry(f"Complete: {success} succeeded, {failed} failed", "header")

        if failed > 0:
            self.log_panel.add_entry(f"{failed} file(s) failed - check log for details", "error")
            messagebox.showwarning(
                t("done_with_errors_title"),
                t("done_with_errors_msg", success=success, failed=failed)
            )
        else:
            self.log_panel.add_entry(f"All {success} file(s) downgraded to AE {self.target_var.get()}!", "success")
            messagebox.showinfo(
                t("success_title"),
                t("success_msg", success=success, year=self.target_var.get())
            )

    def process_log_queue(self):
        try:
            while True:
                level, filepath, msg = self.log_queue.get_nowait()
                name = Path(filepath).name

                if level == "success":
                    self.log_panel.add_entry(f"  ✓ {name}: {msg}", "success")
                    self._set_file_status(filepath, "success")
                else:
                    self.log_panel.add_entry(f"  ✗ {name}: {msg}", "error")
                    self._set_file_status(filepath, "error")
        except queue.Empty:
            pass

        self.root.after(100, self.process_log_queue)

    def on_close(self):
        self.root.quit()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    app = ModernAEDowngraderGUI()
    app.run()


if __name__ == "__main__":
    main()