#!/usr/bin/env python3
"""Inspect original hotel entity-model availability in local Xbox asset ZIPs.

Uses existing safe ZIP *central-directory* scanners to check .mdl/.vvd/.vtx
filenames only. It does NOT decode or extract original game models. Optional
--export saves a private, bounded entity placement manifest under ignored
research/local/ for the next WebGL original model renderer.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

try:
    from .bsp_to_browser_mesh import ROOT, MAP, BspError, read_directory, read_lump
    from .add_bsp_spawns import ENTITY_PATTERN, PAIR_PATTERN
    from .scan_xbox_zip_directory import scan_xbox_zip
    from .inspect_xbox_zip import XboxZipError
    from .inspect_hotel_elements import inspect_bsp
    from .probe_xbox_texture_headers import inspect_local_header
except ImportError:
    from bsp_to_browser_mesh import ROOT, MAP, BspError, read_directory, read_lump
    from add_bsp_spawns import ENTITY_PATTERN, PAIR_PATTERN
    from scan_xbox_zip_directory import scan_xbox_zip
    from inspect_xbox_zip import XboxZipError
    from inspect_hotel_elements import inspect_bsp
    from probe_xbox_texture_headers import inspect_local_header

PACK = ROOT/"game-extracted"/"left4dead2"/"zip0.360.zip"
PRIVATE = (ROOT/"research"/"local").resolve()
OUTPUT = PRIVATE/"hotel-model-placements.json"
MODEL_TYPES=("prop_physics","prop_dynamic","prop_door_rotating",
             "prop_door_rotating_checkpoint","prop_static")
MAX_ENTITIES=100000


def vector3(raw: str) -> list[float] | None:
    try:
        result=[float(x) for x in raw.split()]
    except ValueError:
        return None
    if len(result)!=3 or not all(math.isfinite(x) and abs(x)<1e6 for x in result):
        return None
    return [round(x,3) for x in result]


def list_model_placements(entity_lump: bytes) -> list[dict]:
    """Export only safe model paths, placement transforms and class labels."""
    placements=[]
    for index,match in enumerate(ENTITY_PATTERN.finditer(entity_lump)):
        if index>MAX_ENTITIES:
            raise BspError("Entity count exceeds safe limit")
        fields={}
        for a,b in PAIR_PATTERN.findall(match.group(1)):
            name=a.decode("ascii","replace").casefold()
            if name in ("classname","model","origin","angles","skin","solid"):
                fields[name]=b.decode("utf-8","replace")
        kind=fields.get("classname","").lower()
        model=fields.get("model","").replace("\\","/").casefold()
        if (kind not in MODEL_TYPES or not model.startswith("models/") or
                not model.endswith(".mdl") or len(model)>220 or
                not all(x.isalnum() or x in "._-/" for x in model) or
                any(part in ("",".","..") for part in model.split("/"))):
            continue
        xyz=vector3(fields.get("origin",""))
        if xyz is None:
            continue
        angles=vector3(fields.get("angles","0 0 0")) or [0,0,0]
        placements.append({"class":kind,"model":model,
                           "origin":xyz,"angles":angles})
    return placements


def model_files(model: str) -> dict[str,list[str]]:
    stem=model[:-4]
    return {"mdl":[model],
            "vvd":[stem+".vvd"],
            "vtx":[stem+".vtx",stem+".dx90.vtx",stem+".dx80.vtx",
                   stem+".sw.vtx",stem+".360.vtx"],
            "phy":[stem+".phy"]}


def model_availability(models: list[str], indexed: set[str]) -> list[dict]:
    report=[]
    for model in sorted({name.replace("\\","/").casefold() for name in models}):
        sides=model_files(model)
        present={ext:next((path for path in choices if path in indexed),None)
                 for ext,choices in sides.items()}
        report.append({"model":model,"mdl":bool(present["mdl"]),
                       "vvd":bool(present["vvd"]),"vtx":bool(present["vtx"]),
                       "phy":bool(present["phy"]),
                       "mesh_ready":all(present[t] for t in ("mdl","vvd","vtx"))})
    return report


def make_inventory(bsp: bytes, archive_names: list[str]) -> dict:
    endian,directory,_=read_directory(bsp)
    entities=read_lump(bsp,directory[0],endian)
    placements=list_model_placements(entities)
    metadata=inspect_bsp(bsp)
    static_models=[]
    static_counts=0
    for entry in metadata["static_prop_headers"]:
        static_models+=entry["models"]
        static_counts+=entry["prop_count"]
    indexed={name.replace("\\","/").casefold() for name in archive_names}
    bymodel=Counter(row["model"] for row in placements)
    static_info=model_availability(static_models,indexed)
    dynamics=model_availability(list(bymodel),indexed)
    return {"placement_count":len(placements),
            "entity_models":len(bymodel),
            "entity_classes":Counter(x["class"] for x in placements),
            "static_model_dictionary_count":len(static_models),
            "static_prop_placements_reported":static_counts,
            "static_lump_notes":metadata["game_lump_notes"],
            "dynamic_availability":dynamics,
            "static_availability":static_info,
            "top_entity_models":bymodel.most_common(16),
            "placements":placements}


def probe_model_headers(stream, report: dict, model: str) -> list[dict]:
    """Peek at most 16 payload bytes for one model's local MDL/VVD/VTX headers."""
    index={item["name"].replace("\\","/").casefold():item
           for item in report["entries"] if item["name"].lower().startswith("models/")}
    results=[]
    for kind in ("mdl","vvd","vtx"):
        match=next((index[path] for path in model_files(model)[kind] if path in index),None)
        if not match:
            results.append({"type":kind,"status":"absent"})
            continue
        info=inspect_local_header(stream,stream.seek(0,2),
                                  report["directory_offset"],match)
        signature=info.get("candidate_magic_hex","")
        magic=bytes.fromhex(signature) if signature else b""
        # Source studio headers are sometimes byteswapped for Xbox 360.
        known={b"IDST":"Source MDL",b"TSDI":"Xbox-swapped MDL",
               b"IDSV":"Source VVD",b"VSDI":"Xbox-swapped VVD"}
        results.append({"type":kind,"status":info["status"],
                        "name_match":info.get("local_filename_matches",False),
                        "header_hex":signature,
                        "format_hint":known.get(magic[:4],"unverified; inspect format")})
    return results


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bsp",type=Path,default=MAP)
    p.add_argument("--pack",type=Path,default=PACK)
    p.add_argument("--export",action="store_true",
                   help="Write bounded original model placement manifest into private research/local")
    p.add_argument("--output",type=Path,default=OUTPUT)
    args=p.parse_args()
    try:
        data=args.bsp.expanduser().resolve().read_bytes()
        pack=args.pack.expanduser().resolve()
        archive=scan_xbox_zip(pack)
        inventory=make_inventory(data,archive["filenames"])
        print(f"ORIGINAL HOTEL MODEL AVAILABILITY · {pack.name}")
        print(f"Entities with real MDL model and valid position: {inventory['placement_count']:,}")
        print(f"Unique entity models: {inventory['entity_models']:,}")
        print(f"Entity classes: {dict(inventory['entity_classes'])}")
        print(f"Static prop dictionary models decoded: "
              f"{inventory['static_model_dictionary_count']:,}; "
              f"static placements reported: {inventory['static_prop_placements_reported']:,}")
        for note in inventory["static_lump_notes"][:5]:
            print("Static lump note: "+note)
        for title,group in (("Dynamic/physics/door",inventory["dynamic_availability"]),
                            ("Static",inventory["static_availability"])):
            print(f"{title} models matched against ZIP directory:")
            for feature in ("mdl","vvd","vtx","mesh_ready"):
                print(f"  {feature:>10}: {sum(1 for row in group if row[feature]):,}/"
                      f"{len(group):,}")
            for row in [r for r in group if not r["mesh_ready"]][:8]:
                print(f"    missing companion(s): {row['model']}")
        print("Most frequent original placed models:")
        for name,count in inventory["top_entity_models"][:12]:
            print(f"  {count:>4} · {name}")
        candidate=next((row["model"] for row in inventory["dynamic_availability"]
                        if row["mesh_ready"]),None)
        if candidate:
            print(f"Read-only 16-byte local model header probe: {candidate}")
            with pack.open("rb") as handle:
                for item in probe_model_headers(handle,archive,candidate):
                    print(f"  {item['type']}: {item['status']}; "
                          f"magic={item.get('header_hex','none')}; "
                          f"{item.get('format_hint','not found')}")
        if args.export:
            target=args.output.expanduser().resolve()
            if not target.is_relative_to(PRIVATE) or target==PRIVATE:
                raise ValueError("Placement file must stay in private research/local")
            if target.exists():
                raise ValueError("Placement output already exists; overwrite refused")
            target.parent.mkdir(parents=True,exist_ok=True)
            manifest={"format":"lfd2-original-model-placements-0.1",
                      "source_map":args.bsp.name,
                      "placements":inventory["placements"]}
            with target.open("x",encoding="utf-8") as handle:
                json.dump(manifest,handle,indent=2)
            print(f"Private original entity-model placement manifest: {target}")
        else:
            print("Read-only by default; --export writes original placements privately.")
        print("No model files extracted, decoded or uploaded.")
        return 0
    except (OSError,ValueError,BspError,XboxZipError) as err:
        print(f"Model inventory stopped: {err}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
