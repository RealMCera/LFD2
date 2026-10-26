#!/usr/bin/env python3
"""Prepare a small set of genuine Xbox hotel textures for local Chrome preview.

Default --list: read only the private map + Xbox ZIP central directory.
--run: opt-in, copies up to --count validated original VTFX files under
gitignored research/local/hotel-textures, invokes the user's trusted local
vtfx_reader.exe per file, and copies *one matching-size PNG per material*
into a flat private PNG folder for Chrome multi-select. No uploads/network,
bulk archive extraction, output overwrites, or game file modifications.

This is an experimental direct-name texture preview, NOT VMT dependency
resolution: a material's actual $basetexture may refer to another image.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import shutil
import sys

try:
    from .bsp_to_browser_mesh import ROOT, MAP
    from .inspect_map_materials import inspect_materials
    from .scan_xbox_zip_directory import scan_xbox_zip
    from .scan_source_asset_packs import material_key
    from .extract_single_vtfx import ZIP1, validate_texture, XboxZipError
    from .convert_local_vtfx import run_converter, DEFAULT_CONVERTER, ConversionError
except ImportError:
    from bsp_to_browser_mesh import ROOT, MAP
    from inspect_map_materials import inspect_materials
    from scan_xbox_zip_directory import scan_xbox_zip
    from scan_source_asset_packs import material_key
    from extract_single_vtfx import ZIP1, validate_texture, XboxZipError
    from convert_local_vtfx import run_converter, DEFAULT_CONVERTER, ConversionError

PRIVATE_ROOT = (ROOT / "research" / "local").resolve()
DESTINATION = PRIVATE_ROOT / "hotel-textures"
SKIP_PREFIXES=("tools/","dev/","sky/","effects/","particle/")


def choose_materials(faces: Counter, entries: list[dict], count: int) -> list[tuple[str,int,dict]]:
    """Select popular visible Source materials with exact-name Xbox VTFXs."""
    by_name={}
    duplicates=set()
    for item in entries:
        if not item["name"].casefold().endswith(".360.vtf"):
            continue
        key=material_key(item["name"])
        if key in by_name: duplicates.add(key)
        else: by_name[key]=item
    choices=[]
    for raw,faces_count in sorted(faces.items(),key=lambda x:(-x[1],x[0])):
        key=raw.casefold().replace("\\","/")
        if key.startswith(SKIP_PREFIXES) or key in duplicates: continue
        if key in by_name: choices.append((key,faces_count,by_name[key]))
        if len(choices)>=count:break
    return choices


def asset_paths(key: str, root: Path) -> tuple[Path,Path,Path]:
    """Prevent manipulated material names escaping private output paths."""
    components=key.split("/")
    if (not components or any(not c or c in (".","..") or
         not all(ch.isascii() and (ch.isalnum() or ch in "_-") for ch in c)
         for c in components)):
        raise ValueError(f"Unsafe Source material path: {key}")
    orig=root/"vtfx"/("/".join(components)+".360.vtf")
    temp=root/"work"/("/".join(components))
    flat=root/"png"/(components[-1]+".360_resource_0.png")
    for path in (orig,temp,flat):
        if not path.resolve().is_relative_to(PRIVATE_ROOT):
            raise ValueError("Output path escapes private research/local")
    return orig,temp,flat


def process_one(stream, filesize: int, central_offset: int,
                entry: dict, key: str, root: Path, converter: Path) -> tuple[str,Path]:
    vtfx_path, work, final=asset_paths(key,root)
    if final.exists():
        return "existing_png",final
    record=validate_texture(stream,filesize,central_offset,entry)
    if not vtfx_path.exists():
        vtfx_path.parent.mkdir(parents=True,exist_ok=True)
        stream.seek(record["offset"])
        with vtfx_path.open("xb") as dest:
            remaining=record["bytes"]
            while remaining:
                chunk=stream.read(min(65536,remaining))
                if not chunk:raise XboxZipError("Short original ZIP member data")
                dest.write(chunk);remaining-=len(chunk)
    elif vtfx_path.stat().st_size!=record["bytes"]:
        raise XboxZipError("Existing VTFX size does not match archive; overwrite refused")
    if work.is_dir() and any(work.iterdir()):
        # Recover from a completed previous conversion, but never overwrite.
        from_saved=sorted(work.rglob("*.png"))
        w,h=record["header"]["width"],record["header"]["height"]
        from_checked=[]
        try:
            from .convert_local_vtfx import png_dimensions
        except ImportError:
            from convert_local_vtfx import png_dimensions
        for image in from_saved:
            if png_dimensions(image)==(w,h):from_checked.append(image)
        if not from_checked:
            raise ConversionError("Previous conversion work folder is nonempty; inspect manually")
        results=[(from_checked[0],w,h)]
    else:
        results=run_converter(vtfx_path,work,converter)
    candidates=[item for item in results if item[1:]==
                (record["header"]["width"],record["header"]["height"])]
    if not candidates:raise ConversionError("No original-size PNG generated")
    image=candidates[0][0]
    final.parent.mkdir(parents=True,exist_ok=True)
    with image.open("rb") as src, final.open("xb") as dest:
        shutil.copyfileobj(src,dest,length=1<<20)
    return "converted",final


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run",action="store_true",
                   help="Explicitly extract and convert a small number of original VTFXs")
    p.add_argument("--count",type=int,default=8,help="Number of visual materials (1..16)")
    p.add_argument("--bsp",type=Path,default=MAP)
    p.add_argument("--zip",type=Path,default=ZIP1)
    p.add_argument("--converter",type=Path,default=DEFAULT_CONVERTER)
    args=p.parse_args()
    if not 1<=args.count<=16:p.error("--count must be 1..16")
    try:
        bsp=args.bsp.expanduser().resolve().read_bytes()
        faces=inspect_materials(bsp)["materials"]
        archive=args.zip.expanduser().resolve()
        report=scan_xbox_zip(archive)
        choices=choose_materials(faces,report["entries"],args.count)
        print(f"Hotel materials: {len(faces)}; selected images: {len(choices)} "
              f"from {archive.name} (no BSP game files uploaded)")
        for key,count,_entry in choices:print(f"  {count:>5} faces · {key}")
        if not args.run:
            print("Read-only selection. Add --run to convert into private hotel-textures/png/.")
            return 0
        converter=args.converter.expanduser().resolve()
        if not converter.is_file():
            raise ConversionError(f"Trusted local converter executable not found: {converter}")
        root=DESTINATION
        done=failed=0
        with archive.open("rb") as stream:
            filesize=archive.stat().st_size
            for key,_count,entry in choices:
                try:
                    state,path=process_one(stream,filesize,
                        report["directory_offset"],entry,key,root,converter)
                    print(f"  {state}: {path.name}");done+=1
                except (OSError,ValueError,XboxZipError,ConversionError) as error:
                    print(f"  skipped {key}: {error}");failed+=1
        print(f"Private PNGs available: {done}; unresolved: {failed}")
        print(f"Chrome multi-PNG folder: {root/'png'}")
        print("Select these PNGs together with Chrome's local file picker.")
        return 0 if done else 1
    except (OSError,ValueError,XboxZipError,ConversionError) as err:
        print(f"Local hotel texture setup stopped: {err}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
