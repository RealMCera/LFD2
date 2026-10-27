#!/usr/bin/env python3
"""Diagnose the shared Xbox 360 VMT payload representation, read-only.

Reads ORIGINAL model material candidates via existing exact studio MDL/CDTexture
paths, ZIP metadata and validated bounded local VMT readers. Reports byte
signatures, printable ratios and keyword presence for a few representative
material files. Does not extract or upload private game material scripts.

Use this after a batch resolver reports many 'vmt_without_basetexture' slots.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
import io
import json
from pathlib import Path
import sys

try:
    from .bsp_to_browser_mesh import ROOT,MAP,BspError,read_directory,read_lump
    from .inventory_hotel_studio_materials import (
        PRIVATE, PACK, PLACEMENTS,inventory_models
    )
    from .scan_xbox_zip_directory import scan_xbox_zip,scan_directory
    from .finish_hotel_materials import (
        ZIP1,read_local_member,map_sources,pick_source,extract_basetexture
    )
    from .inspect_xbox_zip import XboxZipError
except ImportError:
    from bsp_to_browser_mesh import ROOT,MAP,BspError,read_directory,read_lump
    from inventory_hotel_studio_materials import (
        PRIVATE, PACK, PLACEMENTS,inventory_models
    )
    from scan_xbox_zip_directory import scan_xbox_zip,scan_directory
    from finish_hotel_materials import (
        ZIP1,read_local_member,map_sources,pick_source,extract_basetexture
    )
    from inspect_xbox_zip import XboxZipError

def material_payload_category(blob: bytes) -> dict:
    """Inspect only structural metadata. Do not output verbatim VMT text."""
    if not blob:return {"kind":"empty", "bytes":0, "hex16":""}
    head=blob[:256]
    printable=sum(x in (9,10,13) or 32<=x<127 for x in head)/len(head)
    zeroes=head.count(0)/len(head)
    text_like=printable>=0.85 and zeroes<0.08
    text=blob.lower()
    has_base=b"$basetexture" in text
    extracted=extract_basetexture(blob) if text_like else None
    magic=blob[:4]
    if magic==b"LZMA":kind="valve_lzma_wrapper"
    elif magic in (b"PK\x03\x04",b"PK\x01\x02"):kind="zip_wrapper"
    elif magic[:2] in (b"\x78\x01",b"\x78\x9c",b"\x78\xda"):kind="zlib_candidate"
    elif len(head)>16 and zeroes>=0.20:
        kind="utf16_or_binary_nul_heavy"
    elif text_like:
        kind="plain_text_basetexture" if extracted else (
            "plain_text_token_unparsed" if has_base else "plain_text_no_basetexture")
    else:kind="binary_or_unknown"
    return {
        "kind":kind,"bytes":len(blob),"hex16":head[:16].hex(" "),
        "printable_first256_percent":round(printable*100,1),
        "nul_first256_percent":round(zeroes*100,1),
        "has_ascii_basetexture_token":has_base,
        "parsed_basetexture":bool(extracted),
    }

def pick_samples(models: list[dict], tables: dict, loader, sample_limit: int=8):
    """One copy of each matched VMT; sample highest-use files per kind."""
    if not 1<=sample_limit<=20:
        raise ValueError("Sample limit must be 1..20")
    referenced=Counter()
    # Purely an independent filename correlation, NOT a verified
    # $basetexture binding. Kept separate to prevent wrong model skins.
    same_name_slots=0
    same_name_weighted=0
    for m in models:
        for candidates in m["texture_candidates"]:
            if any(pick_source(tables,"vtfx",candidate) for candidate in candidates):
                same_name_slots+=1
                same_name_weighted+=m.get("original_placements",0)
            for candidate in candidates:
                original=pick_source(tables,"vmt",candidate)
                if original:
                    referenced[(original[0],original[1]["name"])]+=m.get("original_placements",0)
                    break
    by_kind=defaultdict(list)
    errors=Counter()
    for (label,name),uses in referenced.most_common():
        matches=[i for entries in tables["vmt"].values() for l,i in entries
                 if l==label and i["name"]==name]
        if len(matches)!=1:
            errors["duplicate_manifest_entry"]+=1
            continue
        try:
            blob=loader(label,matches[0])
            item=material_payload_category(blob)
            item["vmt"]=name
            item["source"]=label
            item["referenced_prop_uses"]=uses
            by_kind[item["kind"]].append(item)
        except (OSError,ValueError,XboxZipError,BspError):
            errors["unreadable_vmt"]+=1
    ranked=sorted(
        ({"kind":name,"file_count":len(rows),
          "referenced_prop_uses":sum(r["referenced_prop_uses"] for r in rows),
          "samples":rows[:sample_limit]}
         for name,rows in by_kind.items()),
        key=lambda x:-x["file_count"])
    return {"unique_vmt_files":sum(len(rows) for rows in by_kind.values()),
            "independent_same_name_vtfx_candidate_slots":same_name_slots,
            "independent_same_name_vtfx_candidate_prop_uses":same_name_weighted,
            "counts_by_kind":ranked,"load_errors":dict(errors)}

def inspect_archive_materials(zip_path:Path,bsp_path:Path,models:list[dict],limit=6):
    zip_report=scan_xbox_zip(zip_path)
    bsp=bsp_path.read_bytes()
    endian,directory,_=read_directory(bsp)
    pak=read_lump(bsp,directory[40],endian)
    if not pak or len(pak)>64*1024*1024:
        raise ValueError("Hotel embedded BSP PAK missing or over 64MB")
    pak_report=scan_directory(io.BytesIO(pak),len(pak))
    tables=map_sources(zip_report,pak_report)
    with zip_path.open("rb") as zs,io.BytesIO(pak) as ps:
        handles={"zip1":(zs,zip_path.stat().st_size,zip_report["directory_offset"]),
                 "map":(ps,len(pak),pak_report["directory_offset"])}
        def read(label,entry):
            stream,size,at=handles[label]
            return read_local_member(stream,size,at,entry)
        return pick_samples(models,tables,read,limit)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model-pack",type=Path,default=PACK)
    p.add_argument("--manifest",type=Path,default=PLACEMENTS)
    p.add_argument("--material-pack",type=Path,default=ZIP1)
    p.add_argument("--bsp",type=Path,default=MAP)
    p.add_argument("--limit",type=int,default=4,
                   help="Max sample metadata rows per material encoding family (1..20)")
    args=p.parse_args()
    try:
        paths=[args.model_pack.expanduser().resolve(),
               args.manifest.expanduser().resolve(),
               args.material_pack.expanduser().resolve(),
               args.bsp.expanduser().resolve()]
        if (not all(x.is_relative_to(ROOT) for x in paths)
            or not paths[1].is_relative_to(PRIVATE)):
            raise ValueError("Only local original archives and ignored private manifests")
        if not 1<=args.limit<=20:raise ValueError("Sample limit must be 1..20")
        materials=inventory_models(paths[0],paths[1])
        report=inspect_archive_materials(paths[2],paths[3],materials["models"],args.limit)
        print("ORIGINAL XBOX 360 STUDIO MATERIAL VMT PAYLOAD FORMATS (READ ONLY)")
        print("Unique original VMT material files examined:",report["unique_vmt_files"])
        print("Unreadable/ambiguous archive entries:",report["load_errors"])
        print("Independent exact-same-name VTFX filename candidates (UNVERIFIED):",
              report["independent_same_name_vtfx_candidate_slots"],
              "studio material slots,",
              report["independent_same_name_vtfx_candidate_prop_uses"],
              "prop reference uses")
        print("Same-name filename candidates are NOT verified $basetexture matches.")
        for group in report["counts_by_kind"]:
            print(f"  {group['file_count']:>3} files | {group['kind']} "
                  f"| {group['referenced_prop_uses']} reference uses")
            for item in group["samples"]:
                print(f"    VMT: {item['vmt']}")
                print(f"    zip: {item['source']}; bytes={item['bytes']}; "
                      f"head={item['hex16']}")
                print(f"    first256 printable={item['printable_first256_percent']}%; "
                      f"NUL={item['nul_first256_percent']}%; "
                      f"ASCII $basetexture={item['has_ascii_basetexture_token']}")
        print("No game data extracted, uploaded, changed or committed.")
        return 0
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError,
            XboxZipError,BspError) as e:
        print("VMT format diagnostic stopped:",e,file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
