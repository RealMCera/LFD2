#!/usr/bin/env python3
"""Inspect original Source material references without exporting proprietary assets.

Reads only metadata from the user's private BSP and (optionally) ZIP directories.
Handles endian-correct BSP texdata/texinfo/string tables and HDR faces (lump 58).
Xbox XZIP archives may not be understood by Python's standard zip reader.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import struct
import sys
import zipfile

try:
    from .bsp_to_browser_mesh import ROOT, MAP, BspError, read_directory, read_lump
    from .inspect_xbox_zip import inspect_xbox_zip, XboxZipError
except ImportError:
    from bsp_to_browser_mesh import ROOT, MAP, BspError, read_directory, read_lump
    from inspect_xbox_zip import inspect_xbox_zip, XboxZipError

TEXDATA_LUMP = 2
TEXINFO_LUMP = 6
STRINGS_LUMP = 43
TABLE_LUMP = 44
MATERIAL_FILE_EXTENSIONS = {".vmt", ".vtf", ".vtfx", ".mdl", ".vtx", ".vvd"}
MAX_ZIP_ENTRIES = 200_000
MAX_PRINTED = 18


def texture_strings(data: bytes, endian: str, count: int, indices: list[int]) -> list[str]:
    if len(data) > 8 * 1024 * 1024:
        raise BspError("Unusually large texture string lump")
    names = []
    for ref in indices[:count]:
        if ref < 0 or ref >= len(data):
            raise BspError(f"Texture string offset {ref} outside string lump")
        end = data.find(b"\x00", ref)
        if end < 0 or end - ref > 320:
            raise BspError("Missing or unusually long texture string")
        names.append(data[ref:end].decode("utf-8", errors="replace"))
    return names


def inspect_materials(data: bytes) -> dict:
    endian, directory, layout = read_directory(data)
    needed = (TEXDATA_LUMP, TEXINFO_LUMP, STRINGS_LUMP, TABLE_LUMP)
    blocks = {n: read_lump(data, directory[n], endian) for n in needed}
    texdata, texinfo, strings, table = (blocks[n] for n in needed)
    if not texdata or len(texdata) % 32:
        raise BspError(f"Unexpected texdata structure size: {len(texdata)} (expected 32-byte records)")
    if not texinfo or len(texinfo) % 72:
        raise BspError(f"Unexpected texinfo structure size: {len(texinfo)} (expected 72-byte records)")
    if not table or len(table) % 4:
        raise BspError(f"Unexpected string-table size: {len(table)} (expected 4-byte offsets)")
    table_refs = [r[0] for r in struct.iter_unpack(endian+"i", table)]
    names = texture_strings(strings, endian, len(table_refs), table_refs)
    texdata_names = []
    for i in range(len(texdata)//32):
        ref = struct.unpack_from(endian+"i",texdata,32*i+12)[0]
        if not 0 <= ref < len(names):
            raise BspError(f"Invalid texdata name table id {ref} at texture {i}")
        texdata_names.append(names[ref])
    texinfos = []
    for i in range(len(texinfo)//72):
        flags, texdata_id = struct.unpack_from(endian+"ii", texinfo,72*i+64)
        if texdata_id < 0:
            texinfos.append(None)
        elif texdata_id >= len(texdata_names):
            raise BspError(f"texinfo {i} has invalid texture {texdata_id}")
        else:
            texinfos.append(texdata_names[texdata_id])
    face_index = next((n for n in (58,7,27) if directory[n]["size"]>0),None)
    if face_index is None:
        raise BspError("Missing Source face lump")
    faces = read_lump(data,directory[face_index],endian)
    if len(faces)%56:
        raise BspError(f"Unexpected dface_t size {len(faces)}; expected 56-byte records")
    counts = Counter()
    missing = 0
    for ofs in range(0,len(faces),56):
        texinfo_id = struct.unpack_from(endian+"h",faces,ofs+10)[0]
        if texinfo_id < 0 or texinfo_id >= len(texinfos):
            missing += 1
            continue
        material = texinfos[texinfo_id]
        if material:
            counts[material] += 1
        else:
            missing += 1
    return {"magic":data[:4].decode("ascii"),"layout":layout,
            "face_lump":face_index,"face_count":len(faces)//56,
            "texture_data_count":len(texdata_names),
            "texinfo_count":len(texinfos),"unique_materials":len(counts),
            "unmapped_faces":missing,"materials":counts}


def inspect_zip_directory(path: Path, print_count: int=MAX_PRINTED) -> dict:
    with zipfile.ZipFile(path) as archive:
        info=archive.infolist()
        if len(info)>MAX_ZIP_ENTRIES:
            raise ValueError(f"Archive listing has more than {MAX_ZIP_ENTRIES} entries")
        suffixes=Counter()
        samples=[]
        for entry in info:
            if entry.is_dir():
                continue
            suffix=Path(entry.filename).suffix.lower()
            suffixes[suffix]+=1
            if suffix in MATERIAL_FILE_EXTENSIONS and len(samples)<print_count:
                samples.append(entry.filename)
        return {"files":sum(suffixes.values()),"suffixes":suffixes,
                "sample_assets":samples}


def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bsp",type=Path,default=MAP)
    p.add_argument("--pack",action="store_true",
                   help="Also list ZIP directory metadata for local left4dead2/zip0.360.zip")
    p.add_argument("--limit",type=int,default=14,
                   help="Number of material names to show (1-50)")
    args=p.parse_args()
    if not 1<=args.limit<=50:
        p.error("--limit must be 1..50")
    try:
        path=args.bsp.expanduser().resolve()
        result=inspect_materials(path.read_bytes())
        print(f"MAP: {path.name} ({result['magic']}, layout {result['layout']})")
        print(f"Texture records: {result['texture_data_count']:,}; "
              f"texinfos: {result['texinfo_count']:,}; faces: {result['face_count']:,}")
        print(f"Face source: lump {result['face_lump']}; "
              f"distinct referenced materials: {result['unique_materials']:,}; "
              f"unmapped faces: {result['unmapped_faces']:,}")
        print("MOST REFERENCED ORIGINAL MATERIALS:")
        for name,count in result["materials"].most_common(args.limit):
            print(f"  {count:>5} faces  {name}")
        if args.pack:
            pack=ROOT/"game-extracted"/"left4dead2"/"zip0.360.zip"
            print(f"\nARCHIVE DIRECTORY: {pack.name} ({pack.stat().st_size:,} bytes)")
            try:
                listing=inspect_zip_directory(pack)
                print(f"Files listed: {listing['files']:,}")
                for suffix,count in listing["suffixes"].most_common(15):
                    print(f"  {suffix or '(none)':<8} {count:>7,}")
                print("Sample model/material filenames (if present):")
                for name in listing["sample_assets"]:print("  "+name)
            except (zipfile.BadZipFile,zipfile.LargeZipFile,NotImplementedError,ValueError) as error:
                print(f"  Standard ZIP reader rejected extra data: {error}")
                print("  Trying the bounded Xbox ZIP directory reader...")
                try:
                    metadata=inspect_xbox_zip(pack)
                    print(f"  Xbox directory entries: {metadata['count']:,}; "
                          f"extra bytes skipped: {metadata['skipped_extra_bytes']:,}")
                    for suffix,count in metadata["extension_counts"].most_common(15):
                        print(f"    {suffix or '(none)':<9} {count:>7,}")
                    filenames={name.replace('\\','/').casefold()
                               for name in metadata["filenames"]}
                    matches = [(name,faces) for name,faces in result["materials"].items()
                               if ("materials/"+name.replace('\\','/').lower()+".vmt").casefold()
                               in filenames]
                    print(f"  BSP material VMT names matched in this ZIP: "
                          f"{len(matches)}/{result['unique_materials']} "
                          f"({sum(faces for _name,faces in matches):,} face references)")
                    print("  Matching materials (up to 12):")
                    for name,_faces in sorted(matches)[:12]:
                        print("    "+name)
                    print("  Sample asset paths:")
                    for name in metadata["sample_assets"][:args.limit]:
                        print("    "+name)
                except (XboxZipError, OSError) as extra_error:
                    print(f"  Xbox ZIP directory probe also stopped: {extra_error}")
                    print("  Report this diagnostic; original archive remains untouched.")
        print("\nInspection complete. No commercial game data exported or uploaded.")
        return 0
    except (OSError,ValueError,BspError,struct.error) as error:
        print(f"Material inspection stopped: {error}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
