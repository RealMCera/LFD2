#!/usr/bin/env python3
"""Inspect a local Xbox 360 XEX with the third-party xex2ool CLI.

This tool NEVER edits the input XEX. Optional basefile extraction creates a
separate file in research/local/ (ignored by Git). No downloads are performed.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_XEX = ROOT / "game-extracted" / "default.xex"
LOCAL_OUTPUT = ROOT / "research" / "local" / "default.basefile"


def find_tool(explicit: str | None) -> Path | str | None:
    if explicit:
        candidate = Path(explicit).expanduser()
        return candidate.resolve() if candidate.is_file() else None
    for name in ("xex2ool", "xex2ool.exe"):
        path = shutil.which(name)
        if path:
            return path
    for name in ("xex2ool.exe", "xex2ool"):
        candidate = ROOT / "tools" / "bin" / name
        if candidate.is_file():
            return candidate
    return None


def run(args: list[str]) -> None:
    print("\n> " + subprocess.list2cmdline(args), flush=True)
    subprocess.run(args, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", help="Absolute path to xex2ool.exe (or add it to PATH)")
    parser.add_argument("--xex", type=Path, default=DEFAULT_XEX,
                        help="Path to your original, locally extracted default.xex")
    parser.add_argument("--extract", action="store_true",
                        help="Also create a local decrypted/decompressed basefile")
    parser.add_argument("--output", type=Path, default=LOCAL_OUTPUT,
                        help="Destination for --extract (default: research/local/default.basefile)")
    args = parser.parse_args()

    xex = args.xex.expanduser().resolve()
    if not xex.is_file():
        print(f"Missing local XEX: {xex}", file=sys.stderr)
        return 2
    with xex.open("rb") as file:
        if file.read(4) != b"XEX2":
            print("Input is not a XEX2 file; no tool called.", file=sys.stderr)
            return 2

    tool = find_tool(args.tool)
    if tool is None:
        print(
            "xex2ool not found. Download an official Windows release from "
            "https://github.com/landaire/acceleration/releases and unpack "
            "xex2ool.exe into tools\\bin\\, or pass --tool with its full path.",
            file=sys.stderr,
        )
        return 2

    output = args.output.expanduser().resolve()
    if args.extract:
        if output == xex:
            print("Refusing to overwrite input XEX.", file=sys.stderr)
            return 2
        if output.exists():
            print(f"Refusing to overwrite existing output: {output}", file=sys.stderr)
            return 2
        if output.is_relative_to(ROOT) and not output.is_relative_to(ROOT / "research" / "local"):
            print("Within this public repository, output must be under research/local/.", file=sys.stderr)
            return 2

    cmd = str(tool)
    try:
        run([cmd, "info", str(xex)])
        run([cmd, "imports", str(xex)])
        if args.extract:
            output.parent.mkdir(parents=True, exist_ok=True)
            run([cmd, "basefile", str(xex), "-o", str(output)])
            if not output.is_file() or output.stat().st_size == 0:
                print("No nonempty output produced; check xex2ool messages.", file=sys.stderr)
                return 1
            with output.open("rb") as handle:
                header = handle.read(16)
            print(f"\nLocal basefile created: {output}")
            print(f"Size: {output.stat().st_size:,} bytes")
            print(f"First 16 bytes (hex): {header.hex(' ')}")
            if header.startswith(b"MZ"):
                print("Output begins with MZ; inspect its sections before selecting a loader.")
            else:
                print("Output is not obviously an MZ PE image; verify format before importing.")
        else:
            print("\nMetadata-only mode; no basefile was written.")
        print("Keep local executable, output, and assets OUT of the public Git repository.")
        return 0
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
