#!/usr/bin/env python3
"""Inventory original Source studio material references for ALL hotel prop models.

ONE read-only pass of the owner's Xbox ZIP, not one run per prop. It reads
only model MDL header bytes, never uploads game files, paints invented texture,
or writes converted geometry. No private output unless --export is requested.

Next phase: resolve these genuine studio material paths against original
VMT/VTFX archives and apply them via the existing private WebGL pipeline.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

try:
    from .bsp_to_browser_mesh import ROOT,BspError
    from .build_hotel_scene_bundle import (
        PRIVATE, PLACEMENTS, PACK, load_placements,archive_index,
        choose_trio,read_asset
    )
    from .scan_xbox_zip_directory import scan_xbox_zip
    from .probe_original_hotel_model import parse_source_header,validate_name
    from .inspect_xbox_zip import XboxZipError
except ImportError:
    from bsp_to_browser_mesh import ROOT,BspError
    from build_hotel_scene_bundle import (
        PRIVATE, PLACEMENTS, PACK, load_placements,archive_index,
        choose_trio,read_asset
    )
    from scan_xbox_zip_directory import scan_xbox_zip
    from probe_original_hotel_model import parse_source_header,validate_name
    from inspect_xbox_zip import XboxZipError

DEFAULT_OUT=PRIVATE/"hotel-studio-materials.json"
MAX_TEXTURES=1024
MAX_PATHS=1024
MAX_SKIN_REFS=1024
MAX_SKIN_FAMILIES=128
MAX_STRING_BYTES=256
NAME_PATTERN=re.compile(r"^[a-z0-9_./-]+$")


def get_int(data: bytes, at: int, order: str, signed: bool=False) -> int:
    if at<0 or at+4>len(data):
        raise BspError("Truncated original studio material table")
    return int.from_bytes(data[at:at+4],order,
                          signed=signed)


def get_short(data: bytes, at: int, order: str) -> int:
    if at<0 or at+2>len(data):
        raise BspError("Truncated original studio skin family")
    return int.from_bytes(data[at:at+2],order)


def bounded_array(data: bytes, at: int, count: int, stride: int,
                  limit: int, label: str) -> None:
    if not (0<=count<=limit and
            (count==0 or 0<at<len(data)) and
            0<=at<=len(data) and at+count*stride<=len(data)):
        raise BspError(f"{label} exceeds original MDL bounds")


def original_path(data: bytes, start: int, *, may_be_empty=False) -> str:
    if not 0<=start<len(data):
        raise BspError("Original MDL material string offset out of range")
    end=data.find(b"\0",start,min(len(data),start+MAX_STRING_BYTES))
    if end<0:
        raise BspError("Unterminated or excessive original MDL material string")
    try:
        result=data[start:end].decode("ascii").replace("\\","/").casefold().strip()
    except UnicodeDecodeError as exc:
        raise BspError("Unsupported original studio material encoding") from exc
    if not result:
        if may_be_empty:return ""
        raise BspError("Empty studio material name")
    result=result.strip("/")
    if not NAME_PATTERN.fullmatch(result) or (
        any(part in (".","..","") for part in result.split("/"))
    ):
        raise BspError("Unsafe original studio material name")
    return result


def inspect_studio_materials(mdl: bytes, model: str) -> dict:
    """Source v49: 64-byte mstudiotexture_t, root-relative cdtexture offsets.

    The model mesh's material ID is a *skin table column*, not necessarily
    an index into the base material array. Preserve skin families explicitly.
    """
    model=validate_name(model)
    if len(mdl)<408:
        raise BspError("Original studio header too small for material inventory")
    header=parse_source_header(mdl[:64],"mdl")
    if header.get("version")!=49 or header.get("endian") not in ("big","little"):
        raise BspError("Unsupported original Source MDL material header")
    order=header["endian"]
    count,texture_at=(get_int(mdl,at,order) for at in (204,208))
    npaths,path_at=(get_int(mdl,at,order) for at in (212,216))
    nskin,skin_families,skin_at=(get_int(mdl,at,order)
                                 for at in (220,224,228))
    bounded_array(mdl,texture_at,count,64,MAX_TEXTURES,"studio textures")
    bounded_array(mdl,path_at,npaths,4,MAX_PATHS,"studio material paths")
    if nskin>MAX_SKIN_REFS or skin_families>MAX_SKIN_FAMILIES:
        raise BspError("Excessive original studio skin table")
    if nskin and skin_families:
        bounded_array(mdl,skin_at,nskin*skin_families,2,
                      MAX_SKIN_REFS*MAX_SKIN_FAMILIES,"studio skin references")
    else:
        if nskin or skin_families:
            raise BspError("Incomplete original studio skin family dimensions")
    names=[]
    for i in range(count):
        row=texture_at+i*64
        relative=get_int(mdl,row,order,signed=True)
        names.append(original_path(mdl,row+relative))
    paths=[]
    for i in range(npaths):
        at=get_int(mdl,path_at+i*4,order,signed=True)
        paths.append(original_path(mdl,at,may_be_empty=True))
    skins=[]
    for family in range(skin_families):
        row=[]
        for slot in range(nskin):
            idx=get_short(mdl,skin_at+(family*nskin+slot)*2,order)
            if idx>=count:
                raise BspError("Studio skin family references missing texture")
            row.append(idx)
        skins.append(row)
    candidates=[]
    for name in names:
        entries=[]
        for base in paths or [""]:
            full=(base.rstrip("/")+"/"+name) if base else name
            if NAME_PATTERN.fullmatch(full) and (
                not any(part in (".","..","") for part in full.split("/"))
            ) and full not in entries:
                entries.append(full)
        candidates.append(entries)
    return {
        "model":model,"checksum":header["checksum"],
        "texture_names":names,"search_paths":paths,
        "skin_families":skins,"texture_candidates":candidates,
        "note":"Unresolved original Source VMT paths, not recovered VTFX image data."
    }


def inventory_models(zip_path: Path, manifest_path: Path) -> dict:
    placements,models=load_placements(manifest_path)
    report=scan_xbox_zip(zip_path)
    index,duplicates=archive_index(report["entries"])
    filesize=zip_path.stat().st_size
    placed=Counter(p["model"].casefold() for p in placements)
    accepted=[];skipped=[]
    with zip_path.open("rb") as stream:
        for model in models:
            try:
                trio=choose_trio(model,index,duplicates)
                mdl=read_asset(stream,filesize,report["directory_offset"],
                               trio["mdl"])
                item=inspect_studio_materials(mdl,model)
                item["original_placements"]=placed[model]
                accepted.append(item)
            except (ValueError,OSError,BspError,XboxZipError) as exc:
                skipped.append({"model":model,"error":str(exc)[:220]})
    return {
        "format":"lfd2-original-studio-material-reference-catalog-v1",
        "source":"local Xbox studio MDLs; material paths not yet resolved",
        "model_count":len(models),
        "models_with_readable_material_header":len(accepted),
        "models_skipped":len(skipped),
        "unique_material_path_candidates":len({
            path for item in accepted
            for group in item["texture_candidates"] for path in group
        }),
        "models":accepted,"skipped":skipped
    }


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pack",type=Path,default=PACK)
    p.add_argument("--manifest",type=Path,default=PLACEMENTS)
    p.add_argument("--output",type=Path,default=DEFAULT_OUT)
    p.add_argument("--export",action="store_true",
                   help="Save material-name metadata privately; no image extraction")
    args=p.parse_args()
    try:
        path=args.pack.expanduser().resolve()
        manifest=args.manifest.expanduser().resolve()
        if not path.is_relative_to(ROOT) or not manifest.is_relative_to(PRIVATE):
            raise ValueError("Inputs must stay in local game extraction and research/local")
        result=inventory_models(path,manifest)
        print("AUTOMATIC ORIGINAL XBOX HOTEL STUDIO MATERIAL INVENTORY")
        print("Original models examined:",result["model_count"])
        print("Model headers with readable materials:",
              result["models_with_readable_material_header"])
        print("Model headers rejected:",result["models_skipped"])
        print("Original candidate material paths:",
              result["unique_material_path_candidates"])
        weighted=Counter()
        for item in result["models"]:
            for candidates in item["texture_candidates"]:
                for name in candidates:weighted[name]+=item["original_placements"]
        print("Most-reused model material path candidates:")
        for name,weight in weighted.most_common(12):
            print(f"  {weight:>4} original prop uses | {name}")
        print("First unsupported original material table types:")
        for item in result["skipped"][:6]:
            print("  ",item["model"],":",item["error"])
        if args.export:
            target=args.output.expanduser().resolve()
            if not target.is_relative_to(PRIVATE) or target==PRIVATE or target.exists():
                raise ValueError("Output must be a new file under research/local")
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(json.dumps(result,separators=(",",":")),
                              encoding="utf-8")
            print("PRIVATE MATERIAL REFERENCE CATALOG:",target)
        else:
            print("Read-only. Use --export only to save private material names.")
        print("No original model textures extracted, published or uploaded.")
        return 0
    except (OSError,ValueError,json.JSONDecodeError,BspError,XboxZipError) as exc:
        print("Original studio material inventory stopped:",exc,file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
