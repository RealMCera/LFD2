#!/usr/bin/env python3
"""Read non-proprietary header metadata from a local Xbox 360 XEX2 file.

No decryption, dumping, or execution. No external packages are needed.
XEX2 header layout: https://free60.org/System-Software/Formats/XEX/
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

XEX2_HEADER = struct.Struct(">4sIIIII")
OPTIONAL_ENTRY = struct.Struct(">II")
EXECUTION_ID = 0x00040006
BASE_FILE_FORMAT = 0x000003FF
ENCRYPTION_TYPES = {0: "none", 1: "normal (encrypted)"}
COMPRESSION_TYPES = {0: "none", 1: "basic", 2: "normal (LZX)", 3: "delta"}
MAX_OPTIONAL_HEADERS = 4096


def inspect_xex(path: Path) -> dict:
    size = path.stat().st_size
    if size < XEX2_HEADER.size:
        raise ValueError("File is smaller than a XEX2 header (24 bytes).")
    with path.open("rb") as fp:
        raw = fp.read(XEX2_HEADER.size)
        magic, flags, pe_offset, reserved, security_offset, count = XEX2_HEADER.unpack(raw)
        if magic != b"XEX2":
            raise ValueError(f"Not a XEX2 executable (magic: {magic!r}).")
        if count > MAX_OPTIONAL_HEADERS or XEX2_HEADER.size + count * 8 > size:
            raise ValueError(f"Unreasonable or truncated optional header directory ({count} entries).")
        directory = fp.read(count * OPTIONAL_ENTRY.size)
        if len(directory) != count * OPTIONAL_ENTRY.size:
            raise ValueError("Truncated optional header directory.")
        result = {
            "file": path.name,
            "size": size,
            "format": "XEX2",
            "module_flags": f"0x{flags:08X}",
            "pe_data_offset": f"0x{pe_offset:08X}",
            "security_info_offset": f"0x{security_offset:08X}",
            "optional_header_count": count,
            "execution_id_present": False,
            "base_file_format_present": False,
        }
        entries = [
            OPTIONAL_ENTRY.unpack_from(directory, i * OPTIONAL_ENTRY.size)
            for i in range(count)
        ]
        for key, offset in entries:
            if key != EXECUTION_ID:
                continue
            result["execution_id_present"] = True
            if offset + 24 > size:
                raise ValueError("Execution ID optional header points outside the XEX file.")
            fp.seek(offset)
            data = fp.read(24)
            # MediaID, Version, BaseVersion, TitleID, 4 one-byte values, SaveGameID
            media, version, base_version, title, platform, exe_type, disc, discs, save = struct.unpack(
                ">IIIIBBBBI", data
            )
            result.update({
                "media_id": f"{media:08X}",
                "title_id": f"{title:08X}",
                "version_raw": f"0x{version:08X}",
                "base_version_raw": f"0x{base_version:08X}",
                "platform": platform,
                "executable_type": exe_type,
                "disc_number": disc,
                "disc_count": discs,
                "save_game_id": f"{save:08X}",
            })
            break
        # XEX base-file format descriptor: size (u32), encryption (u16),
        # compression (u16), followed by format-specific fields.
        # Metadata only: do not decrypt keys, decompress, or export code.
        for key, offset in entries:
            if key != BASE_FILE_FORMAT:
                continue
            result["base_file_format_present"] = True
            if offset < XEX2_HEADER.size or offset + 8 > size:
                raise ValueError("Base-file format descriptor points outside the XEX file.")
            fp.seek(offset)
            declared_size, encryption, compression = struct.unpack(">IHH", fp.read(8))
            if declared_size < 8 or declared_size > size - offset:
                raise ValueError("Base-file format descriptor has an invalid size.")
            result.update({
                "base_file_format_size": declared_size,
                "encryption_type": f"{encryption}: {ENCRYPTION_TYPES.get(encryption, 'unknown')}",
                "compression_type": f"{compression}: {COMPRESSION_TYPES.get(compression, 'unknown')}",
            })
            break
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "file", nargs="?", type=Path,
        default=Path("game-extracted") / "default.xex",
        help="Path to local XEX (default: game-extracted/default.xex)",
    )
    args = parser.parse_args()
    try:
        path = args.file.expanduser().resolve()
        if not path.is_file():
            parser.error(f"File not found: {path}")
        report = inspect_xex(path)
        print("Xbox 360 XEX metadata (header only)")
        for key, value in report.items():
            print(f"{key:23}: {value}")
        print("\nThis reads metadata only. It does not decompile or decrypt the game.")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"Cannot inspect XEX: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
