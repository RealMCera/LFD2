#!/usr/bin/env python3
"""Read-only header probe for locally extracted Xbox 360 Source maps and packs.

Never exports geometry, textures, code, or archive contents.
"""
from __future__ import annotations
import argparse
import struct
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DEFAULT_GAME = PROJECT / "game-extracted"
SIGNATURES = {b"VBSP": ("Source BSP (VBSP)", "<"),
              b"PSBV": ("Source BSP (Xbox/swapped candidate)", ">")}
LUMP_NAMES = {0: "entities", 1: "planes", 2: "texdata", 3: "vertices",
              7: "faces", 12: "edges", 13: "surfedges", 35: "gamelump",
              40: "pakfile"}


def probe_bsp_header(header: bytes, length: int) -> dict:
    """Read candidates, not an asserted Xbox BSP schema."""
    if len(header) < 1036:
        return {"status": "too short for 64-lump BSP header", "signature": header[:4].hex()}
    magic = header[:4]
    if magic not in SIGNATURES:
        return {"status": "unrecognized BSP signature", "signature": magic.hex()}
    label, endian = SIGNATURES[magic]
    version = struct.unpack_from(endian + "i", header, 4)[0]
    layouts = {}
    for layout in ("offset_length_version", "version_offset_length"):
        valid = 0
        samples = {}
        for idx in range(64):
            a, b, c = struct.unpack_from(endian + "iii", header, 8 + idx * 16)
            ofs, size, ver = (a, b, c) if layout == "offset_length_version" else (b, c, a)
            if ofs >= 0 and size >= 0 and (size == 0 or (ofs >= 1036 and ofs + size <= length)):
                valid += 1
            if idx in LUMP_NAMES:
                samples[LUMP_NAMES[idx]] = {"offset": ofs, "bytes": size, "version": ver}
        layouts[layout] = {"plausible_lumps": valid, "total_lumps": 64,
                           "sample_lumps": samples}
    return {"status": label, "magic": magic.decode("ascii"),
            "endian_candidate": "big" if endian == ">" else "little",
            "version_candidate": version, "layouts": layouts}


def inspect(root: Path, bsp_limit: int, zip_limit: int) -> int:
    if not root.is_dir():
        raise ValueError(f"Missing local extraction directory: {root}")
    bsps = sorted(root.rglob("*.bsp"))
    packs = sorted(root.rglob("*.zip"))
    print(f"Local Source asset probe: {len(bsps)} BSP maps, {len(packs)} ZIP-named packs")
    print("Header-only: maps read <=1036 bytes, packages read only 16 bytes.")
    print("\nBSP MAP SAMPLES:")
    for path in bsps[:bsp_limit]:
        size = path.stat().st_size
        with path.open("rb") as handle:
            meta = probe_bsp_header(handle.read(1036), size)
        print(f"  {path.relative_to(root).as_posix()} ({size:,} bytes)")
        print(f"    {meta['status']} | magic={meta.get('magic', meta.get('signature', 'n/a'))} "
              f"| endian={meta.get('endian_candidate', 'unknown')} "
              f"| version={meta.get('version_candidate', 'unknown')}")
        for kind, details in meta.get("layouts", {}).items():
            samples = details["sample_lumps"]
            print(f"    candidate {kind}: {details['plausible_lumps']}/64 plausible "
                  f"| entities={samples['entities']['bytes']} "
                  f"| vertices={samples['vertices']['bytes']} "
                  f"| faces={samples['faces']['bytes']}")
    print("\nPACKAGE SAMPLES:")
    for path in sorted(packs, key=lambda p: p.stat().st_size, reverse=True)[:zip_limit]:
        with path.open("rb") as handle:
            first = handle.read(16)
        is_standard = first[:4] in (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
        print(f"  {path.relative_to(root).as_posix()} ({path.stat().st_size:,} bytes)"
              f": first16={first.hex(' ')} "
              + ("ZIP-like signature" if is_standard else "nonstandard/unknown archive signature"))
    print("\nNo proprietary map content or assets were exported or uploaded.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=DEFAULT_GAME)
    parser.add_argument("--maps", type=int, default=3)
    parser.add_argument("--packages", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.maps <= 24 or not 1 <= args.packages <= 8:
        parser.error("--maps must be 1..24, --packages must be 1..8")
    try:
        return inspect(args.root.expanduser().resolve(), args.maps, args.packages)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
