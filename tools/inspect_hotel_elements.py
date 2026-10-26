#!/usr/bin/env python3
"""Inspect ORIGINAL L4D2 hotel props, doors and displacement *metadata*.

No original models, BSP geometry, entity scripts, textures or payload data
are exported. Reads one locally owned Source/Xbox BSP and reports summaries.
Game-lump static prop variants differ between Source engine versions: we
parse just the dictionary/count header and do not guess prop-record strides.
This prepares the next actual original-model rendering milestone.
"""
from __future__ import annotations

import argparse
from collections import Counter
import math
from pathlib import Path
import struct
import sys

try:
    from .bsp_to_browser_mesh import MAP, BspError, read_directory, read_lump, decode_valve_lzma
    from .add_bsp_spawns import ENTITY_PATTERN, PAIR_PATTERN
except ImportError:
    from bsp_to_browser_mesh import MAP, BspError, read_directory, read_lump, decode_valve_lzma
    from add_bsp_spawns import ENTITY_PATTERN, PAIR_PATTERN

GAME_LUMP = 35
DISPINFO = 26
DISPVERTS = 33
MAX_ENTITIES = 100000
MAX_GAME_LUMPS = 512
MAX_MODELS = 100000
MAX_LEAVES = 3000000
CLASS_TARGETS = ("prop_", "func_door", "func_movelinear", "func_breakable",
                 "func_brush", "weapon_", "info_survivor", "point_viewcontrol")
STATIC_IDS = (b"sprp", b"prps")


def entity_summary(raw: bytes) -> dict:
    if len(raw)>16*1024*1024:
        raise BspError("Entity metadata exceeds 16MB limit")
    types=Counter()
    relevant=Counter()
    models=Counter()
    samples=[]
    total=0
    for match in ENTITY_PATTERN.finditer(raw):
        total+=1
        if total>MAX_ENTITIES:
            raise BspError("Entity count exceeds safe limit")
        pairs=PAIR_PATTERN.findall(match.group(1))
        values={}
        for key,value in pairs:
            k=key.decode("ascii","replace").casefold()
            if k in ("classname","model","origin","targetname"):
                values[k]=value.decode("utf-8","replace")
        kind=values.get("classname","").casefold()
        if not kind:
            continue
        types[kind]+=1
        if any(kind.startswith(prefix) for prefix in CLASS_TARGETS):
            relevant[kind]+=1
            name=values.get("model","")
            if name.startswith("models/") and len(name)<=220:
                models[name]+=1
            origin=values.get("origin","")
            coords=[]
            try:
                coords=[float(v) for v in origin.split()]
                if len(coords)!=3 or not all(math.isfinite(v) and abs(v)<1e6 for v in coords):
                    coords=[]
            except ValueError:
                pass
            if len(samples)<20:
                samples.append({"class":kind,"model":name[:150],
                                "origin":[round(v,2) for v in coords]})
    return {"entity_blocks":total,"class_counts":types,"prop_and_door_classes":relevant,
            "model_names":models,"sample_entities":samples}


def read_gamelump_directory(chunk: bytes, endian: str) -> list[dict]:
    if not chunk:
        return []
    if len(chunk)<4:
        raise BspError("Truncated game-lump header")
    count=struct.unpack_from(endian+"I",chunk,0)[0]
    if count>MAX_GAME_LUMPS or 4+16*count>len(chunk):
        raise BspError("Unsupported game-lump directory bounds")
    result=[]
    for i in range(count):
        pos=4+i*16
        tag=chunk[pos:pos+4]
        flags,version,offset,length=struct.unpack_from(endian+"HHII",chunk,pos+4)
        result.append({"id":tag.decode("ascii","replace"),
                       "id_raw":tag,"flags":flags,"version":version,
                       "offset":offset,"length":length})
    return result


def parse_static_dictionary(blob: bytes, endian: str) -> dict:
    """Inspect only model strings, leaf count and prop count; no prop stride guesses."""
    if len(blob)<12:
        raise BspError("Truncated static prop payload")
    num=struct.unpack_from(endian+"I",blob,0)[0]
    if num>MAX_MODELS or 4+num*128+4>len(blob):
        raise BspError("Static prop model dictionary count/size invalid")
    names=[]
    at=4
    for i in range(num):
        path=blob[at:at+128].split(b"\x00",1)[0].decode("utf-8","replace")
        names.append(path)
        at+=128
    leaf_count=struct.unpack_from(endian+"I",blob,at)[0]
    if leaf_count>MAX_LEAVES or at+4+2*leaf_count+4>len(blob):
        raise BspError("Static prop leaf array bounds invalid")
    at+=4+leaf_count*2
    prop_count=struct.unpack_from(endian+"I",blob,at)[0]
    if prop_count>MAX_MODELS:
        raise BspError("Static prop count exceeds safety limit")
    available=len(blob)-(at+4)
    if prop_count and available<prop_count*48:
        raise BspError("Static prop records too short to hold minimum coordinates")
    avg=(available//prop_count if prop_count else 0)
    return {"model_dictionary_entries":num,"models":names,
            "prop_count":prop_count,"leaf_count":leaf_count,
            "payload_bytes":len(blob),"prop_record_bytes_apparent":avg,
            "prop_bytes_remainder":available%prop_count if prop_count else available}


def static_payload_candidates(bsp: bytes, game: bytes, directory: list[dict],
                              game_entry: dict):
    """Candidate static payload offsets, without trusting compressed filelen.

    Valve's GAMELUMPFLAG_COMPRESSED means filelen reports the *uncompressed*
    size; using it to slice the disk is incorrect. The LZMA wrapper itself
    provides a bounded compressed byte length.
    """
    offset=game_entry["offset"]
    game_start=directory[GAME_LUMP]["offset"]
    for label,chunk,location in (
        ("bsp_absolute",bsp,offset),
        ("game_lump_relative",game,offset),
        ("game_lump_adjusted",game,offset-game_start),
    ):
        if 0<=location<len(chunk):
            yield label, chunk[location:location+min(16*1024*1024,len(chunk)-location)]


def probe_compressed_static_payload(bsp: bytes, game: bytes, directory: list[dict],
                                    entry: dict, endian: str) -> tuple[dict | None,list[str]]:
    """Try genuine LZMA wrapper only; never guess Xbox prop record layouts."""
    notes=[]
    for label,chunk in static_payload_candidates(bsp,game,directory,entry):
        magic=chunk[:4]
        if magic!=b"LZMA":
            notes.append(f"{label}: game lump magic {magic.hex(' ')} (not standard Valve LZMA)")
            continue
        try:
            decoded=decode_valve_lzma(chunk,entry["length"],endian)
            info=parse_static_dictionary(decoded,endian)
            if (not info["models"] or not info["prop_count"] or
                    any(not model.lower().startswith("models/") or
                        not model.lower().endswith(".mdl") for model in info["models"])):
                raise BspError("Decompressed static dictionary failed model validation")
            return {"source":label,"version":entry["version"],"compressed":True,
                    **info},notes
        except (BspError, ValueError) as err:
            notes.append(f"{label}: Valve LZMA probe unsuccessful: {err}")
    return None, notes


def inspect_bsp(bsp: bytes) -> dict:
    endian,directory,layout=read_directory(bsp)
    entities=entity_summary(read_lump(bsp,directory[0],endian))
    game=read_lump(bsp,directory[GAME_LUMP],endian)
    entries=read_gamelump_directory(game,endian)
    static=[]
    diagnostics=[]
    for e in entries:
        if e["id_raw"] not in STATIC_IDS:
            continue
        if e["flags"] & 1:
            candidate,notes=probe_compressed_static_payload(bsp,game,directory,e,endian)
            diagnostics.extend(notes[:3])
            if candidate:
                static.append(candidate)
                diagnostics.append("Compressed sprp model dictionary parsed; "
                                   "placement-record transforms remain unverified")
            else:
                diagnostics.append("Compressed sprp v%d: no validated Valve LZMA "
                                   "payload/dictionary yet; no placements decoded" %
                                   e["version"])
            continue
        # Some Source game-lump offsets are BSP absolute; others may point
        # into the decoded GAME_LUMP. Both are checked against known bounds.
        begin=e["offset"];length=e["length"]
        variants=[]
        if length and length<=16*1024*1024:
            if 0<=begin<=len(bsp)-length:
                variants.append(("bsp_absolute",bsp[begin:begin+length]))
            if 0<=begin<=len(game)-length:
                variants.append(("game_lump_relative",game[begin:begin+length]))
            rel=begin-directory[GAME_LUMP]["offset"]
            if 0<=rel<=len(game)-length:
                variants.append(("game_lump_adjusted",game[rel:rel+length]))
        valid=None
        for source,payload in variants:
            try:
                candidate=parse_static_dictionary(payload,endian)
                if (not candidate["models"] or not candidate["prop_count"] or
                        any(not name.lower().startswith("models/") or
                            not name.lower().endswith(".mdl")
                            for name in candidate["models"])):
                    continue
                valid={"source":source,"version":e["version"],**candidate}
                break
            except BspError:
                continue
        if valid:
            static.append(valid)
        else:
            diagnostics.append(
                f"sprp v{e['version']}: offsets or directory layout not validated "
                f"(offset={begin}, length={length})")
    disps={
        "dispinfo_bytes":directory[DISPINFO]["size"],
        "dispvert_bytes":directory[DISPVERTS]["size"],
        "dispinfo_struct_guess_176":directory[DISPINFO]["size"]//176
            if directory[DISPINFO]["size"]%176==0 else None,
    }
    return {"source_magic":bsp[:4].decode("ascii"),
            "layout":layout,"entities":entities,
            "game_lump_entries":[{k:e[k] for k in ("id","flags","version","length")}
                                 for e in entries],
            "static_prop_headers":static,
            "game_lump_notes":diagnostics,
            "displacement_lumps":disps}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bsp",type=Path,default=MAP)
    args=parser.parse_args()
    try:
        path=args.bsp.expanduser().resolve()
        data=inspect_bsp(path.read_bytes())
        print(f"ORIGINAL HOTEL ELEMENTS · {path.name}")
        print("Read-only data inventory. No game files were written or uploaded.")
        ents=data["entities"]
        print(f"\nEntity blocks: {ents['entity_blocks']:,}")
        print("Entity classes relevant to props/doors:")
        for name,n in ents["prop_and_door_classes"].most_common(24):
            print(f"  {n:>6,}  {name}")
        print("Sample prop/door entity placements (at most 12):")
        for row in ents["sample_entities"][:12]:
            print(f"  {row['class']:<25} {row['model'][:60]:<60} {row['origin']}")
        print(f"\nGame-lump headers: {len(data['game_lump_entries']):,}")
        for item in data["game_lump_entries"][:20]:
            print(f"  {item['id']!r}: version={item['version']}, "
                  f"flags={item['flags']}, bytes={item['length']:,}")
        for entry in data["static_prop_headers"]:
            print(f"STATIC PROP DICTIONARY: {entry['model_dictionary_entries']:,} unique "
                  f"models; {entry['prop_count']:,} placements; "
                  f"version={entry['version']}; header source={entry['source']}")
            print(f"  Apparent prop stride: {entry['prop_record_bytes_apparent']}"
                  f" (not decoded until Xbox record layout is confirmed)")
            for name in entry["models"][:12]:
                print("    "+name)
        for note in data["game_lump_notes"]:
            print("NOTE: "+note)
        disp=data["displacement_lumps"]
        print(f"\nDisplacements: info lump {disp['dispinfo_bytes']:,} bytes; "
              f"vertex lump {disp['dispvert_bytes']:,} bytes; "
              f"possible standard records: {disp['dispinfo_struct_guess_176']}")
        print("\nNext: original prop/model formats, placement transforms and displacement mesh.")
        return 0
    except (OSError,BspError,ValueError,struct.error) as exc:
        print(f"Element inventory stopped: {exc}",file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
