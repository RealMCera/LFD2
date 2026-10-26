#!/usr/bin/env python3
"""Build ONE private, resumable L4D2 hotel texture folder for Chrome.

Uses the actual private UV mesh, reads original VMT material dependencies in
zip1.360.zip and the hotel's embedded BSP Pakfile, resolves $basetexture where
possible, and converts locally with the previously installed vtfx_reader.exe.

Only research/local/hotel-complete is written. No game data is committed,
uploaded, downloaded, or served. --run explicitly authorizes conversion;
default is a read-only dry run. Incomplete/unreadable materials are reported,
not silently assigned a guessed original texture.
"""
from __future__ import annotations

import argparse
from collections import Counter
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

try:
    from .bsp_to_browser_mesh import ROOT, MAP, read_directory, read_lump
    from .scan_xbox_zip_directory import scan_directory, scan_xbox_zip
    from .extract_single_vtfx import ZIP1, validate_texture, XboxZipError
    from .probe_xbox_texture_headers import inspect_local_header
    from .convert_local_vtfx import run_converter, png_dimensions, DEFAULT_CONVERTER
except ImportError:
    from bsp_to_browser_mesh import ROOT, MAP, read_directory, read_lump
    from scan_xbox_zip_directory import scan_directory, scan_xbox_zip
    from extract_single_vtfx import ZIP1, validate_texture, XboxZipError
    from probe_xbox_texture_headers import inspect_local_header
    from convert_local_vtfx import run_converter, png_dimensions, DEFAULT_CONVERTER

PRIVATE = (ROOT/"research"/"local").resolve()
DEFAULT_MESH = PRIVATE/"c1m1_hotel_spawns_uv.mesh.json"
DEFAULT_OUTPUT = PRIVATE/"hotel-complete"
MATERIAL_LINE = re.compile(r'(?im)"?\$basetexture"?\s+"?([a-z0-9_./\\-]+)"?')
SAFE_NAME = re.compile(r"^[a-z0-9_.\-]+(?:/[a-z0-9_.\-]+)*$")
MAX_VMT_BYTES = 262144
MAX_TOTAL = 300
SKIP_PREFIX = ("tools/", "dev/", "effects/", "sky/", "particle/")


def normalize_material(value: str) -> str:
    name = str(value).replace("\\", "/").casefold().strip("/")
    if name.startswith("materials/"):
        name = name[len("materials/"):]
    for ext in (".360.vtf", ".vtf", ".vmt", ".png"):
        if name.endswith(ext):
            name = name[:-len(ext)]
    if (not SAFE_NAME.fullmatch(name) or
            any(piece in (".","..") for piece in name.split("/"))):
        raise ValueError("Unsafe Source material path: "+repr(value))
    return name


def read_local_member(stream, size: int, start: int, entry: dict) -> bytes:
    """Read a small *stored* VMT only, after verifying local ZIP header + bounds."""
    if entry["method"] != 0 or entry["flags"] & 1:
        raise XboxZipError("Unsupported compressed/encrypted VMT member")
    length = entry["uncompressed_size"]
    if length < 1 or length > MAX_VMT_BYTES or entry["compressed_size"] != length:
        raise XboxZipError("VMT member size outside safe stored-file bounds")
    local = inspect_local_header(stream, size, start, entry)
    if (local.get("status") != "local_header_found" or
            not local.get("local_filename_matches") or
            local.get("local_method") != 0):
        raise XboxZipError("VMT local ZIP file header mismatch")
    at = local["candidate_payload_offset"]
    if at + length > start:
        raise XboxZipError("VMT member would overlap central directory")
    stream.seek(at)
    payload = stream.read(length)
    if len(payload) != length:
        raise XboxZipError("Short read of private VMT data")
    return payload


def extract_basetexture(payload: bytes) -> str | None:
    if len(payload) > MAX_VMT_BYTES:
        return None
    text = payload.decode("utf-8-sig", errors="replace")
    text = re.sub(r"(?m)//[^\r\n]*", "", text)
    found = MATERIAL_LINE.search(text)
    if not found:
        return None
    try:
        return normalize_material(found.group(1))
    except ValueError:
        return None


def map_sources(zip_report: dict, pak_report: dict) -> dict:
    """Build exact-name lookups. A BSP-embedded file takes priority for its map."""
    tables = {}
    for label, report in (("zip1",zip_report), ("map",pak_report)):
        for entry in report["entries"]:
            name = entry["name"].casefold().replace("\\", "/")
            if not name.startswith("materials/"):
                continue
            if name.endswith(".vmt"):
                kind="vmt"; key=name[10:-4]
            elif name.endswith(".360.vtf"):
                kind="vtfx"; key=name[10:-8]
            else:
                continue
            if (not key or not SAFE_NAME.fullmatch(key) or
                    any(piece in (".","..") for piece in key.split("/"))):
                continue
            tables.setdefault(kind, {}).setdefault(key, [])
            tables[kind][key].append((label,entry))
    return tables


def pick_source(tables: dict, kind: str, name: str):
    matches = tables.get(kind, {}).get(name, [])
    if not matches:
        return None
    # Prefer map pak for map-specific materials, and ZIP1 for generic materials.
    expected = "map" if name.startswith("maps/") else "zip1"
    chosen = [row for row in matches if row[0] == expected] or matches
    return chosen[0] if len(chosen) == 1 else None


def get_material_plan(mesh: dict, tables: dict, vmt_loader) -> tuple[list[dict],list[dict]]:
    names = mesh.get("materials", [])
    tri_ids = mesh.get("triangle_material_ids", [])
    if (mesh.get("uv_format") != "source-face-corners-1" or
            not isinstance(names, list) or not isinstance(tri_ids,list) or
            len(names) > MAX_TOTAL or len(tri_ids) > 2_000_000):
        raise ValueError("Expected valid original Source UV-enriched hotel mesh")
    counts = Counter(tri_ids)
    plan=[];unresolved=[]
    for index,raw in enumerate(names):
        try:
            key=normalize_material(raw)
        except ValueError:
            unresolved.append({"material":str(raw),"triangles":counts[index],"reason":"invalid material path"})
            continue
        count=counts[index]
        if not count:
            continue
        if key.startswith(SKIP_PREFIX):
            unresolved.append({"material":key,"triangles":count,"reason":"nonvisual/tool material"})
            continue
        texture=None;via="direct"
        vmt=pick_source(tables,"vmt",key)
        if vmt:
            try:
                target=extract_basetexture(vmt_loader(*vmt))
                if target:
                    texture=target;via="VMT $basetexture"
            except (OSError,ValueError,XboxZipError):
                pass
        if texture is None:
            texture=key
        image=pick_source(tables,"vtfx",texture)
        if image is None:
            unresolved.append({"material":key,"triangles":count,
                               "reason":"texture missing or ambiguous: "+texture})
            continue
        plan.append({"material":key,"triangles":count,"texture":texture,
                     "source":image[0],"entry":image[1],"via":via})
    return plan,unresolved


def find_cached_png(texture: str, width: int, height: int, output: Path):
    """Reuse previously generated private PNGs, but only if dimensions match."""
    basename=texture.split("/")[-1]
    candidates=[
        output/"textures"/(texture+".png"),
        PRIVATE/"hotel-textures"/"png"/(basename+".360_resource_0.png"),
        PRIVATE/"hotel-textures"/"png"/(basename+".360.png"),
        PRIVATE/"vtfx"/"png"/(basename+".360_resource_0.png"),
    ]
    # Previously converted flat PNGs are ambiguous if two texture paths share
    # the same basename. Caller must reject that case when reusing cache.
    for path in candidates:
        if path.is_file() and path.stat().st_size <= 40*1024*1024:
            try:
                if png_dimensions(path) == (width,height):
                    return path
            except (OSError,ValueError):
                pass
    return None


def make_texture(stream, filesize: int, central: int, entry: dict,
                 texname: str, output: Path, converter: Path, allow_cached: bool):
    """Convert or safely reuse a single texture, without overwriting a prior PNG."""
    relative="textures/"+texname+".png"
    final=output/relative
    vtfx=output/"original-vtfx"/(texname+".360.vtf")
    record=validate_texture(stream,filesize,central,entry)
    width,height=record["header"]["width"],record["header"]["height"]
    if final.is_file():
        if png_dimensions(final)!=(width,height):
            raise ValueError("Existing output PNG dimensions conflict with original VTFX")
        return relative,"existing"
    cached=find_cached_png(texname,width,height,output) if allow_cached else None
    if cached and cached!=final:
        final.parent.mkdir(parents=True,exist_ok=True)
        with cached.open("rb") as src,final.open("xb") as dst:
            shutil.copyfileobj(src,dst)
        return relative,"reused"
    if not converter.is_file():
        raise ValueError("Local VTFX Reader executable missing: "+str(converter))
    vtfx.parent.mkdir(parents=True,exist_ok=True)
    if not vtfx.exists():
        stream.seek(record["offset"])
        with vtfx.open("xb") as dest:
            remaining=record["bytes"]
            while remaining:
                chunk=stream.read(min(65536,remaining))
                if not chunk:
                    raise XboxZipError("Short original texture data")
                dest.write(chunk)
                remaining-=len(chunk)
    elif vtfx.stat().st_size!=record["bytes"]:
        raise ValueError("Existing original VTFX size differs from source")
    work=output/"conversion-work"/texname
    if work.exists() and any(work.iterdir()):
        pngs=sorted(work.rglob("*.png"))
        results=[]
        for item in pngs:
            if png_dimensions(item)==(width,height):
                results.append(item)
    else:
        results=[row[0] for row in run_converter(vtfx,work,converter)
                 if row[1:]==(width,height)]
    if not results:
        raise ValueError("Converter produced no valid original-size PNG")
    final.parent.mkdir(parents=True,exist_ok=True)
    with results[0].open("rb") as src,final.open("xb") as dst:
        shutil.copyfileobj(src,dst)
    return relative,"converted"


def execute(mesh_path: Path, bsp_path: Path, zip_path: Path, output: Path,
            converter: Path, run: bool = False, max_textures: int = 200) -> dict:
    output=output.expanduser().resolve()
    if not output.is_relative_to(PRIVATE) or output == PRIVATE:
        raise ValueError("Output must stay in a dedicated ignored research/local folder")
    if max_textures<1 or max_textures>MAX_TOTAL:
        raise ValueError("Invalid maximum texture count")
    mesh=json.loads(mesh_path.read_text(encoding="utf-8"))
    bsp=bsp_path.read_bytes()
    endian,directory,_=read_directory(bsp)
    pak=read_lump(bsp,directory[40],endian)
    if not pak or len(pak)>64*1024*1024:
        raise ValueError("Embedded BSP PAKFILE missing or exceeds 64MB safety limit")
    map_stream=io.BytesIO(pak)
    pak_report=scan_directory(map_stream,len(pak))
    zip_report=scan_xbox_zip(zip_path)
    zstream=zip_path.open("rb")
    try:
        streams={"zip1":zstream,"map":map_stream}
        sizes={"zip1":zip_path.stat().st_size,"map":len(pak)}
        reports={"zip1":zip_report,"map":pak_report}
        def vmt_loader(label,entry):
            return read_local_member(streams[label],sizes[label],
                                     reports[label]["directory_offset"],entry)
        tables=map_sources(zip_report,pak_report)
        planned,unresolved=get_material_plan(mesh,tables,vmt_loader)
        planned.sort(key=lambda row:-row["triangles"])
        # Avoid incorrect reuse of flat converted PNG names when paths collide.
        basename_count=Counter(row["texture"].split("/")[-1]
                               for row in planned)
        unique_targets={row["texture"] for row in planned}
        preview={"format":"lfd2-private-texture-manifest-v1",
                 "source_mesh":mesh_path.name,
                 "total_triangles":len(mesh["triangle_material_ids"]),
                 "materials":{},"textures":{},
                 "unresolved":unresolved,"summary":{}}
        if not run:
            print(f"Original brush triangles: {preview['total_triangles']:,}")
            print(f"Resolvable Source materials: {len(planned):,}; "
                  f"unique texture files: {len(unique_targets):,}")
            print(f"Unresolved/tool materials: {len(unresolved):,}")
            print("Top unresolved:")
            for item in sorted(unresolved,key=lambda row:-row["triangles"])[:12]:
                print(f"  {item['triangles']:>5} tris  {item['material']}: {item['reason']}")
            print("Read-only check finished; add --run to convert the private files.")
            return preview
        output.mkdir(parents=True,exist_ok=True)
        resolved_images={}
        attempted=set()
        for row in planned:
            texname=row["texture"]
            if texname not in attempted and len(attempted)>=max_textures:
                break
            if texname not in attempted:
                attempted.add(texname)
                label,entry=pick_source(tables,"vtfx",texname)
                try:
                    rel,state=make_texture(
                        streams[label],sizes[label],
                        reports[label]["directory_offset"],
                        entry,texname,output,converter,
                        allow_cached=basename_count[texname.split("/")[-1]]==1)
                    resolved_images[texname]=rel
                    print(f"{len(attempted):>3}/{min(max_textures,len(unique_targets))} "
                          f"{state:<9} {texname}")
                except (ValueError,OSError,XboxZipError,
                        subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
                    print(f"  unsupported {texname}: {error}")
            if texname in resolved_images:
                preview["materials"][row["material"]]=resolved_images[texname]
        ready=sum(row["triangles"] for row in planned
                  if row["material"] in preview["materials"])
        remaining=[row for row in planned
                   if row["material"] not in preview["materials"]]
        preview["unresolved"].extend(
            {"material":row["material"],"triangles":row["triangles"],
             "reason":"image conversion unavailable or deferred"} for row in remaining)
        preview["summary"]={
            "original_brush_triangles":preview["total_triangles"],
            "textured_brush_triangles":ready,
            "textured_percent":round(100*ready/max(1,preview["total_triangles"]),2),
            "mapped_materials":len(preview["materials"]),
            "unique_pngs":len(set(preview["materials"].values())),
            "unresolved_materials":len(preview["unresolved"]),
        }
        # Source filenames are the only identifiers in this manifest.
        target=output/"texture-manifest.json"
        with target.open("w",encoding="utf-8") as handle:
            json.dump(preview,handle,indent=2)
        print("PRIVATE BROWSER FOLDER:",output)
        print("MANIFEST:",target)
        print("COVERAGE:",preview["summary"])
        print("No original commercial assets uploaded or committed.")
        return preview
    finally:
        zstream.close()


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run",action="store_true",help="Convert original local material textures")
    p.add_argument("--mesh",type=Path,default=DEFAULT_MESH)
    p.add_argument("--bsp",type=Path,default=MAP)
    p.add_argument("--zip",type=Path,default=ZIP1)
    p.add_argument("--out",type=Path,default=DEFAULT_OUTPUT)
    p.add_argument("--converter",type=Path,default=DEFAULT_CONVERTER)
    p.add_argument("--max-textures",type=int,default=200)
    args=p.parse_args()
    try:
        execute(args.mesh.expanduser().resolve(),
                args.bsp.expanduser().resolve(),
                args.zip.expanduser().resolve(),
                args.out,args.converter.expanduser().resolve(),
                run=args.run,max_textures=args.max_textures)
        return 0
    except (OSError,ValueError,XboxZipError) as error:
        print(f"Hotel texture finish tool stopped: {error}",file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
