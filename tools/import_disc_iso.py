#!/usr/bin/env python3
"""Probe a local Xbox 360 XDVDFS disc image and optionally extract it locally.

Metadata inspection is read-only and reads at most four volume descriptors.
Full extraction is delegated to the separately installed xdvdfs command.
No game assets or executable bytes are uploaded, decrypted or decompiled.
"""
from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

SECTOR_SIZE = 2048
DESCRIPTOR_OFFSET = 32 * SECTOR_SIZE
MAGIC = b"MICROSOFT*XBOX*MEDIA"
PARTITION_LAYOUTS = (
    ("XISO", 0x00000000),
    ("XGD2", 0x0FD90000),
    ("XGD3", 0x02080000),
    ("XGD1", 0x18300000),
)
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "game-iso-extracted"


def inspect_iso(path: Path) -> dict:
    """Identify layout by reading XDVDFS volume descriptors at known offsets.

    Avoid guessing from the filename or file size. Does not traverse directories.
    """
    size = path.stat().st_size
    with path.open("rb") as stream:
        for name, partition_offset in PARTITION_LAYOUTS:
            start = partition_offset + DESCRIPTOR_OFFSET
            if size < start + SECTOR_SIZE:
                continue
            stream.seek(start)
            descriptor = stream.read(SECTOR_SIZE)
            if len(descriptor) != SECTOR_SIZE:
                continue
            if descriptor[:len(MAGIC)] != MAGIC or descriptor[-len(MAGIC):] != MAGIC:
                continue
            root_sector, root_bytes = struct.unpack_from("<II", descriptor, len(MAGIC))
            root_start = partition_offset + root_sector * SECTOR_SIZE
            if root_sector == 0 or root_bytes == 0 or root_start >= size or root_bytes > size - root_start:
                raise ValueError(
                    f"{name} volume descriptor found, but root directory bounds are invalid."
                )
            return {
                "format": "XDVDFS",
                "layout": name,
                "image_size_bytes": size,
                "partition_offset_bytes": partition_offset,
                "volume_descriptor_offset_bytes": start,
                "root_directory_sector": root_sector,
                "root_directory_size_bytes": root_bytes,
            }
    raise ValueError(
        "No valid XDVDFS volume descriptor at known XISO/XGD1/XGD2/XGD3 offsets. "
        "The file may be incomplete or use an unsupported disc layout."
    )


def extract_iso(path: Path, output: Path, xdvdfs: str | None = None) -> None:
    command = xdvdfs or shutil.which("xdvdfs")
    if not command:
        raise ValueError(
            "xdvdfs CLI not found. Get the appropriate Windows release from "
            "https://github.com/antangelo/xdvdfs/releases and put xdvdfs.exe on PATH, "
            "or specify --xdvdfs C:\\path\\to\\xdvdfs.exe."
        )
    output = output.resolve()
    if output == REPO_ROOT or output == path.parent.resolve():
        raise ValueError("Refusing to extract into the repository or ISO parent directory.")
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise ValueError(f"Extraction directory must be empty or not exist: {output}")
    output.mkdir(parents=True, exist_ok=True)
    # No shell=True: spaces in paths cannot change the command being executed.
    subprocess.run([command, "unpack", str(path), str(output)], check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path, help="Path to a LOCAL Xbox 360 .iso/.xiso file")
    parser.add_argument("--extract", action="store_true", help="Unpack with xdvdfs into a local ignored directory")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Extraction destination (default: game-iso-extracted)")
    parser.add_argument("--xdvdfs", help="Path to external xdvdfs executable (if not on PATH)")
    parser.add_argument("--report", type=Path, help="Save non-proprietary header metadata as JSON (no overwrite)")
    args = parser.parse_args(argv)
    try:
        iso = args.iso.expanduser().resolve()
        if not iso.is_file():
            raise ValueError(f"ISO file not found: {iso}")
        report = inspect_iso(iso)
        print("Xbox disc image header (read-only):")
        for key, value in report.items():
            print(f"  {key}: {value}")
        if args.report:
            report_path = args.report.expanduser().resolve()
            if report_path.exists():
                raise ValueError(f"Report already exists; refusing overwrite: {report_path}")
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with report_path.open("x", encoding="utf-8") as dest:
                json.dump(report, dest, indent=2)
                dest.write("\n")
            print(f"Header metadata written: {report_path}")
        if args.extract:
            output = args.output.expanduser().resolve()
            print(f"Extracting locally to: {output}", flush=True)
            extract_iso(iso, output, args.xdvdfs)
            if (output / "default.xex").is_file():
                print("Verified: default.xex exists in extracted root.")
            else:
                print("Warning: default.xex not at extraction root. Check the directory tree.")
            print("Game data stays on this computer. Do not commit it to GitHub.")
        else:
            print("Inspection complete. Add --extract to unpack; nothing has been extracted.")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
