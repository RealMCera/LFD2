#!/usr/bin/env python3
"""Probe a few privately owned L4D2 Xbox texture headers, without extraction.

Only a local ZIP's central directory, 30-byte local file headers and at most
16 bytes at each candidate image payload position are read. This deliberately
does not decompress, export, or upload any original game texture.
The Xbox 360 ZIP's central *extra-length* fields are not trusted.
"""
from __future__ import annotations

import argparse
import io
from pathlib import Path
import struct
import sys

try:
    from .bsp_to_browser_mesh import ROOT, MAP, read_directory, read_lump, BspError
    from .inspect_map_materials import inspect_materials
    from .inspect_xbox_zip import XboxZipError, MAX_NAME
    from .scan_xbox_zip_directory import scan_directory, scan_xbox_zip
    from .scan_source_asset_packs import material_key
except ImportError:
    from bsp_to_browser_mesh import ROOT, MAP, read_directory, read_lump, BspError
    from inspect_map_materials import inspect_materials
    from inspect_xbox_zip import XboxZipError, MAX_NAME
    from scan_xbox_zip_directory import scan_directory, scan_xbox_zip
    from scan_source_asset_packs import material_key

DEFAULT_ARCHIVE = ROOT / "game-extracted" / "left4dead2" / "zip1.360.zip"
LOCAL_SIGNATURE = b"PK\x03\x04"
IMAGE_EXTENSIONS = (".360.vtf", ".vtfx", ".vtf.360", ".vtf")
SAMPLE_HEADER_LENGTH = 16


def pick_image_entries(report: dict, material_counts: dict, limit: int) -> list[dict]:
    matched = []
    fallback = []
    for item in report["entries"]:
        name = item["name"]
        if not name.casefold().endswith(IMAGE_EXTENSIONS):
            continue
        key = material_key(name)
        if key in material_counts:
            matched.append((material_counts[key], item))
        else:
            fallback.append(item)
    matched.sort(key=lambda p: -p[0])
    chosen = [item for _count, item in matched[:limit]]
    if len(chosen) < limit:
        chosen += fallback[:limit-len(chosen)]
    return chosen


def inspect_local_header(stream, filesize: int, directory_offset: int,
                         entry: dict) -> dict:
    """Verify bounded ZIP local metadata and peek only at texture magic."""
    offset = entry["local_offset"]
    result = {"file": entry["name"], "local_offset": offset,
              "central_method": entry["method"],
              "central_compressed_bytes": entry["compressed_size"],
              "central_uncompressed_bytes": entry["uncompressed_size"]}
    if not 0 <= offset <= min(filesize, directory_offset)-30:
        result["status"] = "invalid_local_offset"
        return result
    stream.seek(offset)
    header = stream.read(30)
    if len(header) != 30 or header[:4] != LOCAL_SIGNATURE:
        result["status"] = "missing_PK_local_header"
        result["found_signature"] = header[:4].hex(" ")
        return result
    sig, needed, flags, method, dostime, dosdate, crc, compressed, expanded, name_len, extra_len = (
        struct.unpack("<I5H3I2H", header))
    result.update({"status": "local_header_found",
                   "local_flags": flags, "local_method": method,
                   "local_filename_bytes": name_len,
                   "local_extra_bytes": extra_len,
                   "local_compressed_bytes": compressed,
                   "local_uncompressed_bytes": expanded})
    if name_len <= 0 or name_len > MAX_NAME:
        result["status"] = "invalid_local_filename_size"
        return result
    data_offset = offset + 30 + name_len + extra_len
    if data_offset > directory_offset or data_offset+SAMPLE_HEADER_LENGTH > filesize:
        result["status"] = "local_data_offset_outside_archive"
        return result
    stream.seek(offset+30)
    name = stream.read(name_len)
    result["local_filename_matches"] = (
        name.decode("utf-8" if flags & 0x800 else "cp437",
                    errors="replace").replace("\\", "/").casefold()
        == entry["name"].casefold()
    )
    result["candidate_payload_offset"] = data_offset
    # Signature ONLY: no archive data is exported. A successful magic check
    # does not prove the rest of the file is valid or decodable.
    stream.seek(data_offset)
    prefix = stream.read(SAMPLE_HEADER_LENGTH)
    result["candidate_magic_hex"] = prefix[:8].hex(" ")
    if prefix.startswith(b"VTFX"):
        result["texture_magic"] = "VTFX"
    elif prefix.startswith(b"VTF\x00"):
        result["texture_magic"] = "VTF"
    else:
        result["texture_magic"] = "unknown"
    return result


def probe_stream(stream, filesize: int, material_counts: dict,
                 samples: int) -> tuple[dict, list[dict]]:
    report = scan_directory(stream, filesize)
    candidates = pick_image_entries(report, material_counts, samples)
    records = [inspect_local_header(stream, filesize,
                                   report["directory_offset"], item)
               for item in candidates]
    return report, records


def print_report(label: str, result: tuple[dict, list[dict]]) -> None:
    report, records = result
    print(f"\n{label}")
    print(f"  Image candidates checked: {len(records)}")
    print(f"  Directory signatures: {report['candidate_headers']:,}/"
          f"{report['eocd_count']:,} declared")
    if not records:
        print("  No image candidates found.")
        return
    for item in records:
        print(f"  FILE: {item['file']}")
        print(f"    central local_offset={item['local_offset']:,}; "
              f"method={item['central_method']}; "
              f"size={item['central_uncompressed_bytes']:,}")
        print(f"    local header: {item['status']}")
        if "local_filename_bytes" in item:
            print(f"    local filename bytes={item['local_filename_bytes']}, "
                  f"extra bytes={item['local_extra_bytes']}, "
                  f"name matches={item.get('local_filename_matches', False)}")
        if "candidate_magic_hex" in item:
            print(f"    8-byte payload signature={item['candidate_magic_hex']} "
                  f"({item['texture_magic']})")
        if "found_signature" in item:
            print(f"    actual local signature={item['found_signature']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--bsp", type=Path, default=MAP)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--include-map-pak", action="store_true",
                        help="Also examine local BSP embedded pakfile image headers")
    args = parser.parse_args()
    if not 1 <= args.samples <= 12:
        parser.error("--samples must be between 1 and 12")
    try:
        bsp = args.bsp.expanduser().resolve().read_bytes()
        counts = {key.casefold(): value for key,value
                  in inspect_materials(bsp)["materials"].items()}
        path = args.archive.expanduser().resolve()
        with path.open("rb") as stream:
            result = probe_stream(stream, path.stat().st_size, counts, args.samples)
        print_report(path.name, result)
        if args.include_map_pak:
            endian, directory, _ = read_directory(bsp)
            blob = read_lump(bsp, directory[40], endian)
            if len(blob) > 64*1024*1024:
                raise XboxZipError("Embedded BSP PAK too large for header probe")
            stream = io.BytesIO(blob)
            print_report("BSP embedded PAKFILE lump 40",
                         probe_stream(stream, len(blob), counts, args.samples))
        print("\nLocal metadata check complete. No textures extracted, decoded, "
              "exported or uploaded.")
        return 0
    except (OSError, ValueError, struct.error, XboxZipError, BspError) as error:
        print(f"Local texture header probe stopped: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
