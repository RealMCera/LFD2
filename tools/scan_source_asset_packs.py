#!/usr/bin/env python3
"""Find *metadata* for original Source material assets across local Xbox packs.

Reads only ZIP central directories; never reads/extracts compressed member data.
Optional BSP pak lump 40 is read locally, to inspect its embedded directory.
Returns *candidate* filename matches, not proof of usable decoded textures.
"""
from __future__ import annotations

import argparse
from collections import Counter
import io
from pathlib import Path
import sys

try:
    from .bsp_to_browser_mesh import ROOT, MAP, BspError, read_directory, read_lump
    from .inspect_map_materials import inspect_materials
    from .scan_xbox_zip_directory import scan_directory, scan_xbox_zip
    from .inspect_xbox_zip import XboxZipError
except ImportError:
    from bsp_to_browser_mesh import ROOT, MAP, BspError, read_directory, read_lump
    from inspect_map_materials import inspect_materials
    from scan_xbox_zip_directory import scan_directory, scan_xbox_zip
    from inspect_xbox_zip import XboxZipError

DEFAULT_ROOT = ROOT / "game-extracted"
# These are only filename conventions. The actual texture *contents* may be
# VTFX regardless of the file extension and must be inspected separately.
MATERIAL_SUFFIXES = (
    ".vtf.360", ".360.vtf", ".vtfx", ".vmt", ".vtf", ".360",
)
MAX_REPORT_MATCHES = 12


def material_key(filename: str) -> str | None:
    """Normalize a console material filename to an uppercase BSP material ID."""
    normal = filename.replace("\\", "/").strip("/").casefold()
    if not normal.startswith("materials/"):
        return None
    path = normal[len("materials/"):]
    for suffix in MATERIAL_SUFFIXES:
        if path.endswith(suffix) and len(path) > len(suffix):
            return path[:-len(suffix)]
    return None


def match_material_names(filenames: list[str], source_materials: Counter) -> dict:
    source = {name.replace("\\", "/").casefold(): count
              for name, count in source_materials.items()}
    matches = {}
    extensions = Counter()
    material_files = 0
    example_material_paths = []
    for filename in filenames:
        if filename.replace("\\", "/").casefold().startswith("materials/"):
            material_files += 1
            if len(example_material_paths) < 6:
                example_material_paths.append(filename)
            suffix = Path(filename).suffix.casefold()
            extensions[suffix] += 1
        key = material_key(filename)
        if key in source:
            matches.setdefault(key, [])
            if len(matches[key]) < 3:
                matches[key].append(filename)
    return {
        "matched_materials": len(matches),
        "matched_faces": sum(source[k] for k in matches),
        "material_files": material_files,
        "material_extensions": extensions,
        "sample_material_paths": example_material_paths,
        "matches": matches,
    }


def scan_local_pak(bsp: bytes) -> dict:
    endian, directory, _ = read_directory(bsp)
    entry = directory[40]
    if not entry["size"]:
        raise XboxZipError("BSP has no embedded PAKFILE lump 40")
    pak = read_lump(bsp, entry, endian)
    # Existing extracted L4D2 BSP reported a 5.6MB embedded ZIP-like lump.
    # A size cap applies to this *local* source lump; no output is generated.
    if len(pak) > 64 * 1024 * 1024:
        raise XboxZipError("Embedded BSP ZIP too large for safe metadata scan")
    return scan_directory(io.BytesIO(pak), len(pak))


def summarize_report(label: str, report: dict, materials: Counter, samples: int) -> None:
    matches = match_material_names(report["filenames"], materials)
    count = report["candidate_headers"]
    print(f"\n{label}")
    print(f"  Directory candidates: {count:,} / {report['eocd_count']:,} declared; "
          f"rejected signatures: {sum(report['rejected'].values()):,}")
    print(f"  Header pairs: {report['adjacent_pairs']:,} adjacent, "
          f"{report['overlapping_pairs']:,} declared-span overlaps, "
          f"{report['small_gap_pairs']:,} small gaps, "
          f"{report['large_gap_pairs']:,} large gaps")
    print(f"  Extensions: {report['extensions'].most_common(6)}")
    print(f"  Files under materials/: {matches['material_files']:,}; "
          f"their extensions: {matches['material_extensions'].most_common(6)}")
    print(f"  Hotel materials with filename candidates: "
          f"{matches['matched_materials']:,}/{len(materials):,}; "
          f"corresponding face references: {matches['matched_faces']:,}")
    print("  Sample material filenames:")
    for name in matches["sample_material_paths"][:samples]:
        print(f"    {name}")
    if not matches["sample_material_paths"]:
        print("    (none found)")
    print("  Matching hotel material filenames:")
    for key in sorted(matches["matches"])[:samples]:
        print(f"    {key}: {matches['matches'][key][0]}")
    if not matches["matches"]:
        print("    (none found; another pack may contain textures)")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                   help="Private game-extracted directory")
    p.add_argument("--bsp", type=Path, default=MAP,
                   help="Private c1m1_hotel.360.bsp map for reference names")
    p.add_argument("--include-map-pak", action="store_true",
                   help="Also scan BSP's embedded PAKFILE lump 40, if present")
    p.add_argument("--samples", type=int, default=5,
                   help="Filename samples per archive (1..12)")
    args = p.parse_args()
    if not 1 <= args.samples <= 12:
        p.error("--samples must be 1..12")
    try:
        root = args.root.expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"Game extraction directory not found: {root}")
        bsp_path = args.bsp.expanduser().resolve()
        bsp = bsp_path.read_bytes()
        source = inspect_materials(bsp)["materials"]
        packs = sorted(root.rglob("*.360.zip"))
        if not packs:
            raise ValueError("No locally extracted .360.zip files found")
        if len(packs) > 32:
            raise ValueError("Unexpectedly many pack files; scan stopped")
        print(f"Original map: {bsp_path.name}; {len(source):,} distinct material names")
        print(f"Local console packs found: {len(packs)}")
        print("Only bounded ZIP central directories are scanned; no archive member data is read.")
        successes = 0
        for pack in packs:
            try:
                rel = pack.relative_to(root).as_posix()
                report = scan_xbox_zip(pack)
                summarize_report(rel, report, source, args.samples)
                successes += 1
            except (XboxZipError, OSError, ValueError) as err:
                print(f"\n{pack.name}: directory metadata not recognized: {err}")
        if args.include_map_pak:
            try:
                report = scan_local_pak(bsp)
                summarize_report(f"{bsp_path.name} embedded PAKFILE (BSP lump 40)",
                                 report, source, args.samples)
                successes += 1
            except (XboxZipError, OSError, ValueError, BspError) as err:
                print(f"\nEmbedded BSP PAKFILE: unavailable: {err}")
        print(f"\nFinished: {successes} supported directory scans. "
              "Candidate filenames only; no textures decoded or files exported.")
        return 0 if successes else 1
    except (OSError, ValueError, BspError) as err:
        print(f"Read-only pack scan stopped: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
