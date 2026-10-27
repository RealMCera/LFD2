#!/usr/bin/env python3
"""Read-only summary of a private automatic hotel-prop conversion batch.

Analyzes *existing* research/local/hotel-auto-props/scene.json without
converting anything, rescanning ZIPs, changing game files, or uploading assets.
Summarizes shared failure families by affected model types AND placement count
so we can improve common formats rather than debug each item individually.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
import json
from pathlib import Path
import sys

try:
    from .bsp_to_browser_mesh import ROOT
except ImportError:
    from bsp_to_browser_mesh import ROOT

PRIVATE=(ROOT/"research"/"local").resolve()
DEFAULT=PRIVATE/"hotel-auto-props"/"scene.json"
DEFAULT_PLACEMENTS=PRIVATE/"hotel-all-props.json"


def reason_category(error: str) -> str:
    """Deliberately broad: counts are evidence, categories are heuristics."""
    value=error.casefold()
    for fragment,name in (
        ("companion ambiguous or absent","Missing/ambiguous original model parts"),
        ("no such file","Missing original local file"),
        ("original studio checksum","Checksums / Source version"),
        ("checksum mismatch","Checksums / Source version"),
        ("header/checksum mismatch","Checksums / Source version"),
        ("header checksum","Checksums / Source version"),
        ("version","Source version/format"),
        ("lzma","Xbox compression/wrapper"),
        ("decompress","Xbox compression/wrapper"),
        ("bodypart","Bodypart/model hierarchy"),
        ("submodel","Bodypart/model hierarchy"),
        ("model counts","Bodypart/model hierarchy"),
        ("model vertex","MDL vertex indexing"),
        ("mesh association","MDL vertex indexing"),
        ("origmeshvertid","VTX index/strip layout"),
        ("vtx strip","VTX index/strip layout"),
        ("strip","VTX index/strip layout"),
        ("mesh counts","Mesh hierarchy"),
        ("mesh","Mesh hierarchy"),
        ("vertex pool","VVD vertex layout/fixups"),
        ("vvd fixup","VVD vertex layout/fixups"),
        ("vvd","VVD vertex layout/fixups"),
        ("vertex","VVD vertex layout/fixups"),
        ("triangle","Triangle limit/geometry"),
        ("source studio structure","Source structure/bounds"),
        ("outside","Source structure/bounds"),
        ("bounds","Source structure/bounds"),
        ("invalid","Other rejected Source structure"),
    ):
        if fragment in value:
            return name
    return "Other format or validation error"


def summarize_scene(scene: dict, limit: int = 12,
                    original_placements: list[dict] | None = None) -> dict:
    if (scene.get("format")!="lfd2-original-hotel-studio-bundle-v1"
        or scene.get("source_map")!="c1m1_hotel.360.bsp"
        or not isinstance(scene.get("models"),list)
        or not isinstance(scene.get("skipped"),list)
        or not isinstance(scene.get("placements"),list)):
        raise ValueError("Not an original locally converted hotel scene.json")
    if not 1<=limit<=100:
        raise ValueError("Invalid top-N limit")
    placement_counts=Counter(
        p.get("model","") for p in (original_placements or [])
        if isinstance(p,dict))
    categories=defaultdict(list)
    for item in scene["skipped"]:
        if not isinstance(item,dict) or not isinstance(item.get("model"),str):
            raise ValueError("Invalid skipped-model report")
        categories[reason_category(str(item.get("error","")))].append(item)
    ranked=sorted(
        ({"category":kind,"count":len(rows),
          "affected_placements":sum(placement_counts[x["model"]] for x in rows),
          "examples":[{"model":x["model"],"reason":str(x.get("error",""))[:150],
                       "placement_count":placement_counts[x["model"]]}
                      for x in sorted(rows,
                          key=lambda x:-placement_counts[x["model"]])[:2]]}
         for kind,rows in categories.items()),
        key=lambda d:(-d["affected_placements"],-d["count"],d["category"])
    )
    successful=Counter(p.get("model","") for p in scene["placements"])
    top_success=successful.most_common(limit)
    top_skipped=sorted(({"model":s["model"],"placements":placement_counts[s["model"]],
                         "reason":str(s.get("error",""))[:150]}
                        for s in scene["skipped"]),
                       key=lambda x:-x["placements"])[:limit]
    stats=scene.get("stats",{})
    return {
        "stats":stats,
        "by_error_type":ranked[:limit],
        "all_error_type_count":len(ranked),
        "top_decoded_placements":top_success,
        "top_skipped_placements":top_skipped,
        "note":"Categories are heuristic; examples contain only filename/rejection metadata.",
    }


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("scene",nargs="?",type=Path,default=DEFAULT)
    p.add_argument("--top",type=int,default=12)
    p.add_argument("--manifest",type=Path,default=DEFAULT_PLACEMENTS)
    args=p.parse_args()
    try:
        path=args.scene.resolve()
        if not path.is_relative_to(PRIVATE):
            raise ValueError("Only original ignored research/local scene reports are allowed")
        if path.stat().st_size>25*1024*1024:
            raise ValueError("Scene metadata larger than 25MB")
        scene=json.loads(path.read_text(encoding="utf-8"))
        manifest_path=args.manifest.resolve()
        if not manifest_path.is_relative_to(PRIVATE) or manifest_path.stat().st_size>25*1024*1024:
            raise ValueError("Original placement manifest must be under research/local and below 25MB")
        original=json.loads(manifest_path.read_text(encoding="utf-8"))
        if (original.get("format")!="lfd2-original-prop-placements-v1"
            or not isinstance(original.get("placements"),list)):
            raise ValueError("Invalid original hotel placement manifest")
        result=summarize_scene(scene,args.top,original["placements"])
        stats=result["stats"]
        print("ORIGINAL HOTEL AUTOMATIC MODEL CONVERSION — PRIVATE METADATA SUMMARY")
        print("Processed model types:",stats.get("attempted_models","?"))
        print("Converted original model types:",stats.get("decoded_models","?"))
        print("Skipped model types:",stats.get("skipped_models","?"))
        print("Original placements represented:",stats.get("original_placements_included","?"),
              "/",stats.get("original_placements_total","?"))
        print("SKIPPED MODEL FAMILIES (fix shared formats in groups):")
        for group in result["by_error_type"]:
            print(f"  {group['count']:>4} models | "
                  f"{group['affected_placements']:>4} original placements | "
                  f"{group['category']}")
            for ex in group["examples"]:
                print("       Example:",ex["model"],
                      f"({ex['placement_count']} placements)")
                print("       Check:",ex["reason"])
        print("Highest-impact missing original model types:")
        for item in result["top_skipped_placements"]:
            if item["placements"]<1:break
            print(f"  {item['placements']:>4} original references | "
                  f"{item['model']} | {item['reason']}")
        print("Most-reused already decoded model types:")
        for model,count in result["top_decoded_placements"][:6]:
            print(f"  {count:>4} placements | {model}")
        print("Report read-only. No original assets copied, uploaded or changed.")
        return 0
    except (OSError,ValueError,json.JSONDecodeError,KeyError,TypeError) as exc:
        print("Original batch report stopped:",str(exc),file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
