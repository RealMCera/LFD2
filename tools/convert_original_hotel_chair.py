#!/usr/bin/env python3
"""Convert ONE verified original Xbox Source v49 studio model to private mesh JSON.

For the authenticated c1m1 hotel chair, uses the decoded .mdl, original
big-endian .360.vvd and .dx90.360.vtx extracted from the owner's game.
Decodes LOD 0 triangles through MDL -> VTX strip groups -> VVD original
vertices. Does not fabricate geometry, perform animation/skin transforms,
or include original commercial assets in the public repository.

Only --run writes an ignored private JSON mesh under research/local/.
Default mode validates and reports the actual Source geometry read-only.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct
import sys

try:
    from .bsp_to_browser_mesh import ROOT,BspError
    from .probe_original_hotel_model import (
        parse_source_header,studio_model_summary,OUT_DIR,DEFAULT_MODEL,
    )
except ImportError:
    from bsp_to_browser_mesh import ROOT,BspError
    from probe_original_hotel_model import (
        parse_source_header,studio_model_summary,OUT_DIR,DEFAULT_MODEL,
    )

PRIVATE=(ROOT/"research"/"local").resolve()
DEFAULT_MDL=OUT_DIR/"decoded"/DEFAULT_MODEL
DEFAULT_VVD=OUT_DIR/"models"/"props_furniture"/"hotel_chair.360.vvd"
DEFAULT_VTX=OUT_DIR/"models"/"props_furniture"/"hotel_chair.dx90.360.vtx"
DEFAULT_OUT=PRIVATE/"hotel-chair.mesh.json"
MAX_VERTICES=100000
MAX_TRIANGLES=200000
MAX_MODELS=64
MAX_MESHES=128
MAX_GROUPS=128
MAX_INDICES=600000
MDL_MODEL_SIZE=148
MDL_MESH_SIZE=116
VTX_STRIP_GROUP_SIZE=25
VTX_STRIP_SIZE=27
VTX_VERTEX_SIZE=9
VVD_VERTEX_SIZE=48


def read_at(data: bytes, order: str, fmt: str, offset: int):
    size=struct.calcsize(order+fmt)
    if offset<0 or offset+size>len(data):
        raise BspError("Source studio structure goes outside original file")
    return struct.unpack_from(order+fmt,data,offset)


def validate_array(data: bytes, start: int, count: int, stride: int,
                   label: str, max_count: int) -> None:
    if (count<0 or count>max_count or start<0 or
        stride<1 or start+count*stride>len(data)):
        raise BspError(f"{label}: invalid count or relative array bounds")


def decode_vvd(data: bytes, checksum: str) -> list[dict]:
    hdr=parse_source_header(data[:64],"vvd")
    if (hdr.get("version")!=4 or hdr.get("checksum")!=checksum):
        raise BspError("VVD version or Source studio checksum mismatch")
    endian="<" if hdr["endian"]=="little" else ">"
    num_lods=read_at(data,endian,"I",12)[0]
    lod_counts=read_at(data,endian,"8I",16)
    fixups,fixup_start,vertex_start,tangent_start=read_at(data,endian,"4I",48)
    if num_lods<1 or num_lods>8 or lod_counts[0]>MAX_VERTICES:
        raise BspError("VVD LOD count outside supported range")
    needed=lod_counts[0]
    validate_array(data,vertex_start,needed,VVD_VERTEX_SIZE,"VVD positions",MAX_VERTICES)
    if fixups:
        validate_array(data,fixup_start,fixups,12,"VVD fixups",MAX_VERTICES)
        order_ids=[]
        for i in range(fixups):
            lod,source,n=read_at(data,endian,"III",fixup_start+i*12)
            if lod>=num_lods or n>MAX_VERTICES or source+n>needed:
                raise BspError("VVD fixup references invalid Source vertex range")
            # LOD 0 keeps all fixup groups in this order.
            order_ids.extend(range(source,source+n))
            if len(order_ids)>MAX_VERTICES:
                raise BspError("VVD fixups contain excessive vertices")
        if len(order_ids)!=needed:
            raise BspError("VVD LOD 0 fixups do not cover expected vertex count")
    else:
        order_ids=range(needed)
    vertices=[]
    for index in order_ids:
        offset=vertex_start+index*VVD_VERTEX_SIZE
        pos=read_at(data,endian,"3f",offset+16)
        normal=read_at(data,endian,"3f",offset+28)
        uv=read_at(data,endian,"2f",offset+40)
        if not all(math.isfinite(x) and abs(x)<1000000 for x in pos+normal+uv):
            raise BspError("Nonfinite or implausible Source vertex")
        vertices.append({"p":pos,"n":normal,"uv":uv})
    return vertices


def studio_meshes(mdl: bytes, checksum: str) -> list[dict]:
    hdr=parse_source_header(mdl[:64],"mdl")
    if (hdr.get("version")!=49 or hdr.get("checksum")!=checksum or
        hdr.get("endian") not in ("big","little")):
        raise BspError("Decoded MDL v49 header/checksum mismatch")
    if studio_model_summary(mdl,hdr)["status"]!="studiohdr counts and table bounds plausible":
        raise BspError("MDL studiohdr table bounds are not validated")
    order=">" if hdr["endian"]=="big" else "<"
    nbody,bodyptr=read_at(mdl,order,"2I",232)
    validate_array(mdl,bodyptr,nbody,16,"MDL bodyparts",MAX_MODELS)
    bodyparts=[]
    for b in range(nbody):
        p=bodyptr+b*16
        nmodels=read_at(mdl,order,"I",p+4)[0]
        moff=read_at(mdl,order,"I",p+12)[0]
        validate_array(mdl,p+moff,nmodels,MDL_MODEL_SIZE,"MDL submodels",MAX_MODELS)
        models=[]
        for m in range(nmodels):
            modelptr=p+moff+m*MDL_MODEL_SIZE
            meshes,meshoff=read_at(mdl,order,"2I",modelptr+72)
            nverts,vertbyte=read_at(mdl,order,"2I",modelptr+80)
            if vertbyte%VVD_VERTEX_SIZE!=0 or nverts>MAX_VERTICES:
                raise BspError("MDL model vertex byte offset is misaligned")
            validate_array(mdl,modelptr+meshoff,meshes,MDL_MESH_SIZE,
                           "MDL meshes",MAX_MESHES)
            meshlist=[]
            for j in range(meshes):
                pmesh=modelptr+meshoff+j*MDL_MESH_SIZE
                material,modelback,nvertices,voffset=read_at(
                    mdl,order,"4i",pmesh)
                if (modelback!=modelptr-pmesh or nvertices<0 or
                    voffset<0 or voffset+nvertices>nverts or material<0):
                    raise BspError("MDL mesh association/vertex interval invalid")
                meshlist.append({"material":material,"vertex_offset":voffset,
                                 "vertex_count":nvertices,
                                 "model_vertex_base":vertbyte//VVD_VERTEX_SIZE})
            models.append(meshlist)
        bodyparts.append(models)
    return bodyparts


def vtx_triangles(vtx: bytes, studio: list, pool_size: int,
                  checksum: str) -> list[tuple[int,int,int,int]]:
    hdr=parse_source_header(vtx[:64],"vtx")
    if (hdr.get("version")!=7 or hdr.get("checksum")!=checksum or
        hdr.get("endian") not in ("little","big")):
        raise BspError("VTX v7 header/checksum mismatch")
    order=">" if hdr["endian"]=="big" else "<"
    nbody,bodyptr=read_at(vtx,order,"2I",28)
    if nbody!=len(studio):
        raise BspError("VTX/MDL bodypart counts disagree")
    validate_array(vtx,bodyptr,nbody,8,"VTX bodyparts",MAX_MODELS)
    result=[]
    for b in range(nbody):
        pbody=bodyptr+b*8
        nm,mo=read_at(vtx,order,"2I",pbody)
        if nm!=len(studio[b]):
            raise BspError("VTX/MDL model counts disagree")
        validate_array(vtx,pbody+mo,nm,8,"VTX models",MAX_MODELS)
        for m in range(nm):
            pmodel=pbody+mo+m*8
            nlod,lo=read_at(vtx,order,"2I",pmodel)
            if nlod<1 or nlod>8:
                raise BspError("VTX missing supported LOD 0")
            plod=pmodel+lo
            validate_array(vtx,plod,nlod,12,"VTX LODs",8)
            mesh_count,mesh_offset=read_at(vtx,order,"2I",plod)
            if mesh_count!=len(studio[b][m]):
                raise BspError("VTX/MDL mesh counts disagree")
            validate_array(vtx,plod+mesh_offset,mesh_count,9,
                           "VTX meshes",MAX_MESHES)
            for j in range(mesh_count):
                pmesh=plod+mesh_offset+j*9
                group_count,group_offset=read_at(vtx,order,"2I",pmesh)
                validate_array(vtx,pmesh+group_offset,group_count,
                               VTX_STRIP_GROUP_SIZE,"VTX strip groups",MAX_GROUPS)
                source=studio[b][m][j]
                for g in range(group_count):
                    pgroup=pmesh+group_offset+g*VTX_STRIP_GROUP_SIZE
                    numv,vo,numi,io,nums,so=read_at(vtx,order,"6I",pgroup)
                    validate_array(vtx,pgroup+vo,numv,VTX_VERTEX_SIZE,
                                   "VTX group vertices",MAX_VERTICES)
                    validate_array(vtx,pgroup+io,numi,2,
                                   "VTX group indices",MAX_INDICES)
                    validate_array(vtx,pgroup+so,nums,VTX_STRIP_SIZE,
                                   "VTX group strips",MAX_GROUPS)
                    local_to_global=[]
                    for vi in range(numv):
                        v=pgroup+vo+vi*VTX_VERTEX_SIZE
                        orig=read_at(vtx,order,"H",v+4)[0]
                        if orig>=source["vertex_count"]:
                            raise BspError("VTX origMeshVertID outside MDL mesh")
                        absolute=(source["model_vertex_base"]+
                                  source["vertex_offset"]+orig)
                        if absolute>=pool_size:
                            raise BspError("VTX index outside original VVD vertex pool")
                        local_to_global.append(absolute)
                    # Strip indices always address the *group* vertex table.
                    indices=read_at(vtx,order,f"{numi}H",pgroup+io) if numi else ()
                    for st in range(nums):
                        strip=pgroup+so+st*VTX_STRIP_SIZE
                        ni,first,nv,firstvert=read_at(vtx,order,"4I",strip)
                        flags=vtx[strip+18]
                        if (ni>MAX_INDICES or first+ni>numi or
                                firstvert+nv>numv or not (flags&3)):
                            raise BspError("Invalid original VTX strip range/flags")
                        def emit(a,b,c):
                            if a==b or b==c or c==a:return
                            if max(a,b,c)>=numv:
                                raise BspError("VTX strip references nonexistent group vertex")
                            result.append((local_to_global[a],
                                           local_to_global[b],
                                           local_to_global[c],
                                           source["material"]))
                            if len(result)>MAX_TRIANGLES:
                                raise BspError("Too many original Source prop triangles")
                        if flags&1:
                            if ni%3:raise BspError("Source tri-list indices not multiple of 3")
                            for k in range(first,first+ni,3):
                                emit(indices[k],indices[k+1],indices[k+2])
                        elif flags&2:
                            for k in range(first+2,first+ni):
                                a,b1,c=indices[k-2:k+1]
                                emit(*( (b1,a,c) if (k-first)%2 else (a,b1,c) ))
    if not result:
        raise BspError("Original model contains no supported triangle geometry")
    return result


def convert_original_model(mdl: bytes, vvd: bytes, vtx: bytes) -> dict:
    hdr=parse_source_header(mdl[:64],"mdl")
    checksum=hdr.get("checksum")
    if not checksum:
        raise BspError("Original MDL header missing Source checksum")
    pool=decode_vvd(vvd,checksum)
    hierarchy=studio_meshes(mdl,checksum)
    triangles=vtx_triangles(vtx,hierarchy,len(pool),checksum)
    used=sorted({id for a,b,c,_ in triangles for id in (a,b,c)})
    id_map={old:i for i,old in enumerate(used)}
    positions=[v for id in used for v in pool[id]["p"]]
    normals=[v for id in used for v in pool[id]["n"]]
    uvs=[v for id in used for v in pool[id]["uv"]]
    indices=[id_map[id] for a,b,c,_ in triangles for id in (a,b,c)]
    face_mats=[mat for *_,mat in triangles]
    return {"format":"lfd2-source-original-model-v1",
            "source":"original local Xbox Source studio files",
            "model":"models/props_furniture/hotel_chair.mdl",
            "checksum":checksum,"vertices":positions,"normals":normals,
            "uvs":uvs,"indices":indices,"triangle_material_ids":face_mats,
            "triangle_count":len(triangles),"vertex_count":len(used),
            "materials_verified":False,
            "note":"Original vertex/triangle data; material textures and skeletal animation not yet decoded."}


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mdl",type=Path,default=DEFAULT_MDL)
    p.add_argument("--vvd",type=Path,default=DEFAULT_VVD)
    p.add_argument("--vtx",type=Path,default=DEFAULT_VTX)
    p.add_argument("--out",type=Path,default=DEFAULT_OUT)
    p.add_argument("--run",action="store_true",
                   help="Explicitly save one original chair geometry JSON privately")
    args=p.parse_args()
    try:
        for file in (args.mdl,args.vvd,args.vtx):
            if not file.expanduser().resolve().is_relative_to(PRIVATE):
                raise ValueError("Original commercial model inputs must remain inside ignored research/local")
        decoded=convert_original_model(args.mdl.read_bytes(),args.vvd.read_bytes(),
                                       args.vtx.read_bytes())
        print(f"Source v49 studio mesh decoded: {decoded['triangle_count']:,} triangles, "
              f"{decoded['vertex_count']:,} original vertices")
        print(f"Checksum: {decoded['checksum']}; material mapping still pending")
        if args.run:
            target=args.out.expanduser().resolve()
            if (not target.is_relative_to(PRIVATE) or target.exists() or
                    target==PRIVATE):
                raise ValueError("Output must be a new file under private research/local")
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open("x",encoding="utf-8") as handle:
                json.dump(decoded,handle,separators=(",",":"))
            print("Private authentic model geometry:",target)
        else:
            print("Read-only validation finished; use --run to save mesh JSON privately.")
        print("Original game files not modified or uploaded.")
        return 0
    except (OSError,ValueError,struct.error,BspError) as exc:
        print("Original studio mesh converter stopped:",exc,file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
