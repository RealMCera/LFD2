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
    from .bsp_to_browser_mesh import ROOT,BspError,decode_valve_lzma
    from .probe_original_hotel_model import (
        parse_source_header,studio_model_summary,OUT_DIR,DEFAULT_MODEL,validate_name,
    )
except ImportError:
    from bsp_to_browser_mesh import ROOT,BspError,decode_valve_lzma
    from probe_original_hotel_model import (
        parse_source_header,studio_model_summary,OUT_DIR,DEFAULT_MODEL,validate_name,
    )

PRIVATE=(ROOT/"research"/"local").resolve()
DEFAULT_MDL=OUT_DIR/"decoded"/DEFAULT_MODEL
DEFAULT_VVD=OUT_DIR/"models"/"props_furniture"/"hotel_chair.360.vvd"
DEFAULT_VTX=OUT_DIR/"models"/"props_furniture"/"hotel_chair.dx90.360.vtx"
DEFAULT_OUT=PRIVATE/"hotel-chair.mesh.json"
MAX_VERTICES=100000
VVD_TANGENT_SIZE=16
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


def describe_vvd_layout(data: bytes) -> dict:
    """Report only public layout metadata from one privately held Xbox VVD.

    No vertex payload, raw original data, geometry, or files are exported.
    This compares the Source 48-byte vertex assumption to the actual on-disk
    VVD header and identifies possible embedded Valve LZMA wrappers.
    """
    parsed=parse_source_header(data[:64],"vvd")
    if parsed.get("version")!=4 or parsed.get("endian") not in ("big","little"):
        raise BspError("VVD v4 header not independently recognized")
    endian=">" if parsed["endian"]=="big" else "<"
    num_lods=read_at(data,endian,"I",12)[0]
    lod_counts=list(read_at(data,endian,"8I",16))
    fixups,fixup_start,vertex_start,tangent_start=read_at(data,endian,"4I",48)
    n=lod_counts[0]
    remain=max(0,len(data)-vertex_start) if vertex_start<=len(data) else 0
    at_start=(data[vertex_start:vertex_start+8].hex(" ")
              if 0<=vertex_start<len(data) else "outside file")
    hints=[]
    if vertex_start==0 or vertex_start>=len(data):
        hints.append("VVD vertex data start absent/out of range")
    if n>0 and vertex_start<=len(data) and vertex_start+n*48>len(data):
        hints.append("48-byte Source vertex array does not fit; Xbox data layout may differ")
    if 0<=vertex_start<len(data) and data[vertex_start:vertex_start+4]==b"LZMA":
        hints.append("Valve LZMA signature found at VVD vertex offset; compressed payload needs decoder")
    if 0<=vertex_start<len(data) and n:
        hints.append(f"Bytes available per declared LOD0 vertex: {remain/n:.2f}")
    return {
        "file_bytes":len(data),"header_magic":data[:4].hex(" "),
        "header_version":parsed["version"],"byte_order":parsed["endian"],
        "checksum":parsed["checksum"],"lod_count":num_lods,
        "lod_vertex_counts":lod_counts,
        "fixup_count":fixups,"fixup_start":fixup_start,
        "vertex_data_start":vertex_start,"tangent_data_start":tangent_start,
        "assumed_vertex_bytes":VVD_VERTEX_SIZE,
        "expected_vertex_end_48":vertex_start+n*VVD_VERTEX_SIZE,
        "available_vertex_bytes":remain,
        "vertex_start_first8_hex":at_start,
        "hints":hints,
    }


def expanded_vvd(data: bytes) -> tuple[bytes,dict]:
    """Decompress Xbox VVD's Valve LZMA vertex/tangent payload.

    The fixed 64-byte header is uncompressed. Xbox stores a second,
    independent LZMA wrapper at header.vertexDataStart; its decoded bytes
    replace the vertex + tangent arrays. Read declared sizes, verify exact
    expected length (LOD0*48 vertex bytes + LOD0*16 tangent bytes), and
    preserve original file-relative header pointers before parsing.
    """
    detail=describe_vvd_layout(data)
    vertex_start=detail["vertex_data_start"]
    vertex_count=detail["lod_vertex_counts"][0]
    tangent_start=detail["tangent_data_start"]
    if not (1<=vertex_count<=MAX_VERTICES and
            64<=vertex_start<len(data) and
            detail["lod_count"] in range(1,9)):
        raise BspError("Invalid Xbox VVD vertex pool header")
    if data[vertex_start:vertex_start+4]!=b"LZMA":
        return data,{"compression":"none","expanded_bytes":len(data)}
    # All 1395 chair vertices are stored in one LOD0 group, and the
    # tangent block follows the 48-byte Source vertex pool directly.
    required_tangent_start=vertex_start+vertex_count*VVD_VERTEX_SIZE
    required_end=required_tangent_start+vertex_count*VVD_TANGENT_SIZE
    if tangent_start!=required_tangent_start or required_end>10*1024*1024:
        raise BspError("Xbox compressed VVD has unexpected tangent/vertex layout")
    raw=data[vertex_start:]
    if len(raw)<17:
        raise BspError("Truncated Xbox VVD LZMA wrapper")
    header_candidates=[struct.unpack_from("<II",raw,4),
                       struct.unpack_from(">II",raw,4)]
    desired=required_end-vertex_start
    exact=[(decoded,compressed) for decoded,compressed in header_candidates
           if decoded==desired and compressed==len(raw)-17]
    if len(exact)!=1:
        raise BspError(
            "Xbox VVD LZMA declared sizes disagree with Source LOD0 vertex+tangent "
            f"allocation: expected {desired} decoded bytes and "
            f"{len(raw)-17} compressed bytes; found {header_candidates}"
        )
    decoded=decode_valve_lzma(raw,desired,detail["byte_order"]=="big" and ">" or "<",
                                allow_studio_no_eos=True)
    if len(decoded)!=desired:
        raise BspError("Xbox VVD LZMA decompressed size mismatch")
    expanded=data[:vertex_start]+decoded
    if len(expanded)!=required_end:
        raise BspError("Xbox VVD vertex/tangent block did not end at declared size")
    return expanded,{"compression":"Valve LZMA",
                     "compressed_bytes":len(raw),
                     "decoded_vertex_bytes":vertex_count*VVD_VERTEX_SIZE,
                     "decoded_tangent_bytes":vertex_count*VVD_TANGENT_SIZE,
                     "expanded_bytes":len(expanded)}


def decode_vvd(data: bytes, checksum: str) -> list[dict]:
    hdr=parse_source_header(data[:64],"vvd")
    if (hdr.get("version")!=4 or hdr.get("checksum")!=checksum):
        raise BspError("VVD version or Source studio checksum mismatch")
    data,_compression=expanded_vvd(data)
    endian="<" if hdr["endian"]=="little" else ">"
    num_lods=read_at(data,endian,"I",12)[0]
    lod_counts=read_at(data,endian,"8I",16)
    fixups,fixup_start,vertex_start,tangent_start=read_at(data,endian,"4I",48)
    if num_lods<1 or num_lods>8 or lod_counts[0]>MAX_VERTICES:
        raise BspError("VVD LOD count outside supported range")
    needed=lod_counts[0]
    try:
        validate_array(data,vertex_start,needed,VVD_VERTEX_SIZE,"VVD positions",MAX_VERTICES)
    except BspError as exc:
        # Retain strict limits and explain which assumption failed rather than
        # guessing Xbox vertex stride or silently truncating the original mesh.
        meta=describe_vvd_layout(data)
        raise BspError(
            "VVD positions: 48-byte Source vertex array exceeds local Xbox VVD; "
            f"LOD0={meta['lod_vertex_counts'][0]}, "
            f"vertex_start={meta['vertex_data_start']}, "
            f"expected_end={meta['expected_vertex_end_48']}, "
            f"file_bytes={meta['file_bytes']}; "
            "run --diagnose-vvd for exact original header layout"
        ) from exc
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


MAX_DECODED_VTX = 16 * 1024 * 1024


def expanded_vtx(data: bytes, checksum: str) -> tuple[bytes,dict]:
    """Inspect and optionally expand the Xbox VTX bodypart block.

    A Source v7 VTX header is 36 bytes; some Xbox archives store following
    optimized model data as a bounded Valve LZMA member. No guessed bodypart
    counts/offsets are used: expand only if its own exact wrapper is present.
    """
    hdr=parse_source_header(data[:64],"vtx")
    if hdr.get("version")!=7 or hdr.get("checksum")!=checksum:
        raise BspError("VTX header checksum/version mismatch")
    order=">" if hdr["endian"]=="big" else "<"
    count,start=read_at(data,order,"2I",28)
    if not 1<=count<=MAX_MODELS or not 36<=start<len(data):
        raise BspError("VTX original bodypart header offset/count invalid")
    if data[start:start+4]!=b"LZMA":
        return data,{"compression":"none","bodypart_offset":start,
                     "bodypart_count":count,"file_bytes":len(data)}
    raw=data[start:]
    if len(raw)<17:
        raise BspError("Truncated Xbox VTX Valve LZMA wrapper")
    # Wrapper sizes can be little or big endian regardless of the studio file
    # byte order. Both 32-bit fields must agree with the actual stored bytes.
    candidates=[(o,*read_at(raw,o,"2I",4)) for o in ("<",">")]
    good=[(o,unpacked,compressed) for o,unpacked,compressed in candidates
          if 8*count<=unpacked<=MAX_DECODED_VTX
          and compressed==len(raw)-17]
    if len(good)!=1:
        raise BspError(
            "Xbox VTX LZMA sizes do not match bounded Source bodypart data: "
            f"wrapper={candidates}, compressed_available={len(raw)-17}"
        )
    decoded=decode_valve_lzma(raw,good[0][1],order)
    if len(decoded)!=good[0][1]:
        raise BspError("Original Xbox VTX LZMA unpacked size mismatch")
    output=data[:start]+decoded
    validate_array(output,start,count,8,"decompressed VTX bodyparts",MAX_MODELS)
    return output,{"compression":"Valve LZMA","bodypart_offset":start,
                   "bodypart_count":count,"compressed_bytes":len(raw),
                   "decoded_bodypart_bytes":len(decoded),
                   "expanded_bytes":len(output)}


def diagnose_studio_hierarchy(mdl: bytes, vtx: bytes) -> dict:
    """Read-only counts/offsets, never original vertices or model geometry."""
    hdr=parse_source_header(mdl[:64],"mdl")
    tx=parse_source_header(vtx[:64],"vtx")
    if hdr.get("version")!=49 or tx.get("version")!=7 or (
        hdr.get("checksum")!=tx.get("checksum")
    ):
        raise BspError("Studio hierarchy diagnosis requires checksum-matched v49/v7 files")
    mdle=">" if hdr["endian"]=="big" else "<"
    txe=">" if tx["endian"]=="big" else "<"
    mb,mbptr=read_at(mdl,mdle,"2I",232)
    vb,vbptr=read_at(vtx,txe,"2I",28)
    if not (1<=mb<=MAX_MODELS and 1<=vb<=MAX_MODELS
            and mbptr+mb*16<=len(mdl) and 36<=vbptr<len(vtx)):
        raise BspError("Studio hierarchy bodypart bounds invalid")
    mdls=[]
    for i in range(mb):
        pos=mbptr+16*i
        num=read_at(mdl,mdle,"I",pos+4)[0]
        offset=read_at(mdl,mdle,"I",pos+12)[0]
        mdls.append({"part":i,"mdlnummodels":num,
                     "mdlmodeloffset_relative":offset,
                     "mdlmodel_start":pos+offset})
    prefix=vtx[vbptr:vbptr+8]
    wrapper=prefix[:4]==b"LZMA"
    raw= {"vtx_version":tx["version"],"vtx_endian":tx["endian"],
          "checksum_match":hdr["checksum"]==tx["checksum"],
          "mdl_bodyparts":mb,"mdl_bodypart_offset":mbptr,
          "mdl_model_counts":mdls,
          "vtx_bodyparts":vb,"vtx_bodypart_offset":vbptr,
          "vtx_first_bodypart_eight_bytes_hex":prefix.hex(" "),
          "vtx_bodypart_lzma_wrapper":wrapper,
          "vtx_file_bytes":len(vtx)}
    if wrapper:
        unpacked,info=expanded_vtx(vtx,hdr["checksum"])
        raw["decoded_vtx"] = info
        vtx=unpacked
    else:
        raw["decoded_vtx"]={"compression":"none"}
    parts=[]
    for i in range(vb):
        p=vbptr+i*8
        if p+8>len(vtx):
            raise BspError("Original VTX bodypart outside data")
        n,offset=read_at(vtx,txe,"2I",p)
        parts.append({"part":i,"vtxnummodels":n,
                      "vtxmodeloffset_relative":offset,
                      "vtxmodel_start":p+offset})
    raw["vtx_model_counts"]=parts
    return raw


def vtx_triangles(vtx: bytes, studio: list, pool_size: int,
                  checksum: str) -> list[tuple[int,int,int,int]]:
    hdr=parse_source_header(vtx[:64],"vtx")
    if (hdr.get("version")!=7 or hdr.get("checksum")!=checksum or
        hdr.get("endian") not in ("little","big")):
        raise BspError("VTX v7 header/checksum mismatch")
    order=">" if hdr["endian"]=="big" else "<"
    vtx,_vtx_compression=expanded_vtx(vtx,checksum)
    nbody,bodyptr=read_at(vtx,order,"2I",28)
    if nbody!=len(studio):
        raise BspError("VTX/MDL bodypart counts disagree")
    validate_array(vtx,bodyptr,nbody,8,"VTX bodyparts",MAX_MODELS)
    result=[]
    for b in range(nbody):
        pbody=bodyptr+b*8
        nm,mo=read_at(vtx,order,"2I",pbody)
        if nm!=len(studio[b]):
            raise BspError(
                "VTX/MDL model counts disagree at bodypart "
                f"{b}: VTX={nm}, MDL={len(studio[b])}, "
                f"bodypart_offset={pbody}, model_array_offset={mo}, "
                f"compression={_vtx_compression['compression']}; "
                "run --diagnose-hierarchy for read-only Source offsets"
            )
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


def convert_original_model(mdl: bytes, vvd: bytes, vtx: bytes, *,
                           model_name: str = DEFAULT_MODEL) -> dict:
    model_name=validate_name(model_name)
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
            "model":model_name,
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
    p.add_argument("--diagnose-vvd",action="store_true",
                   help="Read-only report of VVD header, LOD0 vertex counts, offsets and source stride fit")
    p.add_argument("--diagnose-hierarchy",action="store_true",
                   help="Read-only compare MDL/VTX bodypart/model offsets and inspect any Xbox VTX LZMA")
    args=p.parse_args()
    try:
        for file in (args.mdl,args.vvd,args.vtx):
            if not file.expanduser().resolve().is_relative_to(PRIVATE):
                raise ValueError("Original commercial model inputs must remain inside ignored research/local")
        if args.diagnose_vvd:
            diag=describe_vvd_layout(args.vvd.read_bytes())
            print("ORIGINAL XBOX VVD LAYOUT (metadata only; no model data exported)")
            print(json.dumps(diag,indent=2))
            if "Valve LZMA signature" in " ".join(diag["hints"]):
                _expanded,info=expanded_vvd(args.vvd.read_bytes())
                print("Verified bounded Source VVD decompression:",info)
            print("Read-only VVD diagnosis complete. No geometry written.")
            return 0
        if args.diagnose_hierarchy:
            report=diagnose_studio_hierarchy(args.mdl.read_bytes(),
                                               args.vtx.read_bytes())
            print("ORIGINAL XBOX MDL/VTX HIERARCHY (read-only metadata)")
            print(json.dumps(report,indent=2))
            print("No original geometry exported.")
            return 0
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
