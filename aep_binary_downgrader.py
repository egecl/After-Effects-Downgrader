#!/usr/bin/env python3
"""
AE Project Binary Downgrader - Accurate Version
Patches the major version byte in the RIFX/head chunk.

Based on research from:
- https://github.com/itsAnchorpoint/AEP-Downgrader (technical docs)
- https://ken-eizo.github.io/after-effects-internals-guide/persistence/aep/
- https://forticheprod.github.io/py-aep/file_format/

AEP Format (RIFX = little-endian RIFF):
  Offset 0:   "RIFX" (4 bytes)
  Offset 4:   File size (4 bytes, LE)
  Offset 8:   "Egg!" form type (4 bytes)  -- AE uses "Egg!" not "AEP "
  Offset 12:  Chunks...
    "head" chunk at offset ~12-16:
      Offset 0: "head" tag
      Offset 4: chunk size
      Offset 8: chunk data starts
        Offset 0 (abs 20): major version byte = head_data[1] - 0x5B + 20
        Offset 1 (abs 21): minor version
        Offset 2-7: signature bytes (version-specific)
        ... rest of header
"""

import struct
import sys
import os
import argparse
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass


# Major version byte values (head chunk data[1])
# Formula: major_version = byte_value - 0x5B + 20
# So: byte_value = major_version - 20 + 0x5B = major_version + 0x47
MAJOR_VERSION_BYTE = {
    2025: 0x60,  # 25 + 0x47 = 0x60
    2024: 0x5F,  # 24 + 0x47 = 0x5F
    2023: 0x5E,  # 23 + 0x47 = 0x5E
    2022: 0x5D,  # 22 + 0x47 = 0x5D
    2021: 0x5C,  # 18 + 0x47 = 0x5C  (AE 2021 = 18.x)
    2020: 0x5B,  # 17 + 0x47 = 0x5B  (AE 2020 = 17.x)
    2019: 0x5A,  # 16 + 0x47 = 0x5A  (AE 2019 = 16.x)
    2018: 0x59,  # 15 + 0x47 = 0x59  (CC 2018)
}

# Reverse mapping
BYTE_TO_VERSION = {v: k for k, v in MAJOR_VERSION_BYTE.items()}

# Known signatures (head chunk data[2:8]) for validation
KNOWN_SIGNATURES = {
    0x60: bytes([0x60, 0x01, 0x0F, 0x08, 0x86, 0x44]),  # AE 2025
    0x5F: bytes([0x5F, 0x05, 0x0F, 0x02, 0x86, 0x34]),  # AE 2024
    0x5E: bytes([0x5E, 0x09, 0x0B, 0x3B, 0x06, 0x37]),  # AE 2023
    0x5D: bytes([0x5D, 0x2B, 0x0B, 0x33, 0x06, 0x3B]),  # AE 2022
    0x5C: bytes([0x5C, 0x00, 0x00, 0x00, 0x00, 0x00]),  # AE 2021 (placeholder)
    0x5B: bytes([0x5B, 0x00, 0x00, 0x00, 0x00, 0x00]),  # AE 2020 (placeholder)
    0x5A: bytes([0x5A, 0x00, 0x00, 0x00, 0x00, 0x00]),  # AE 2019 (placeholder)
}


@dataclass
class AEPInfo:
    """Information extracted from .aep file"""
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


def find_rifx_egg(data: bytes) -> Tuple[Optional[int], Optional[int]]:
    """Find RIFX/RIFF header and Egg! form type."""
    # Try RIFX first (little-endian, Windows)
    rifx_pos = data.find(b"RIFX")
    if rifx_pos >= 0:
        if rifx_pos + 12 <= len(data):
            form_type = data[rifx_pos + 8:rifx_pos + 12]
            if form_type == b"Egg!":
                return rifx_pos, rifx_pos + 8

    # Try RIFF (big-endian, Mac)
    riff_pos = data.find(b"RIFF")
    if riff_pos >= 0:
        if riff_pos + 12 <= len(data):
            form_type = data[riff_pos + 8:riff_pos + 12]
            if form_type == b"Egg!":
                return riff_pos, riff_pos + 8

    return None, None


def find_head_chunk(data: bytes, start_offset: int) -> Tuple[Optional[int], Optional[int]]:
    """Find 'head' chunk after Egg! form type."""
    # Search for "head" tag starting from form type
    search_start = start_offset + 4  # Skip form type
    head_pos = data.find(b"head", search_start)
    if head_pos < 0:
        return None, None

    # Chunk structure: tag(4) + size(4, BIG-ENDIAN) + data
    # AE's RIFX files use big-endian chunk sizes inside Egg! form
    if head_pos + 8 <= len(data):
        chunk_size = struct.unpack(">I", data[head_pos + 4:head_pos + 8])[0]
        data_start = head_pos + 8
        data_end = data_start + chunk_size
        if data_end <= len(data):
            return head_pos, chunk_size

    return None, None


def analyze_aep(filepath: str) -> AEPInfo:
    """Analyze an .aep file and extract version info from head chunk."""
    with open(filepath, "rb") as f:
        data = f.read()

    info = AEPInfo(file_path=filepath, file_size=len(data))

    # Find RIFX/RIFF + Egg!
    rifx_offset, egg_offset = find_rifx_egg(data)
    if rifx_offset is None:
        return info

    info.rifx_offset = rifx_offset
    info.egg_offset = egg_offset

    # Determine format
    is_riff = data[rifx_offset:rifx_offset+4] == b"RIFF"

    # Find head chunk
    head_offset, head_size = find_head_chunk(data, egg_offset)
    if head_offset is None:
        return info

    info.head_offset = head_offset
    info.head_size = head_size

    # Head chunk data starts at head_offset + 8
    head_data_start = head_offset + 8
    head_data = data[head_data_start:head_data_start + head_size]

    if len(head_data) >= 8:
        # head_data[0] = usually 0x00 or similar
        # head_data[1] = major version byte
        info.major_version_byte = head_data[1]
        info.detected_version = BYTE_TO_VERSION.get(head_data[1])
        info.signature = head_data[2:8]
        info.signature_known = head_data[1] in KNOWN_SIGNATURES

    return info


def patch_aep_version(
    input_path: str,
    output_path: str,
    target_year: int,
    dry_run: bool = False,
    force: bool = False
) -> bool:
    """
    Patch .aep file to target version by modifying the major version byte.
    """
    if target_year not in MAJOR_VERSION_BYTE:
        print(f"  ✗ Unsupported target year: {target_year}")
        return False

    target_byte = MAJOR_VERSION_BYTE[target_year]

    with open(input_path, "rb") as f:
        data = bytearray(f.read())

    # Analyze first
    info = analyze_aep(input_path)

    if info.rifx_offset is None:
        print(f"  ✗ Not a valid RIFX/RIFF Egg! file")
        return False

    if info.head_offset is None:
        print(f"  ✗ 'head' chunk not found")
        return False

    if info.major_version_byte is None:
        print(f"  ✗ Could not read major version byte")
        return False

    # Determine format for endianness
    is_riff = data[info.rifx_offset:info.rifx_offset+4] == b"RIFF"
    format_name = "RIFF (big-endian)" if is_riff else "RIFX (little-endian)"

    current_byte = info.major_version_byte
    current_version = info.detected_version

    print(f"  File: {os.path.basename(input_path)}")
    print(f"  Format: {format_name}")
    print(f"  Header at: 0x{info.rifx_offset:X}")
    print(f"  head chunk at: 0x{info.head_offset:X} (size: {info.head_size})")
    print(f"  Current version byte: 0x{current_byte:02X} -> AE {current_version or 'unknown'}")
    print(f"  Signature: {info.signature.hex().upper() if info.signature else 'N/A'} {'(known)' if info.signature_known else '(unknown)'}")

    if current_version == target_year:
        print(f"  ⚠ Already target version {target_year}")
        if not force:
            return False

    print(f"  Target version byte: 0x{target_byte:02X} -> AE {target_year}")

    if dry_run:
        print(f"  [DRY RUN] Would patch byte at offset 0x{info.head_offset + 9:X}")
        return True

    # Patch the major version byte (head_data[1] = file offset head_offset + 9)
    patch_offset = info.head_offset + 9
    data[patch_offset] = target_byte

    # Optionally update signature bytes to match target version (bytes 2-7 of head data)
    # This is what some tools do for better compatibility
    if target_byte in KNOWN_SIGNATURES:
        target_sig = KNOWN_SIGNATURES[target_byte]
        sig_offset = info.head_offset + 10  # head_data[2] onwards
        data[sig_offset:sig_offset + 6] = target_sig
        print(f"  Also updated signature to: {target_sig.hex().upper()}")

    # Write output
    with open(output_path, "wb") as f:
        f.write(data)

    print(f"  ✓ Saved to: {output_path}")
    return True


def batch_downgrade(
    input_dir: str,
    output_dir: str,
    target_year: int,
    dry_run: bool = False,
    force: bool = False
) -> List[str]:
    """Batch process .aep files in a directory."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if target_year not in MAJOR_VERSION_BYTE:
        print(f"Error: Unsupported target year {target_year}")
        return []

    target_byte = MAJOR_VERSION_BYTE[target_year]

    print(f"\nTarget: AE {target_year} (version byte 0x{target_byte:02X})")
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Dry run: {dry_run}\n")

    files = list(input_path.glob("*.aep"))
    if not files:
        print("No .aep files found.")
        return []

    results = []
    for f in files:
        print(f"Processing: {f.name}")
        output_file = output_path / f"{f.stem}_v{target_year}{f.suffix}"

        success = patch_aep_version(
            str(f), str(output_file), target_year, dry_run, force
        )
        results.append(f"{f.name}: {'OK' if success else 'FAILED/SKIPPED'}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="AE Project Binary Downgrader - patches major version byte in head chunk",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a file
  python aep_binary_downgrader.py analyze project.aep

  # Downgrade single file (dry run first)
  python aep_binary_downgrader.py patch project.aep -t 2023 --dry-run
  python aep_binary_downgrader.py patch project.aep -t 2023 -o project_2023.aep

  # Batch downgrade folder
  python aep_binary_downgrader.py batch ./projects ./output -t 2023

Supported versions: 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018

WARNING: This patches ONLY the version byte in the head chunk.
It does NOT convert features, effects, expressions, or assets.
Complex projects may crash or lose data in older AE versions.
ALWAYS TEST ON A COPY!
        """
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze .aep file version info")
    analyze_parser.add_argument("file", help="Path to .aep file")

    # Patch command
    patch_parser = subparsers.add_parser("patch", help="Patch single .aep file")
    patch_parser.add_argument("input", help="Input .aep file")
    patch_parser.add_argument("-o", "--output", help="Output file (default: input_vYYYY.aep)")
    patch_parser.add_argument("-t", "--target", type=int, required=True,
                              choices=sorted(MAJOR_VERSION_BYTE.keys()),
                              help="Target AE year (e.g., 2023)")
    patch_parser.add_argument("--dry-run", action="store_true",
                              help="Show what would be changed without writing")
    patch_parser.add_argument("--force", action="store_true",
                              help="Patch even if already target version")

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Batch process folder")
    batch_parser.add_argument("input_dir", help="Input directory with .aep files")
    batch_parser.add_argument("output_dir", help="Output directory")
    batch_parser.add_argument("-t", "--target", type=int, required=True,
                              choices=sorted(MAJOR_VERSION_BYTE.keys()),
                              help="Target AE year (e.g., 2023)")
    batch_parser.add_argument("--dry-run", action="store_true",
                              help="Show what would be changed without writing")
    batch_parser.add_argument("--force", action="store_true",
                              help="Patch even if already target version")

    args = parser.parse_args()

    if args.command == "analyze":
        info = analyze_aep(args.file)
        print(f"File: {info.file_path}")
        print(f"Size: {info.file_size:,} bytes")
        print(f"RIFX header: {'0x%X' % info.rifx_offset if info.rifx_offset else 'NOT FOUND'}")
        print(f"Egg! form:   {'0x%X' % info.egg_offset if info.egg_offset else 'NOT FOUND'}")
        print(f"head chunk:  {'0x%X' % info.head_offset if info.head_offset else 'NOT FOUND'}"
              f"{' (size: %d)' % info.head_size if info.head_size else ''}")
        print(f"Version byte: 0x{info.major_version_byte:02X}" if info.major_version_byte else "Version byte: NOT FOUND")
        print(f"Detected AE:  {info.detected_version}" if info.detected_version else "Detected AE: Unknown")
        print(f"Signature:    {info.signature.hex().upper() if info.signature else 'N/A'}"
              f"{' (known)' if info.signature_known else ' (unknown)'}")

    elif args.command == "patch":
        output = args.output
        if not output:
            stem = Path(args.input).stem
            suffix = Path(args.input).suffix
            output = f"{stem}_v{args.target}{suffix}"

        patch_aep_version(args.input, output, args.target, args.dry_run, args.force)

    elif args.command == "batch":
        results = batch_downgrade(args.input_dir, args.output_dir, args.target, args.dry_run, args.force)
        print("\n=== Summary ===")
        for r in results:
            print(f"  {r}")


if __name__ == "__main__":
    main()