#!/usr/bin/env python3
"""Convert ONE privately extracted Xbox VTFX to PNG using an external local tool.

Requires the user to download and inspect rob5300/vtfx_reader.exe separately.
This script NEVER downloads programs or assets, and NEVER uploads original
game data. It verifies the input VTFX header, rejects non-private outputs,
refuses nonempty PNG output directories, invokes the tool without a shell,
and validates PNG signature/dimensions. The original VTFX remains untouched.

Docs: https://github.com/rob5300/vtfx_reader
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import struct
import subprocess
import sys

try:
    from .bsp_to_browser_mesh import ROOT
    from .extract_single_vtfx import parse_vtfx_header, XboxZipError
except ImportError:
    from bsp_to_browser_mesh import ROOT
    from extract_single_vtfx import parse_vtfx_header, XboxZipError

PRIVATE_ROOT = ROOT / "research" / "local"
DEFAULT_INPUT = PRIVATE_ROOT / "vtfx" / "plaster_int_14.360.vtf"
DEFAULT_OUTPUT = PRIVATE_ROOT / "vtfx" / "png"
DEFAULT_CONVERTER = PRIVATE_ROOT / "tools" / "vtfx_reader.exe"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class ConversionError(ValueError):
    pass


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as src:
        header = src.read(24)
    if (len(header) != 24 or header[:8] != PNG_SIGNATURE
            or header[12:16] != b"IHDR"):
        raise ConversionError(f"PNG output header invalid: {path.name}")
    width, height = struct.unpack_from(">II", header, 16)
    if not (1 <= width <= 8192 and 1 <= height <= 8192):
        raise ConversionError(f"PNG has unsafe dimensions: {width}x{height}")
    return width, height


def verify_vtfx(path: Path) -> dict:
    if not path.is_file():
        raise ConversionError(f"Private VTFX input not found: {path}")
    if not path.is_relative_to(PRIVATE_ROOT.resolve()):
        raise ConversionError("Input must stay under ignored research/local/")
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ConversionError("Input larger than 8MB single-image safety limit")
    with path.open("rb") as src:
        return parse_vtfx_header(src.read(80))


def run_converter(vtfx: Path, output: Path, converter: Path) -> list[tuple[Path, int, int]]:
    """Execute only an explicitly installed executable; no download/shell."""
    vtfx = vtfx.expanduser().resolve()
    output = output.expanduser().resolve()
    converter = converter.expanduser().resolve()
    expected = verify_vtfx(vtfx)
    if not output.is_relative_to(PRIVATE_ROOT.resolve()):
        raise ConversionError("Output directory must stay in ignored research/local/")
    if output == PRIVATE_ROOT.resolve() or output == vtfx.parent:
        raise ConversionError("Use a dedicated output subfolder, not the input folder")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ConversionError(f"Output must be empty to prevent overwrites: {output}")
    if not converter.is_file() or converter.suffix.lower() != ".exe":
        raise ConversionError(f"Converter exe not found: {converter}. "
                              "Download a trusted Windows release of rob5300/vtfx_reader "
                              "and place it in research/local/tools/.")
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(converter), "-i", str(vtfx), "-o", str(output)],
                   check=True, timeout=180)
    pngs = sorted(output.rglob("*.png"))
    if not pngs or len(pngs) > 20:
        raise ConversionError(f"Expected 1..20 PNGs in private output; found {len(pngs)}")
    results = []
    for png in pngs:
        width, height = png_dimensions(png)
        if png.stat().st_size > 40 * 1024 * 1024:
            raise ConversionError(f"PNG exceeds 40MB safety limit: {png.name}")
        results.append((png, width, height))
    if not any((w, h) == (expected["width"], expected["height"])
               for _p,w,h in results):
        raise ConversionError(
            f"No PNG matched original VTFX dimensions "
            f"{expected['width']}x{expected['height']}; inspect output locally.")
    return results


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--converter", type=Path, default=DEFAULT_CONVERTER)
    args=p.parse_args()
    try:
        results=run_converter(args.input,args.output,args.converter)
        print("Original Xbox VTFX converted locally with vtfx_reader.")
        for png,w,h in results:
            print(f"  PNG: {png} ({w}x{h}; {png.stat().st_size:,} bytes)")
        print("Compare this PNG visually with the hotel. Keep artwork private.")
        return 0
    except (ConversionError, XboxZipError, OSError,
            subprocess.CalledProcessError, subprocess.TimeoutExpired) as err:
        print(f"Local VTFX conversion stopped: {err}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
