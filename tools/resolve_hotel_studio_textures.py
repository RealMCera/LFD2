#!/usr/bin/env python3
"""Read-only matching of ALL original hotel studio material slots to Xbox VMT/VTFX.

Reuses the independently tested source model inventory and hotel map material
ZIP readers. Resolves only exact original material paths and VMT
$basetexture references, never guesses by similar filenames. Runs locally;
--export saves only private metadata under research/local for the next
all-model texture conversion pipeline. No art is copied or uploaded.
"""
from __future__ import annotations

import argparse
from collections import Counter
import io
import json
from pathlib import Path
import sys

try:
    from .bsp_to_browser_mesh import ROOT,MAP,BspError,read_directory,read_lump
    from .inventory_hotel_studio_materials import (
        PRIVATE,PACK,PLACEMENTS,inventory_models
    )
    from .scan_xbox_zip_directory import scan_xbox_zip,scan_directory
    from .finish_hotel_materials import (
        ZIP1,MAX_VMT_BYTES,map_sources,pick_source,read_local_member,
        extract_basetexture,normalize_material
    )
    from .inspect_xbox_zip import XboxZipError
except ImportError:
    from bsp_to_browser_mesh import ROOT,MAP,BspError,read_directory,read_lump
    from inventory_hotel_studio_materials import (
        PRIVATE,PACK,PLACEMENTS,inventory_models
    )
    from scan_xbox_zip_directory import scan_xbox_zip,scan_directory
    from finish_hotel_materials import (
        ZIP1,MAX_VMT_BYTES,map_sources,pick_source,read_local_member,
        extract_basetexture,normalize_material
    )
    from inspect_xbox_zip import XboxZipError

DEFAULT_OUT=PRIVATE/"hotel-studio-texture-matches.json"
MAX_CATALOG=30*1024*1024


def safe_catalog(catalog: dict) -> list[dict]:
    if (catalog.get("format")!="lfd2-original-studio-material-reference-catalog-v1"
        or not isinstance(catalog.get("models"),list)
        or len(catalog["models"])>4000):
        raise ValueError("Expected original hotel studio material inventory")
    for row in catalog["models"]:
        if (not isinstance(row,dict)
            or not isinstance(row.get("model"),str)
            or not isinstance(row.get("texture_candidates"),list)
            or len(row["texture_candidates"])>1024
            or any(not isinstance(group,list) or len(group)>128
                   for group in row["texture_candidates"])):
            raise ValueError("Invalid Source studio material slot list")
        for group in row["texture_candidates"]:
            for item in group:
                normalize_material(item)  # strict path check
    return catalog["models"]


def resolve_slots(models: list[dict], tables: dict, vmt_loader) -> dict:
    """Only accept a path when its VMT and its VTFX are both identified."""
    cache={}
    resolved=[];unresolved=[]
    # Include zero-valued keys in the serialized report. Counter returns 0 for
    # a missing key, but dict(Counter) drops it; both the CLI and browser
    # tooling require matched_slots to exist even when nothing matched.
    stats=Counter({"matched_slots":0,"weighted_matched_slots":0})
    matched_materials=set()
    matched_images=set()
    for model in models:
        count=int(model.get("original_placements",0))
        for slot,candidates in enumerate(model["texture_candidates"]):
            if not candidates:
                stats["no_path_candidates"]+=1
                unresolved.append({"model":model["model"],"slot":slot,
                                   "reason":"no_path_candidates"})
                continue
            chosen=None
            encountered=[]
            for candidate in candidates:
                key=normalize_material(candidate)
                material=pick_source(tables,"vmt",key)
                if not material:
                    encountered.append("missing_or_ambiguous_vmt")
                    continue
                label,entry=material
                vmt_key=(label,entry["name"])
                try:
                    if vmt_key not in cache:
                        cache[vmt_key]=extract_basetexture(vmt_loader(label,entry))
                    image_name=cache[vmt_key]
                except (OSError,ValueError,XboxZipError) as exc:
                    encountered.append("unreadable_vmt")
                    continue
                if not image_name:
                    encountered.append("vmt_without_basetexture")
                    continue
                image=pick_source(tables,"vtfx",image_name)
                if not image:
                    encountered.append("missing_or_ambiguous_vtfx")
                    continue
                chosen={
                    "model":model["model"],"slot":slot,
                    "material":key,"texture":image_name,
                    "vmt_source":label,"vmt_file":entry["name"],
                    "vtfx_source":image[0],"vtfx_file":image[1]["name"],
                    "placements":count,
                    "note":"Exact original VMT $basetexture and Xbox VTFX directory match; images not converted."
                }
                break
            if chosen:
                resolved.append(chosen)
                matched_materials.add(chosen["material"])
                matched_images.add(chosen["texture"])
                stats["matched_slots"]+=1
                stats["weighted_matched_slots"]+=count
            else:
                reason=encountered[-1] if encountered else "no_path_candidates"
                unresolved.append({"model":model["model"],"slot":slot,
                                   "reason":reason,"candidates":candidates[:8],
                                   "placements":count})
                stats[reason]+=1
    stats["total_slots"]=len(resolved)+len(unresolved)
    stats["unmatched_slots"]=len(unresolved)
    stats["unique_exact_materials"]=len(matched_materials)
    stats["unique_original_images"]=len(matched_images)
    stats["readable_models"]=len(models)
    return {
        "format":"lfd2-original-hotel-studio-texture-matches-v1",
        "stats":dict(stats),"matched":resolved,"unresolved":unresolved,
        "note":"Read-only exact studio-VMT-VTFX references, not converted textures or GPU bindings."
    }


def resolve_archive_materials(catalog: dict, zip_path: Path, bsp_path: Path) -> dict:
    models=safe_catalog(catalog)
    zip_report=scan_xbox_zip(zip_path)
    bsp=bsp_path.read_bytes()
    endian,directory,_=read_directory(bsp)
    pak=read_lump(bsp,directory[40],endian)
    if not pak or len(pak)>64*1024*1024:
        raise ValueError("Missing or oversized original hotel BSP embedded pak")
    pak_report=scan_directory(io.BytesIO(pak),len(pak))
    tables=map_sources(zip_report,pak_report)
    with zip_path.open("rb") as zip_stream,io.BytesIO(pak) as pak_stream:
        streams={"zip1":(zip_stream,zip_path.stat().st_size,
                         zip_report["directory_offset"]),
                 "map":(pak_stream,len(pak),pak_report["directory_offset"])}
        def loader(label,entry):
            stream,filesize,at=streams[label]
            return read_local_member(stream,filesize,at,entry)
        return resolve_slots(models,tables,loader)


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalog",type=Path,
                   help="Optional previously exported private material inventory")
    p.add_argument("--model-pack",type=Path,default=PACK)
    p.add_argument("--manifest",type=Path,default=PLACEMENTS)
    p.add_argument("--material-pack",type=Path,default=ZIP1)
    p.add_argument("--bsp",type=Path,default=MAP)
    p.add_argument("--export",action="store_true",
                   help="Save reference metadata privately; no texture images")
    p.add_argument("--output",type=Path,default=DEFAULT_OUT)
    args=p.parse_args()
    try:
        model_pack=args.model_pack.expanduser().resolve()
        manifest=args.manifest.expanduser().resolve()
        material_pack=args.material_pack.expanduser().resolve()
        bsp=args.bsp.expanduser().resolve()
        if (not model_pack.is_relative_to(ROOT) or
            not material_pack.is_relative_to(ROOT) or
            not bsp.is_relative_to(ROOT) or
            not manifest.is_relative_to(PRIVATE)):
            raise ValueError("Only original local game assets and private manifests are accepted")
        if args.catalog:
            c=args.catalog.expanduser().resolve()
            if not c.is_relative_to(PRIVATE) or c.stat().st_size>MAX_CATALOG:
                raise ValueError("Inventory catalog must remain private and below 30MB")
            catalog=json.loads(c.read_text(encoding="utf-8"))
        else:
            catalog=inventory_models(model_pack,manifest)
        report=resolve_archive_materials(catalog,material_pack,bsp)
        stats=report["stats"]
        print("AUTOMATIC HOTEL SOURCE STUDIO -> VMT -> VTFX MATCHES")
        print("Studio models inventoried:",catalog["model_count"])
        print("Studio model headers read:",catalog["models_with_readable_material_header"])
        print("Model headers still unsupported:",catalog["models_skipped"])
        print("Original material slots examined:",stats["total_slots"])
        print("Exact VMT + VTFX texture matches:",stats["matched_slots"])
        print("Unmatched material slots:",stats["unmatched_slots"])
        print("Unique real VMT materials matched:",stats["unique_exact_materials"])
        print("Unique original VTFX images located:",stats["unique_original_images"])
        print("Unmatched causes:")
        summary=Counter(x["reason"] for x in report["unresolved"])
        for reason,n in summary.most_common(8):
            print(f"  {n:>4} slots | {reason}")
        if args.export:
            out=args.output.expanduser().resolve()
            if not out.is_relative_to(PRIVATE) or out==PRIVATE or out.exists():
                raise ValueError("Output must be a new file under ignored research/local")
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(json.dumps(report,separators=(",",":")),
                           encoding="utf-8")
            print("PRIVATE EXACT-MATCH MATERIAL CATALOG:",out)
        else:
            print("Read-only by default; --export saves only private material metadata.")
        print("No original textures copied, converted, published or uploaded.")
        return 0
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError,
            XboxZipError,BspError) as exc:
        print("Studio material resolver stopped:",exc,file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
