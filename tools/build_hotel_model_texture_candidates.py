#!/usr/bin/env python3
"""Automatically convert Xbox model texture files with exact-name candidates.

Important: Xbox studio VMT scripts use an unidentified binary representation
(observed 0xaa4ff4d8 prefix). This program does NOT claim to interpret its
material parameters. If an original MDL material path corresponds exactly to
both a binary VMT and a uniquely indexed VTFX of the SAME original name, that
file is a provisional filename-based diffuse preview, NOT a verified shader
mapping. Never substitutes similar names or unrelated textures.

Dry-run by default. --run extracts/decodes unique VTFX candidates in a new
private folder, reusing the project's existing local VTFX PNG converter.
No copyrighted assets go to GitHub.
"""
from __future__ import annotations

import argparse
from collections import Counter
import io
import json
from pathlib import Path
import subprocess
import sys

try:
    from .bsp_to_browser_mesh import ROOT,MAP,BspError,read_directory,read_lump
    from .inventory_hotel_studio_materials import PACK,PLACEMENTS,PRIVATE,inventory_models
    from .finish_hotel_materials import (
        ZIP1,DEFAULT_CONVERTER,map_sources,pick_source,read_local_member,
        make_texture,normalize_material
    )
    from .scan_xbox_zip_directory import scan_xbox_zip,scan_directory
    from .inspect_xbox_zip import XboxZipError
except ImportError:
    from bsp_to_browser_mesh import ROOT,MAP,BspError,read_directory,read_lump
    from inventory_hotel_studio_materials import PACK,PLACEMENTS,PRIVATE,inventory_models
    from finish_hotel_materials import (
        ZIP1,DEFAULT_CONVERTER,map_sources,pick_source,read_local_member,
        make_texture,normalize_material
    )
    from scan_xbox_zip_directory import scan_xbox_zip,scan_directory
    from inspect_xbox_zip import XboxZipError

OUTPUT=PRIVATE/"hotel-model-textures-v1"
PREFIX=bytes.fromhex("aa4ff4d8")
MAX_TEXTURES=1000


def plan_provisional(models: list[dict], tables:dict, loader)->dict:
    """Match only original studio CDTexture candidate + same-name VMT/VTFX.

    A filename association is not validation of material shader properties.
    """
    vmt_cache={}
    slots=[];unresolved=[]
    for row in models:
        model=row["model"]
        for slot,paths in enumerate(row["texture_candidates"]):
            selected=None;reason="no_exact_vmt_and_vtfx_name"
            for path in paths:
                name=normalize_material(path)
                vmt=pick_source(tables,"vmt",name)
                tex=pick_source(tables,"vtfx",name)
                if not vmt or not tex:
                    continue
                label,item=vmt
                key=(label,item["name"])
                try:
                    if key not in vmt_cache:
                        raw=loader(label,item)
                        vmt_cache[key]=raw[:4]
                    prefix=vmt_cache[key]
                except (OSError,ValueError,XboxZipError):
                    reason="vmt_read_failed"
                    continue
                if prefix != PREFIX:
                    reason="vmt_not_observed_binary_family"
                    continue
                selected={
                    "model":model,"slot":slot,"material":name,
                    "texture":name,"vtfx_source":tex[0],
                    "vtfx_file":tex[1]["name"],
                    "original_placements":row.get("original_placements",0),
                    "mapping":"PROVISIONAL_EXACT_FILENAME_NOT_VMT_VERIFIED"
                }
                break
            if selected:slots.append(selected)
            else:unresolved.append({"model":model,"slot":slot,"reason":reason})
    return {"format":"lfd2-original-hotel-provisional-material-filenames-v1",
            "matches":slots,"unresolved":unresolved,
            "stats":{"candidate_slots":len(slots),
                     "unresolved_slots":len(unresolved),
                     "unique_image_names":len({item["texture"] for item in slots})}}


def prepare(zip_path:Path,bsp_path:Path,model_pack:Path,manifest:Path,
            output:Path,converter:Path,run:bool=False,max_textures:int=300)->dict:
    if not 1<=max_textures<=MAX_TEXTURES:
        raise ValueError("max-textures outside 1..1000")
    output=output.expanduser().resolve()
    if not output.is_relative_to(PRIVATE) or output==PRIVATE:
        raise ValueError("Output must be a dedicated ignored private research/local folder")
    if run and output.exists():
        raise ValueError("Output folder already exists; choose a NEW private --output directory")
    catalog=inventory_models(model_pack,manifest)
    zip_report=scan_xbox_zip(zip_path)
    bsp=bsp_path.read_bytes()
    endian,directory,_=read_directory(bsp)
    pak=read_lump(bsp,directory[40],endian)
    if not pak or len(pak)>64*1024*1024:
        raise ValueError("Original hotel BSP PAK missing or too large")
    pak_report=scan_directory(io.BytesIO(pak),len(pak))
    tables=map_sources(zip_report,pak_report)
    with zip_path.open("rb") as archive,io.BytesIO(pak) as mapfile:
        handles={"zip1":(archive,zip_path.stat().st_size,
                         zip_report["directory_offset"]),
                 "map":(mapfile,len(pak),pak_report["directory_offset"])}
        def read_vmt(label,entry):
            stream,size,at=handles[label]
            return read_local_member(stream,size,at,entry)
        planned=plan_provisional(catalog["models"],tables,read_vmt)
        targets=sorted({entry["texture"] for entry in planned["matches"]})
        print("ORIGINAL XBOX HOTEL MODEL TEXTURE EXACT-NAME CANDIDATES")
        print("Total studio model types:",catalog["model_count"])
        print("Studio material headers readable:",catalog["models_with_readable_material_header"])
        print("Candidate model material slots:",planned["stats"]["candidate_slots"])
        print("Unresolved model material slots:",planned["stats"]["unresolved_slots"])
        print("Unique exact-name image files:",len(targets))
        print("Original VMT binary signature:",PREFIX.hex(" "))
        print("CAUTION: these are provisional filename matches; Xbox VMT shader references are still undecoded.")
        if not run:
            print("Read-only. --run extracts and converts unique real Xbox VTFX candidates in a NEW private folder.")
            return planned
        output.mkdir(parents=True)
        created={};errors={}
        for seq,name in enumerate(targets[:max_textures],1):
            selected=pick_source(tables,"vtfx",name)
            if selected is None:
                errors[name]="no_unique_original_vtfx"
                continue
            label,entry=selected
            stream,size,at=handles[label]
            try:
                rel,kind=make_texture(stream,size,at,entry,name,output,
                                      converter,allow_cached=False)
                created[name]=rel
                print(f"  {seq}/{min(len(targets),max_textures)} {kind}: {name}",flush=True)
            except (OSError,ValueError,XboxZipError,
                    subprocess.CalledProcessError,subprocess.TimeoutExpired) as e:
                errors[name]=str(e)[:180]
                print(f"  {seq}/{min(len(targets),max_textures)} unavailable: {name} ({str(e)[:100]})",flush=True)
        model_slots=[]
        for slot in planned["matches"]:
            if slot["texture"] in created:
                model_slots.append({
                    "model":slot["model"],"slot":slot["slot"],
                    "texture":slot["texture"],"png":created[slot["texture"]],
                    "mapping":slot["mapping"]
                })
        result={
            "format":"lfd2-original-hotel-provisional-model-textures-v1",
            "source_scene":"hotel-auto-props-v2/scene.json",
            "method":"provisional exact same-name VMT and VTFX; binary VMT shader unverified",
            "models":model_slots,
            "summary":{"model_material_slots_ready":len(model_slots),
                       "unique_original_images_converted":len(created),
                       "original_texture_files_unavailable":len(errors),
                       "unresolved_studio_material_slots":planned["stats"]["unresolved_slots"]},
            "errors":errors
        }
        (output/"texture-manifest.json").write_text(
            json.dumps(result,separators=(",",":")),encoding="utf-8")
        print("PRIVATE ORIGINAL MODEL TEXTURE FOLDER:",output)
        print("TEXTURE SUMMARY:",result["summary"])
        print("Original game files stay local; models and previous scene are unchanged.")
        return result


def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run",action="store_true",help="Convert all exact-name original VTFX candidates privately")
    p.add_argument("--model-pack",type=Path,default=PACK)
    p.add_argument("--manifest",type=Path,default=PLACEMENTS)
    p.add_argument("--material-pack",type=Path,default=ZIP1)
    p.add_argument("--bsp",type=Path,default=MAP)
    p.add_argument("--converter",type=Path,default=DEFAULT_CONVERTER)
    p.add_argument("--output",type=Path,default=OUTPUT)
    p.add_argument("--max-textures",type=int,default=300)
    args=p.parse_args()
    try:
        paths=[args.model_pack.expanduser().resolve(),
               args.manifest.expanduser().resolve(),
               args.material_pack.expanduser().resolve(),
               args.bsp.expanduser().resolve()]
        if not all(p.is_relative_to(ROOT) for p in paths) or not paths[1].is_relative_to(PRIVATE):
            raise ValueError("Original sources must stay local and placement manifest private")
        prepare(paths[2],paths[3],paths[0],paths[1],args.output,
                args.converter.expanduser().resolve(),
                run=args.run,max_textures=args.max_textures)
        return 0
    except (OSError,ValueError,BspError,XboxZipError,KeyError,TypeError,
            json.JSONDecodeError) as e:
        print("Original studio texture batch stopped:",e,file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
