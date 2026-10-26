#!/usr/bin/env python3
"""Decode original L4D2 Xbox v9 static prop PLACEMENTS and locate model packages.

Local original game data stays private. Scans all extracted Xbox 360 ZIP
directories, never extracts models. An opt-in --export writes only placement
metadata to ignored research/local/hotel-all-props.json. A successful static
record decode validates ALL prop IDs, leaf ranges and finite transforms.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
import json
import math
from pathlib import Path
import struct
import sys

try:
    from .bsp_to_browser_mesh import ROOT,MAP,BspError,read_directory,read_lump,decode_valve_lzma
    from .inspect_hotel_elements import (
        GAME_LUMP,STATIC_IDS,read_gamelump_directory,static_payload_candidates,
        parse_static_dictionary
    )
    from .inspect_hotel_model_assets import list_model_placements,model_files,model_availability
    from .scan_xbox_zip_directory import scan_xbox_zip
    from .inspect_xbox_zip import XboxZipError
except ImportError:
    from bsp_to_browser_mesh import ROOT,MAP,BspError,read_directory,read_lump,decode_valve_lzma
    from inspect_hotel_elements import (
        GAME_LUMP,STATIC_IDS,read_gamelump_directory,static_payload_candidates,
        parse_static_dictionary
    )
    from inspect_hotel_model_assets import list_model_placements,model_files,model_availability
    from scan_xbox_zip_directory import scan_xbox_zip
    from inspect_xbox_zip import XboxZipError

PACK_ROOT=ROOT/"game-extracted"
PRIVATE=(ROOT/"research"/"local").resolve()
DEFAULT_OUTPUT=PRIVATE/"hotel-all-props.json"
MAX_STATIC=100000
STATIC_V9_SIZE=72


def decode_v9_static_records(payload: bytes, endian: str) -> tuple[dict,list[dict]]:
    """L4D2 Source v9/72-byte records: origin, angles, model/leaf and flags.

    Check the complete array, never reinterpret a non-v9 or invalid byte
    sequence as usable world-space placements.
    """
    info=parse_static_dictionary(payload,endian)
    n=len(info["models"])
    at=4+n*128
    leaf_count=struct.unpack_from(endian+"I",payload,at)[0]
    at+=4+leaf_count*2
    count=struct.unpack_from(endian+"I",payload,at)[0]
    at+=4
    if (not 0<count<=MAX_STATIC or info["prop_bytes_remainder"]!=0 or
        len(payload)-at != count*STATIC_V9_SIZE):
        raise BspError("Source v9 static records do not have exact 72-byte stride")
    placements=[]
    for i in range(count):
        pos=at+i*STATIC_V9_SIZE
        origin=struct.unpack_from(endian+"3f",payload,pos)
        angles=struct.unpack_from(endian+"3f",payload,pos+12)
        model_id,leaf_first,leaves=struct.unpack_from(endian+"3H",payload,pos+24)
        skin=struct.unpack_from(endian+"i",payload,pos+32)[0]
        fade_min,fade_max=struct.unpack_from(endian+"2f",payload,pos+36)
        force_fade=struct.unpack_from(endian+"f",payload,pos+56)[0]
        disabled_xbox=bool(payload[pos+68])
        if (model_id>=n or leaf_first+leaves>leaf_count or
            not all(math.isfinite(v) and abs(v)<1000000 for v in origin) or
            not all(math.isfinite(v) and abs(v)<3601 for v in angles) or
            not all(math.isfinite(v) and abs(v)<1e8
                    for v in (fade_min,fade_max,force_fade))):
            raise BspError(f"Invalid static v9 placement record #{i}; refused entire array")
        placements.append({
            "class":"prop_static","model":info["models"][model_id].replace("\\","/").casefold(),
            "origin":[round(x,3) for x in origin],
            "angles":[round(x,3) for x in angles],
            "skin":skin,
            "leaf_count":leaves,
            "disabled_on_xbox":disabled_xbox,
        })
    return info,placements


def decode_static_from_bsp(bsp: bytes) -> tuple[dict,list[dict],list[str]]:
    endian,directory,_=read_directory(bsp)
    game=read_lump(bsp,directory[GAME_LUMP],endian)
    notes=[]
    for entry in read_gamelump_directory(game,endian):
        if entry["id_raw"] not in STATIC_IDS or entry["version"]!=9:
            continue
        for location,raw in static_payload_candidates(bsp,game,directory,entry):
            try:
                if entry["flags"] & 1:
                    if raw[:4]!=b"LZMA":
                        notes.append(f"{location}: no Valve LZMA header")
                        continue
                    data=decode_valve_lzma(raw,entry["length"],endian)
                else:
                    data=raw[:entry["length"]]
                info,placements=decode_v9_static_records(data,endian)
                if (not info["models"] or
                    any(not name.casefold().startswith("models/") or
                        not name.casefold().endswith(".mdl")
                        for name in info["models"])):
                    raise BspError("Decoded dictionary contains invalid MDL paths")
                return {"version":entry["version"],"location":location,
                        "model_count":len(info["models"]), "count":len(placements),
                        "record_stride":STATIC_V9_SIZE},placements,notes
            except (ValueError,struct.error,BspError) as err:
                notes.append(f"{location}: {str(err)[:180]}")
    raise BspError("Could not validate all L4D2 v9 static prop positions: "+
                   "; ".join(notes[:3]))


def normalize_archive_path(name: str) -> str:
    """Handle asset prefix/suffix variants without claiming their format is valid."""
    x=name.replace("\\","/").casefold().lstrip("/")
    for prefix in ("left4dead2/","l4d2/"):
        if x.startswith(prefix): x=x[len(prefix):]
    if x.endswith(".360.mdl"):
        x=x[:-8]+".mdl"
    if x.endswith(".360.vvd"):
        x=x[:-8]+".vvd"
    return x


def scan_model_archive_directories(root: Path) -> tuple[dict,dict,list[str]]:
    packs=sorted(root.rglob("*.360.zip"))
    if not packs or len(packs)>32:
        raise ValueError("Expected 1..32 extracted Xbox 360 ZIP packages")
    sources=defaultdict(list)
    per_pack={}
    problems=[]
    for path in packs:
        label=path.relative_to(root).as_posix()
        try:
            report=scan_xbox_zip(path)
        except (OSError,XboxZipError,ValueError) as err:
            problems.append(f"{label}: {err}")
            continue
        counts=Counter()
        for filename in report["filenames"]:
            canonical=normalize_archive_path(filename)
            if canonical.startswith("models/") and canonical.endswith(
                    (".mdl",".vvd",".vtx",".phy")):
                counts[canonical.rsplit(".",1)[-1]]+=1
                sources[canonical].append(label)
        per_pack[label]={"candidates":report["candidate_headers"],
                         "models":sum(counts.values()),"extensions":dict(counts)}
    # Additional loose files in user's extracted game tree can be inventoried
    # without reading their original bytes.
    loose=0
    for suffix in ("*.mdl","*.vvd","*.vtx","*.phy"):
        for path in root.rglob(suffix):
            if "research" in path.parts: continue
            rel=path.relative_to(root).as_posix()
            name=normalize_archive_path(rel)
            if name.startswith("models/"):
                sources[name].append("loose:"+rel)
                loose+=1
            if loose>200000:raise ValueError("Excessive loose model filenames")
    per_pack["loose_files"]={"candidates":loose,"models":loose,"extensions":{}}
    return dict(sources),per_pack,problems


def build_inventory(bsp: bytes, sources: dict) -> dict:
    endian,directory,_=read_directory(bsp)
    dynamic=list_model_placements(read_lump(bsp,directory[0],endian))
    static_info,static,notes=decode_static_from_bsp(bsp)
    names=[row["model"] for row in dynamic+static]
    index=set(sources)
    availability=model_availability(names,index)
    by_model={row["model"]:row for row in availability}
    classes=Counter(row["class"] for row in dynamic+static)
    return {
        "format":"lfd2-original-prop-placements-v1",
        "source_map":"c1m1_hotel.360.bsp",
        "static_header":static_info,
        "dynamic_count":len(dynamic),
        "static_count":len(static),
        "total":len(dynamic)+len(static),
        "classes":dict(classes),
        "unique_models":len(set(names)),
        "models_with_mdl":sum(row["mdl"] for row in availability),
        "models_with_complete_mesh_triplet":sum(row["mesh_ready"] for row in availability),
        "top_models":Counter(names).most_common(16),
        "availability":availability,
        "notes":notes,
        "placements":dynamic+static
    }


def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bsp",type=Path,default=MAP)
    parser.add_argument("--root",type=Path,default=PACK_ROOT)
    parser.add_argument("--export",action="store_true",
                        help="Write verified placement metadata under ignored research/local")
    parser.add_argument("--output",type=Path,default=DEFAULT_OUTPUT)
    args=parser.parse_args()
    try:
        root=args.root.expanduser().resolve()
        bsp=args.bsp.expanduser().resolve().read_bytes()
        sources,packs,problems=scan_model_archive_directories(root)
        record=build_inventory(bsp,sources)
        print("HOTEL ORIGINAL MODEL PACKAGES + STATIC V9 PLACEMENTS")
        print(f"Archive directories scanned: {len(packs)-1}; failed: {len(problems)}")
        for pack,stats in packs.items():
            print(f"  {pack}: model filenames={stats['models']:,}; "
                  f"extensions={stats['extensions']}")
        for note in problems[:5]:print("  PACK NOTE:",note)
        hdr=record["static_header"]
        print(f"Static records: {record['static_count']:,} at "
              f"{hdr['record_stride']} bytes each; dictionary {hdr['model_count']:,} "
              f"models; compression location={hdr['location']}")
        print(f"Dynamic/physics/door: {record['dynamic_count']:,}; "
              f"combined placements: {record['total']:,}")
        print("Class counts:",record["classes"])
        print(f"Unique referenced model paths: {record['unique_models']:,}; "
              f"MDL files matched: {record['models_with_mdl']:,}; "
              f"full MDL/VVD/VTX groups: {record['models_with_complete_mesh_triplet']:,}")
        print("Most frequently placed original assets:")
        for model,count in record["top_models"][:12]:
            print(f"  {count:>5} {model}")
        complete=next((row for row in record["availability"] if row["mesh_ready"]),None)
        if complete:
            print("First verified filename triplet:",complete["model"])
            for kind in ("mdl","vvd","vtx"):
                for key in model_files(complete["model"])[kind]:
                    if key in sources:
                        print(f"  {kind}: {key} in {', '.join(sources[key][:2])}")
                        break
        else:
            print("No complete standard model triplet located across these local packages.")
            print("Inspect model file suffixes and loose disc extraction before decoding.")
        if args.export:
            target=args.output.expanduser().resolve()
            if not target.is_relative_to(PRIVATE) or target==PRIVATE or target.exists():
                raise ValueError("Export requires unused filename inside research/local")
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open("x",encoding="utf-8") as handle:
                json.dump({k:v for k,v in record.items()
                           if k not in ("availability","notes")},handle,separators=(",",":"))
            print("Saved private 2,000+ prop placement manifest:",target)
        else:
            print("Read-only by default. --export saves metadata to private research/local.")
        print("No proprietary model geometry copied or uploaded.")
        return 0
    except (OSError,BspError,ValueError,struct.error) as err:
        print(f"Hotel prop scan stopped: {err}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
