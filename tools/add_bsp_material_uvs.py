#!/usr/bin/env python3
"""Add Source face material IDs and UVs to an existing private browser mesh.

This augments (never overwrites) the successful Xbox hotel geometry and
preserves any embedded camera start points. UVs are stored PER TRIANGLE CORNER
because one 3D BSP vertex can have different materials/UVs on different faces.

This does not copy original texture images or upload game assets.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import struct
import sys

try:
    from .bsp_to_browser_mesh import ROOT, MAP, BspError, read_directory, read_lump
    from .inspect_map_materials import texture_strings
except ImportError:
    from bsp_to_browser_mesh import ROOT, MAP, BspError, read_directory, read_lump
    from inspect_map_materials import texture_strings

DEFAULT_INPUT = ROOT / "research" / "local" / "c1m1_hotel_spawns.mesh.json"
DEFAULT_OUTPUT = ROOT / "research" / "local" / "c1m1_hotel_spawns_uv.mesh.json"
LUMP_TEXTURES=(2,3,6,12,13,43,44,58)
MAX_UV=1e7


def uv_mapping(texinfo: bytes, texdata: bytes, names: list[str], endian: str):
    if len(texinfo)%72 or len(texdata)%32:
        raise BspError("Invalid Source texinfo or texdata stride")
    mappings=[]
    for ix in range(len(texinfo)//72):
        matrix=struct.unpack_from(endian+"8f",texinfo,ix*72)
        texdata_id=struct.unpack_from(endian+"i",texinfo,ix*72+68)[0]
        if not 0<=texdata_id<len(texdata)//32:
            mappings.append(None)
            continue
        record=texdata_id*32
        name_id,width,height=struct.unpack_from(endian+"3i",texdata,record+12)
        if (not 0<=name_id<len(names) or width<=0 or height<=0
                or width>16384 or height>16384):
            mappings.append(None)
            continue
        mappings.append((matrix,width,height,names[name_id]))
    return mappings


def augment_mesh(bsp: bytes, mesh: dict) -> dict:
    if mesh.get("format")!="source-brush-mesh-0.1":
        raise BspError("Expected private Source brush geometry mesh format 0.1")
    if "corner_uvs" in mesh:
        raise BspError("Mesh is already UV-enriched; will not add duplicate attributes")
    positions=mesh.get("vertices")
    index=mesh.get("indices")
    if (not isinstance(positions,list) or not isinstance(index,list)
            or len(positions)%3 or len(index)%3):
        raise BspError("Mesh vertices and indices missing or misaligned")
    endian, directory, _ = read_directory(bsp)
    face_lump=mesh.get("face_lump",58)
    if face_lump not in (7,27,58):
        raise BspError(f"Unexpected Source face lump {face_lump}")
    chunks={ix:read_lump(bsp,directory[ix],endian)
            for ix in (2,3,6,12,13,43,44,face_lump)}
    texdata,texinfo = chunks[2], chunks[6]
    offsets=chunks[44]
    if len(offsets)%4:
        raise BspError("Unaligned Source material string table")
    names=texture_strings(chunks[43],endian,len(offsets),
                          [r[0] for r in struct.iter_unpack(endian+"i",offsets)])
    mappings=uv_mapping(texinfo,texdata,names,endian)
    vertices=chunks[3];edges=chunks[12];surfedges=chunks[13];faces=chunks[face_lump]
    if (len(vertices)%12 or len(edges)%4 or len(surfedges)%4
            or len(faces)%56):
        raise BspError("BSP geometry lump stride mismatch")
    vertex=[v for v in struct.iter_unpack(endian+"3f",vertices)]
    edge=[e for e in struct.iter_unpack(endian+"2H",edges)]
    surf=[v[0] for v in struct.iter_unpack(endian+"i",surfedges)]
    uv=[]
    material_ids=[]
    materials=[]
    material_indices={}
    face_uv_counts=0
    for offset in range(0,len(faces),56):
        firstedge=struct.unpack_from(endian+"i",faces,offset+4)[0]
        nedge=struct.unpack_from(endian+"h",faces,offset+8)[0]
        disp=struct.unpack_from(endian+"h",faces,offset+12)[0]
        if disp>=0:
            continue
        if nedge<3 or nedge>512 or firstedge<0 or firstedge+nedge>len(surf):
            continue
        polygon=[]
        for se in surf[firstedge:firstedge+nedge]:
            edgeid=abs(se)
            if edgeid>=len(edge):
                polygon=[];break
            a,b=edge[edgeid]
            vi=a if se>=0 else b
            if vi>=len(vertex):
                polygon=[];break
            if not polygon or vi!=polygon[-1]:
                polygon.append(vi)
        if len(polygon)>1 and polygon[0]==polygon[-1]:
            polygon.pop()
        if len(polygon)<3:
            continue
        texid=struct.unpack_from(endian+"h",faces,offset+10)[0]
        if texid<0 or texid>=len(mappings) or mappings[texid] is None:
            raise BspError(f"No valid material/UV for BSP face {offset//56}")
        matrix,width,height,name=mappings[texid]
        if name not in material_indices:
            material_indices[name]=len(materials)
            materials.append(name)
        mat=material_indices[name]
        for j in range(1,len(polygon)-1):
            v_idx=(polygon[0],polygon[j],polygon[j+1])
            a,b,c=(vertex[k] for k in v_idx)
            ux,uy,uz=(b[k]-a[k] for k in range(3))
            vx,vy,vz=(c[k]-a[k] for k in range(3))
            area2=(uy*vz-uz*vy)**2+(uz*vx-ux*vz)**2+(ux*vy-uy*vx)**2
            if area2<1e-8:
                continue
            t=len(material_ids)
            if t>=len(index)//3:
                raise BspError("More BSP triangles than the existing private mesh")
            for i,vert in enumerate((a,b,c)):
                old_idx=index[t*3+i]
                if not (0<=old_idx<len(positions)//3):
                    raise BspError("Mesh index out of bounds")
                old=positions[old_idx*3:old_idx*3+3]
                if any(abs(round(v,3)-w)>0.005 for v,w in zip(vert,old)):
                    raise BspError(f"Triangle {t} differs from original BSP; regenerate private mesh")
                x,y,z=vert
                u=(matrix[0]*x+matrix[1]*y+matrix[2]*z+matrix[3])/width
                v=(matrix[4]*x+matrix[5]*y+matrix[6]*z+matrix[7])/height
                if not (math.isfinite(u) and math.isfinite(v)
                        and abs(u)<=MAX_UV and abs(v)<=MAX_UV):
                    raise BspError("Invalid Source face texture coordinates")
                uv.extend((round(u,6),round(v,6)))
            material_ids.append(mat)
            face_uv_counts+=1
    if face_uv_counts!=mesh.get("triangle_count") or len(index)!=face_uv_counts*3:
        raise BspError(f"Triangle mismatch: BSP face UV pass {face_uv_counts}, "
                       f"original mesh {mesh.get('triangle_count')}")
    result=dict(mesh)
    result.update({"uv_format":"source-face-corners-1",
                   "corner_uvs":uv,
                   "triangle_material_ids":material_ids,
                   "materials":materials})
    return result


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bsp",type=Path,default=MAP)
    p.add_argument("--mesh",type=Path,default=DEFAULT_INPUT)
    p.add_argument("--output",type=Path,default=DEFAULT_OUTPUT)
    args=p.parse_args()
    output=args.output.expanduser().resolve()
    if not output.is_relative_to(ROOT/"research"/"local"):
        p.error("Output must remain in ignored research/local/")
    if output.exists():
        p.error(f"Refusing to overwrite private mesh: {output}")
    try:
        with args.mesh.expanduser().resolve().open(encoding="utf-8") as src:
            mesh=json.load(src)
        result=augment_mesh(args.bsp.expanduser().resolve().read_bytes(),mesh)
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open("x",encoding="utf-8") as dest:
            json.dump(result,dest,separators=(",",":"))
        print(f"Private original material-aware map written: {output}")
        print(f"Triangles: {result['triangle_count']:,}; "
              f"material names: {len(result['materials']):,}; "
              f"UV pairs: {len(result['corner_uvs'])//2:,}")
        print("Original mesh/spawns preserved; no texture images exported or uploaded.")
        return 0
    except (OSError,BspError,ValueError,struct.error) as err:
        print(f"Source UV enrichment stopped: {err}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
