#!/usr/bin/env python3
"""
After Effects Project Analyzer
Reads .aepx (XML) project files to extract version info and metadata.
Useful for checking project compatibility before attempting downgrade.

Note: .aep files are binary and cannot be easily parsed. .aepx files are XML-based.
If you only have .aep, you must open in After Effects and save as .aepx first.
"""

import xml.etree.ElementTree as ET
import sys
import os
import argparse
from pathlib import Path
from typing import Optional, Dict, Any


def parse_aepx(filepath: str) -> Dict[str, Any]:
    """Parse an .aepx file and extract key metadata."""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except ET.ParseError as e:
        return {"error": f"XML parse error: {e}"}
    except Exception as e:
        return {"error": f"Failed to read file: {e}"}

    info = {
        "file": os.path.basename(filepath),
        "path": filepath,
    }

    # Find version information
    # After Effects XML structure varies, try common locations
    for elem in root.iter():
        tag_lower = elem.tag.lower()
        text = elem.text.strip() if elem.text else ""

        if "version" in tag_lower and text:
            if "after" in tag_lower or "ae" in tag_lower or "app" in tag_lower:
                info["ae_version"] = text
            elif "project" in tag_lower:
                info["project_version"] = text
            else:
                info.setdefault("versions", []).append(f"{elem.tag}: {text}")

        if "name" in tag_lower and text and "project" in tag_lower:
            info["project_name"] = text

        if "created" in tag_lower and text:
            info["created_date"] = text
        if "modified" in tag_lower and text:
            info["modified_date"] = text

    # Try to find the main project element
    project_elem = root.find(".//project") or root.find(".//Project") or root
    if project_elem is not None:
        for key, value in project_elem.attrib.items():
            if "version" in key.lower():
                info[f"attr_{key}"] = value

    return info


def check_compatibility(info: Dict[str, Any], target_version: int = 2023) -> Dict[str, Any]:
    """Check if project might be compatible with target AE version."""
    result = {
        "target_version": target_version,
        "warnings": [],
        "likely_compatible": True,
    }

    ae_version = info.get("ae_version", "")
    if ae_version:
        try:
            # Extract major version number (e.g., "24.0" -> 24)
            major = int(float(aep_version.split(".")[0])) if "." in ae_version else int(ae_version)
            if major > target_version:
                result["warnings"].append(
                    f"Project created in AE {major}.0 (target: {target_version}) - "
                    f"Features from newer versions may not work"
                )
                result["likely_compatible"] = False
            elif major == target_version:
                result["warnings"].append("Project version matches target - should work directly")
            else:
                result["warnings"].append(f"Project version ({major}) is older than target - no downgrade needed")
        except ValueError:
            result["warnings"].append(f"Could not parse version: {ae_version}")

    # Check for common problematic features
    project_name = info.get("project_name", "").lower()
    if any(kw in project_name for kw in ["3d", "cineware", "vr", "immersive"]):
        result["warnings"].append("Project name suggests 3D/VR features - may not downgrade cleanly")

    return result


def analyze_folder(folder: str, target_version: int = 2023) -> None:
    """Analyze all .aepx files in a folder."""
    path = Path(folder)
    files = list(path.glob("*.aepx")) + list(path.glob("*.aep"))

    if not files:
        print(f"No .aepx or .aep files found in {folder}")
        return

    print(f"Analyzing {len(files)} file(s) in {folder}...\n")

    for f in files:
        if f.suffix.lower() == ".aep":
            print(f"{f.name}: Binary .aep file - cannot analyze without After Effects")
            print(f"  -> Open in AE and save as .aepx (File > Save As > .aepx)")
            continue

        info = parse_aepx(str(f))
        compat = check_compatibility(info, target_version)

        print(f"=== {f.name} ===")
        for k, v in info.items():
            if k != "path":
                print(f"  {k}: {v}")

        print(f"  Compatibility (AE {target_version}):")
        print(f"    Likely compatible: {compat['likely_compatible']}")
        for w in compat["warnings"]:
            print(f"    ⚠ {w}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Analyze After Effects project files for version compatibility"
    )
    parser.add_argument("path", help="Path to .aepx file or folder")
    parser.add_argument(
        "--target", "-t", type=int, default=2023,
        help="Target AE version (default: 2023)"
    )
    parser.add_argument(
        "--json", "-j", action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path does not exist: {path}")
        sys.exit(1)

    if path.is_file():
        info = parse_aepx(str(path))
        compat = check_compatibility(info, args.target)

        if args.json:
            import json
            print(json.dumps({"info": info, "compatibility": compat}, indent=2))
        else:
            print(f"=== {path.name} ===")
            for k, v in info.items():
                if k != "path":
                    print(f"  {k}: {v}")
            print(f"\nCompatibility (AE {args.target}):")
            print(f"  Likely compatible: {compat['likely_compatible']}")
            for w in compat["warnings"]:
                print(f"  ⚠ {w}")
    else:
        analyze_folder(str(path), args.target)


if __name__ == "__main__":
    main()