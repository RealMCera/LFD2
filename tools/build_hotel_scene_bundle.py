#!/usr/bin/env python3
"""Batch convert every referenced original c1m1 hotel studio prop from Xbox ZIP.

ONE local command, not one command per furniture item. Scans the original
archive central directory once and converts all unique referenced MDL/VVD/VTX
sets with the original Source geometry decoder. Unsupported models are reported
and skipped, never replaced with fake boxes. Outputs go to an ignored PRIVATE
folder with one scene.json and one mesh JSON per successfully decoded model.

    py tools/build_hotel_scene_bundle.py --run

The folder is meant for a single Chrome directory-picker load. Does not
upload, commit, or write any original Valve-owned game data to the repository.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

try:
    from .bsp_to_browser_mesh import ROOT,BspError
    from .build_hotel_prop_manifest import DEFAULT_OUTPUT as PLACEMENTS
    from .inspect_hotel_model_assets import PACK,model_files
    from .probe_original_hotel_model import (
        bounded_member,decode_xbox_mdl,validate_name,
    )
    from .scan_xbox_zip_directory import scan_xbox_zip
    from .inspect_xbox_zip import XboxZipError
    from .convert_original_hotel_chair import convert_original_model
except ImportError:
    from bsp_to_browser_mesh import ROOT,BspError
    from build_hotel_prop_manifest import DEFAULT_OUTPUT as PLACEMENTS
    from inspect_hotel_model_assets import PACK,model_files
    from probe_original_hotel_model import (
        bounded_member,decode_xbox_mdl,validate_name,
    )
    from scan_xbox_zip_directory import scan_xbox_zip
    from inspect_xbox_zip import XboxZipError
    from convert_original_hotel_chair import convert_original_model

PRIVATE=(ROOT/"research"/"local").resolve()
DEFAULT_FOLDER=PRIVATE/"hotel-auto-props"
MAX_REFERENCED=4000
MAX_PACKAGE_MODELS=4000
MAX_FILE_BYTES=50*1024*1024


def load_placements(source: Path) -> tuple[list[dict],list[str]]:
    data=json.loads(source.read_text(encoding="utf-8"))
    if (data.get("format")!="lfd2-original-prop-placements-v1"
        or data.get("source_map")!="c1m1_hotel.360.bsp"
        or not isinstance(data.get("placements"),list)
        or not 1<=len(data["placements"])<=100000):
        raise ValueError("Expected verified private hotel-all-props.json manifest")
    names=set()
    for item in data["placements"]:
        name=validate_name(item["model"])
        xyz=item.get("origin")
        angles=item.get("angles")
        if (not isinstance(xyz,list) or len(xyz)!=3 or
            not isinstance(angles,list) or len(angles)!=3 or
            not all(isinstance(x,(int,float)) and -1e6<x<1e6
                    for x in xyz+angles)):
            raise ValueError("Invalid original BSP prop placement transform")
        names.add(name)
    if len(names)>MAX_REFERENCED:
        raise ValueError("Too many original referenced models")
    return data["placements"],sorted(names)


def archive_index(entries: list[dict]) -> tuple[dict,set]:
    index={};duplicate=set()
    for entry in entries:
        name=entry["name"].replace("\\","/").casefold()
        if name in index:duplicate.add(name)
        else:index[name]=entry
    return index,duplicate


def choose_trio(name: str, index: dict, duplicate: set) -> dict:
    choices=model_files(validate_name(name))
    result={}
    for kind in ("mdl","vvd","vtx"):
        selected=[index[c] for c in choices[kind]
                  if c in index and c not in duplicate]
        if len(selected)!=1:
            raise ValueError(f"{kind} companion ambiguous or absent ({len(selected)} matches)")
        result[kind]=selected[0]
    return result


def read_asset(stream, filesize: int, directory_offset: int, entry: dict) -> bytes:
    record=bounded_member(stream,filesize,directory_offset,entry)
    if entry["name"].casefold().endswith(".mdl"):
        return decode_xbox_mdl(stream,record)
    stream.seek(record["offset"])
    payload=stream.read(record["length"])
    if len(payload)!=record["length"]:
        raise XboxZipError("Short local Xbox ZIP model payload read")
    return payload


def build_bundle(source_zip: Path, manifest: Path, output: Path,
                 limit: int = 0) -> dict:
    """Write a PRIVATE atomic scene folder; skip unsupported per-model sets."""
    target=output.expanduser().resolve()
    if not target.is_relative_to(PRIVATE) or target==PRIVATE or target.exists():
        raise ValueError("Output must be a new folder under ignored research/local")
    placements,names=load_placements(manifest)
    if limit<0 or limit>MAX_PACKAGE_MODELS:
        raise ValueError("Model limit out of range")
    if limit:names=names[:limit]
    if not names:raise ValueError("No original model references to convert")
    report=scan_xbox_zip(source_zip)
    index,duplicate=archive_index(report["entries"])
    filesize=source_zip.stat().st_size
    ok=[];failed=[]
    total_placements=Counter(p["model"].casefold() for p in placements)
    PRIVATE.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix=".studio-build-",dir=PRIVATE))
    try:
        models_dir=staging/"models"
        models_dir.mkdir()
        with source_zip.open("rb") as stream:
            for position,name in enumerate(names,1):
                try:
                    trio=choose_trio(name,index,duplicate)
                    mdl=read_asset(stream,filesize,report["directory_offset"],trio["mdl"])
                    vvd=read_asset(stream,filesize,report["directory_offset"],trio["vvd"])
                    vtx=read_asset(stream,filesize,report["directory_offset"],trio["vtx"])
                    mesh=convert_original_model(mdl,vvd,vtx,model_name=name)
                    # No file paths derived directly from ZIP filenames.
                    file_id=hashlib.sha256(name.encode("ascii")).hexdigest()[:24]
                    basename=file_id+".mesh.json"
                    meshfile=models_dir/basename
                    body=json.dumps(mesh,separators=(",",":"),allow_nan=False)
                    if len(body.encode("utf-8"))>MAX_FILE_BYTES:
                        raise BspError("Model exceeds private mesh output size limit")
                    meshfile.write_text(body,encoding="utf-8")
                    ok.append({"model":name,"file":"models/"+basename,
                               "vertices":mesh["vertex_count"],
                               "triangles":mesh["triangle_count"],
                               "placements":total_placements[name],
                               "checksum":mesh["checksum"]})
                except (OSError,ValueError,BspError,XboxZipError,KeyError,
                        TypeError,OverflowError) as exc:
                    failed.append({"model":name,"error":str(exc)[:240]})
                if position%20==0 or position==len(names):
                    print(f"  {position}/{len(names)} original models inspected; "
                          f"{len(ok)} decoded, {len(failed)} skipped",flush=True)
        if not ok:
            raise ValueError("None of the original referenced models could be decoded; "
                             "no scene bundle exported")
        success={x["model"] for x in ok}
        active=[p for p in placements if p["model"].casefold() in success
                and not p.get("disabled_on_xbox",False)]
        scene={"format":"lfd2-original-hotel-studio-bundle-v1",
               "source_map":"c1m1_hotel.360.bsp",
               "models":ok,"placements":active,
               "stats":{"attempted_models":len(names),"decoded_models":len(ok),
                        "skipped_models":len(failed),
                        "original_placements_included":len(active),
                        "original_placements_total":len(placements)},
               "skipped":failed,
               "note":"Original Xbox studio geometry only; no converted model textures/animation."}
        (staging/"scene.json").write_text(
            json.dumps(scene,separators=(",",":"),allow_nan=False),
            encoding="utf-8")
        # Windows and Linux support renaming an entire local folder atomically
        # after all model files are safely written; never overwrite.
        if target.exists():
            raise ValueError("Output folder appeared during conversion")
        os.rename(staging,target)
        print("PRIVATE SCENE FOLDER:",target)
        print("Original decoded models:",len(ok),"/",len(names))
        print("Original placements with decoded models:",len(active),"/",len(placements))
        print("Skipped original model formats:",len(failed),
              "(reasons in PRIVATE scene.json)")
        print("Browser: open local hotel BSP mesh, then select this entire folder once.")
        print("All original model geometry stays PRIVATE; no GitHub asset upload.")
        return scene
    finally:
        if staging.exists():shutil.rmtree(staging)


def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack",type=Path,default=PACK)
    parser.add_argument("--manifest",type=Path,default=PLACEMENTS)
    parser.add_argument("--output",type=Path,default=DEFAULT_FOLDER)
    parser.add_argument("--limit",type=int,default=0,
                        help="Convert first N sorted referenced models; default 0 = ALL")
    parser.add_argument("--run",action="store_true",
                        help="Write ALL supported private model meshes in one batch")
    args=parser.parse_args()
    try:
        if (not args.pack.expanduser().resolve().is_relative_to(ROOT) or
            not args.manifest.expanduser().resolve().is_relative_to(PRIVATE)):
            raise ValueError("Original archive must be local; manifest under research/local")
        if not args.run:
            placements,names=load_placements(args.manifest)
            print(f"Hotel models referenced: {len(names)} unique; "
                  f"{len(placements)} original placements")
            print("Read-only planning. --run batches every model into one private folder.")
            return 0
        build_bundle(args.pack,args.manifest,args.output,args.limit)
        return 0
    except (OSError,ValueError,XboxZipError,BspError,
            json.JSONDecodeError) as exc:
        print("Original batch pipeline stopped:",str(exc),file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
