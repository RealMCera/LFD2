#!/usr/bin/env python3
"""Inspect PE/COFF headers in a locally extracted Xbox 360 XEX basefile.

Reads header and section metadata only; never executes, decrypts, changes,
or uploads the file. Uses Python standard library only.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "research" / "local" / "default.basefile"
MACHINE_NAMES = {0x01F0: "PowerPC", 0x01F2: "PowerPC FP", 0x8664: "x64", 0x014C: "x86"}


def parse_pe(data: bytes) -> dict:
    def require(offset: int, length: int) -> None:
        if offset < 0 or length < 0 or offset + length > len(data):
            raise ValueError(f"Truncated PE header at offset 0x{offset:X}")

    require(0, 0x40)
    if data[:2] != b"MZ":
        raise ValueError("Missing DOS MZ signature")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    require(pe_offset, 24)
    if data[pe_offset:pe_offset + 4] != b"PE\x00\x00":
        raise ValueError("Missing PE signature at DOS e_lfanew")
    machine, section_count, timestamp, symptr, symcount, opt_size, flags = (
        struct.unpack_from("<HHIIIHH", data, pe_offset + 4)
    )
    if section_count > 96:
        raise ValueError(f"Implausible number of sections: {section_count}")
    opt_offset = pe_offset + 24
    require(opt_offset, opt_size)
    if opt_size < 64:
        raise ValueError("Optional header too small to contain image metadata")
    magic = struct.unpack_from("<H", data, opt_offset)[0]
    if magic == 0x10B:
        image_base = struct.unpack_from("<I", data, opt_offset + 28)[0]
        fmt = "PE32"
    elif magic == 0x20B:
        image_base = struct.unpack_from("<Q", data, opt_offset + 24)[0]
        fmt = "PE32+"
    else:
        raise ValueError(f"Unsupported optional header magic: 0x{magic:04X}")
    entry_rva = struct.unpack_from("<I", data, opt_offset + 16)[0]
    image_size = struct.unpack_from("<I", data, opt_offset + 56)[0]
    section_offset = opt_offset + opt_size
    require(section_offset, section_count * 40)

    sections = []
    for index in range(section_count):
        start = section_offset + index * 40
        name, virtual_size, rva, disk_size, disk_offset, reloc, line, nr, nl, attrs = (
            struct.unpack_from("<8sIIIIIIHHI", data, start)
        )
        name = name.partition(b"\0")[0].decode("ascii", errors="replace")
        sections.append({
            "name": name,
            "rva": f"0x{rva:08X}",
            "virtual_size": virtual_size,
            "file_offset": f"0x{disk_offset:08X}",
            "file_size": disk_size,
            "characteristics": f"0x{attrs:08X}",
        })

    return {
        "format": fmt,
        "size": len(data),
        "pe_header_offset": f"0x{pe_offset:X}",
        "machine": f"0x{machine:04X} ({MACHINE_NAMES.get(machine, 'unknown')})",
        "sections": section_count,
        "image_base": f"0x{image_base:X}",
        "entry_rva": f"0x{entry_rva:X}",
        "entry_va_from_pe": f"0x{image_base + entry_rva:X}",
        "size_of_image": f"0x{image_size:X}",
        "section_table": sections,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, nargs="?", default=DEFAULT,
                        help="Local basefile path (default: research/local/default.basefile)")
    args = parser.parse_args()
    try:
        path = args.path.expanduser().resolve()
        data = path.read_bytes()
        info = parse_pe(data)
        print("PE metadata (not executable code):")
        for key, value in info.items():
            if key != "section_table":
                print(f"{key:22}: {value}")
        print("Section headers:")
        for section in info["section_table"]:
            print(
                f"  {section['name']:<9} RVA={section['rva']}"
                f" virtual={section['virtual_size']:,}"
                f" raw={section['file_offset']}+{section['file_size']:,}"
                f" flags={section['characteristics']}"
            )
        print("\nExpected XEX-derived entry: 0x82010CB8, load address: 0x82000000.")
        print("Compare the values above; differences may require Xbox-specific mapping.")
        print("No proprietary binary data was emitted or uploaded.")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"PE inspection failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
