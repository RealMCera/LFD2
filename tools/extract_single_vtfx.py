#!/usr/bin/env python3
"""Inspect or explicitly extract ONE original Xbox 360 VTFX texture locally.

Default is read-only and inspects a single matching file header in zip1.360.zip,
or from the hotel's embedded BSP PAKFILE using --source map. --extract writes
the *original single VTFX file* under gitignored research/local/vtfx only.

No game data is sent to GitHub, no network is used, and no decompression,
image conversion, bulk extraction, or overwrite occurs.
"""
from __future__ import annotations

import argparse
import io
from pathlib import Path
import struct
import sys

try:
    from .bsp_to_browser_mesh import ROOT, MAP, read_directory, read_lump, BspError
    from .inspect_xbox_zip import XboxZipError
    from .probe_xbox_texture_headers import inspect_local_header
    from .scan_xbox_zip_directory import scan_directory
except ImportError:
    from bsp_to_browser_mesh import ROOT, MAP, read_directory, read_lump, BspError
    from inspect_xbox_zip import XboxZipError
    from probe_xbox_texture_headers import inspect_local_header
    from scan_xbox_zip_directory import scan_directory

ZIP1 = ROOT / "game-extracted" / "left4dead2" / "zip1.360.zip"
OUT_DIR = ROOT / "research" / "local" / "vtfx"
DEFAULT_MATERIAL = "materials/plaster/plaster_int_14.360.vtf"
MAX_TEXTURE_BYTES = 8 * 1024 * 1024
FILE_FORMATS = {0:"RGBA8888", 1:"ABGR8888", 2:"RGB888", 3:"BGR888",
                11:"ARGB8888", 12:"BGRA8888", 13:"DXT1", 14:"DXT3",
                15:"DXT5", 16:"BGRX8888", 25:"RGBA16161616"}


def parse_vtfx_header(data: bytes) -> dict:
    """Read endian-aware Xbox 360 metadata from Valve SDK VTFFileHeaderX360_t."""
    if len(data) < 0x3c or data[:4] != b"VTFX":
        raise XboxZipError("Texture lacks a complete 0x3c-byte VTFX header")
    major, minor, header_size, flags = struct.unpack_from(">4I", data, 4)
    width,height,depth,frames,preload = struct.unpack_from(">5H",data,0x14)
    mip_skip,resource_count=struct.unpack_from(">2B",data,0x1e)
    image_format=struct.unpack_from(">I",data,0x30)[0]
    compressed_size=struct.unpack_from(">I",data,0x38)[0]
    if (major != 0x360 or minor != 8 or not 0x3c <= header_size <= 4096
            or not (1 <= width <= 8192 and 1 <= height <= 8192)
            or not (1 <= depth <= 2048 and 1 <= frames <= 8192)
            or resource_count > 32):
        raise XboxZipError("Unsupported or implausible Xbox VTFX header fields")
    if header_size < 0x3c + resource_count*8:
        raise XboxZipError("VTFX resource table exceeds reported header size")
    return {"version":f"{major}.{minor}", "header_size":header_size,
            "width":width, "height":height, "depth":depth, "frames":frames,
            "flags_hex":f"0x{flags:08x}","mip_skip":mip_skip,
            "resource_count":resource_count, "preload_bytes":preload,
            "format_id":image_format,
            "format_name":FILE_FORMATS.get(image_format,"unknown"),
            "compressed_resource_bytes":compressed_size}


def select_entry(entries: list[dict], material: str) -> dict:
    target=material.replace("\\","/").casefold().strip("/")
    found=[x for x in entries if x["name"].casefold().strip("/")==target]
    if len(found)!=1:
        raise XboxZipError(f"Expected exactly one filename match for '{material}'; found {len(found)}")
    return found[0]


def validate_texture(stream, filesize: int, central_offset: int, entry: dict) -> dict:
    meta=inspect_local_header(stream,filesize,central_offset,entry)
    if (meta["status"]!="local_header_found" or
            meta.get("texture_magic")!="VTFX" or
            not meta.get("local_filename_matches",False)):
        raise XboxZipError(f"Local entry failed VTFX header checks: {meta['status']}, "
                           f"magic={meta.get('texture_magic')}, "
                           f"matching_name={meta.get('local_filename_matches')}")
    if entry["method"]!=0 or meta["local_method"]!=0:
        raise XboxZipError("Compressed ZIP member unsupported for safe single-file copy")
    if entry["flags"] & 1 or meta["local_flags"] & 1:
        raise XboxZipError("Encrypted ZIP member unsupported")
    length=entry["compressed_size"]
    if not (0x3c <= length <= MAX_TEXTURE_BYTES):
        raise XboxZipError(f"Texture size {length:,} is outside 60B..8MB safety limit")
    if entry["uncompressed_size"]!=length:
        raise XboxZipError("ZIP member compressed/uncompressed sizes differ for stored file")
    if meta["local_compressed_bytes"] not in (0,length) or (
            meta["local_uncompressed_bytes"] not in (0,length)):
        raise XboxZipError("Local ZIP member length contradicts directory length")
    offset=meta["candidate_payload_offset"]
    if offset+length > central_offset:
        raise XboxZipError("Texture payload would overlap ZIP central directory")
    stream.seek(offset)
    vtfx=parse_vtfx_header(stream.read(min(0x3c,length)))
    if vtfx["header_size"] > length:
        raise XboxZipError("VTFX reported header exceeds member data")
    return {"name":entry["name"],"offset":offset,"bytes":length,"header":vtfx}


def inspect_archive(stream, filesize:int, filename:str) -> dict:
    report=scan_directory(stream,filesize)
    selected=select_entry(report["entries"], filename)
    result=validate_texture(stream,filesize,report["directory_offset"],selected)
    result["directory_candidates"]=report["candidate_headers"]
    result["directory_declared"]=report["eocd_count"]
    return result


def local_archive(source: str, bsp_path: Path, zip_path: Path):
    if source=="zip1":
        p=zip_path.expanduser().resolve()
        return p.open("rb"), p.stat().st_size
    bsp=bsp_path.expanduser().resolve().read_bytes()
    endian,directory,_=read_directory(bsp)
    pak=read_lump(bsp,directory[40],endian)
    if not pak or len(pak)>64*1024*1024:
        raise XboxZipError("Map pak missing or larger than local 64MB limit")
    return io.BytesIO(pak),len(pak)


def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",choices=("zip1","map"),default="zip1")
    p.add_argument("--material",default=DEFAULT_MATERIAL,
                   help="Exact material file name from local ZIP directory")
    p.add_argument("--zip",type=Path,default=ZIP1)
    p.add_argument("--bsp",type=Path,default=MAP)
    p.add_argument("--extract",action="store_true",
                   help="Explicitly write only this original texture into ignored research/local/vtfx")
    p.add_argument("--output",type=Path,
                   help="Private output file path within research/local/vtfx")
    args=p.parse_args()
    try:
        stream,size=local_archive(args.source,args.bsp,args.zip)
        with stream:
            result=inspect_archive(stream,size,args.material)
            print(f"Found original VTFX: {result['name']}")
            print(f"Source: {args.source}; members: "
                  f"{result['directory_candidates']:,}/"
                  f"{result['directory_declared']:,} directory signatures")
            print(f"Local file data: {result['bytes']:,} bytes at offset {result['offset']:,}")
            info=result["header"]
            print(f"VTFX version: {info['version']}; "
                  f"image: {info['width']}x{info['height']}; "
                  f"format: {info['format_name']} ({info['format_id']})")
            print(f"Header bytes: {info['header_size']}; "
                  f"resources: {info['resource_count']}; "
                  f"compressed image resource: {info['compressed_resource_bytes']:,} bytes")
            if not args.extract:
                print("Read-only header validation complete. Add --extract "
                      "to copy only this texture privately.")
                return 0
            output=(args.output or OUT_DIR / Path(args.material).name).expanduser().resolve()
            if not output.is_relative_to(OUT_DIR):
                raise XboxZipError("Output must be inside ignored research/local/vtfx")
            if output.exists():
                raise XboxZipError(f"Output already exists; overwrite refused: {output}")
            output.parent.mkdir(parents=True,exist_ok=True)
            stream.seek(result["offset"])
            with output.open("xb") as target:
                remaining=result["bytes"]
                while remaining:
                    block=stream.read(min(65536,remaining))
                    if not block:
                        raise XboxZipError("Unexpected short original texture data")
                    target.write(block)
                    remaining-=len(block)
            print(f"Private original texture copied: {output} "
                  f"({output.stat().st_size:,} bytes)")
            print("No archive changed, no images decoded, and no data uploaded.")
        return 0
    except (OSError,ValueError,BspError,XboxZipError,struct.error) as err:
        print(f"Single-texture operation stopped: {err}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
