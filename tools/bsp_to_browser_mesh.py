#!/usr/bin/env python3
"""Convert locally owned Source/Xbox BSP brush geometry to a private browser mesh.

Experimental: supports big/little endian PSBV/VBSP lumps, standard Source
brush face layout, optional Valve LZMA-wrapped lumps and HDR face fallback.
Writes only into research/local/ (gitignored). It does NOT include textures,
props, displacements, game logic, or collision/navigation meshes.
"""
from __future__ import annotations

import argparse
import json
import lzma
import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = ROOT / "game-extracted" / "left4dead2" / "maps" / "c1m1_hotel.360.bsp"
OUTPUT = ROOT / "research" / "local" / "c1m1_hotel.mesh.json"
HEADER_BYTES = 1036
MAX_LUMP_BYTES = 128 * 1024 * 1024
LUMP_NAMES = {0: "entities", 3: "vertices", 7: "faces", 12: "edges",
              13: "surfedges", 27: "original_faces", 58: "hdr_faces"}


class BspError(ValueError):
    pass


def read_directory(data: bytes, layout: str = "auto") -> tuple[str, list[dict], str]:
    if len(data) < HEADER_BYTES:
        raise BspError("Too short for Source BSP directory")
    magic = data[:4]
    if magic not in (b"VBSP", b"PSBV"):
        raise BspError(f"Not recognized as VBSP/PSBV: {magic.hex()}")
    endian = "<" if magic == b"VBSP" else ">"
    version = struct.unpack_from(endian + "I", data, 4)[0]
    if version not in (19, 20, 21, 22):
        raise BspError(f"Unexpected BSP version {version}. Investigate before converting.")
    guesses = {}
    for kind in ("offset_length_version", "version_offset_length"):
        dirs = []
        score = 0
        for index in range(64):
            a, b, c, d = struct.unpack_from(endian + "4I", data, 8 + index * 16)
            offset, size, ver = (a, b, c) if kind == "offset_length_version" else (b, c, a)
            valid = size == 0 or (HEADER_BYTES <= offset and offset + size <= len(data))
            score += int(valid)
            dirs.append({"index": index, "offset": offset, "size": size,
                         "version": ver, "uncompressed_size": d, "valid": valid})
        # Prefer the standard ordering when both appear plausible, but report
        # scores rather than silently treating an Xbox variant as verified.
        guesses[kind] = (score, dirs)
    if layout == "auto":
        layout = max(guesses, key=lambda k: guesses[k][0])
    score, dirs = guesses[layout]
    if score < 62:
        raise BspError(f"Header directory layout not confidently identified: "
                       f"{layout}={score}/64 valid. Scores: "
                       + str({key: value[0] for key, value in guesses.items()}))
    for index in (3, 12, 13):
        if not dirs[index]["size"] or not dirs[index]["valid"]:
            raise BspError(f"Required {LUMP_NAMES[index]} lump is missing or invalid")
    return endian, dirs, layout


def decode_valve_lzma(payload: bytes, expected_size: int, endian: str, *,
                      allow_studio_no_eos: bool = False) -> bytes:
    if len(payload) < 17 or payload[:4] != b"LZMA":
        raise BspError("Compressed lump lacks standard Valve LZMA wrapper")
    # Valve wrapper: "LZMA", realSize:uint32, compressedSize:uint32,
    # properties[5], compressed raw LZMA bytes. Try numeric byte orders
    # because Xbox ports can change the header endianness.
    prop = payload[12]
    lc = prop % 9
    rest = prop // 9
    lp = rest % 5
    pb = rest // 5
    if lc > 8 or lp > 4 or pb > 4:
        raise BspError("Invalid LZMA properties")
    errors = []
    for fmt in (endian, ">" if endian == "<" else "<"):
        actual, compressed = struct.unpack_from(fmt + "II", payload, 4)
        dictionary = struct.unpack_from("<I", payload, 13)[0]
        if dictionary <= 0 or dictionary > MAX_LUMP_BYTES:
            dictionary = struct.unpack_from(">I", payload, 13)[0]
        if not (0 < actual <= MAX_LUMP_BYTES and 0 < compressed <= len(payload)-17
                and 4096 <= dictionary <= MAX_LUMP_BYTES):
            continue
        if expected_size and actual != expected_size:
            continue
        try:
            dec = lzma.LZMADecompressor(
                format=lzma.FORMAT_RAW, filters=[{"id": lzma.FILTER_LZMA1,
                    "dict_size": dictionary, "lc": lc, "lp": lp, "pb": pb}]
            )
            out = dec.decompress(payload[17:17+compressed], max_length=MAX_LUMP_BYTES+1)
            if len(out) == actual:
                return out
            # Xbox studio MDL/VVD/VTX streams sometimes omit the LZMA
            # end-of-stream marker. Their final range-coder flush can
            # synthesize one trailing byte when Python decodes to input
            # exhaustion instead of stopping at Valve's declared length.
            # Enable ONLY for model assets, never BSP/map lump data.
            # We also require the complete compressed member, no EOS marker,
            # and exactly ONE surplus byte; callers then independently
            # validate full studio headers, checksums and index bounds.
            if (allow_studio_no_eos and len(out) == actual + 1
                    and not dec.eof and not dec.unused_data
                    and compressed == len(payload) - 17):
                return out[:actual]
            errors.append(f"{fmt}: expected {actual} bytes; got {len(out)}")
        except (lzma.LZMAError, ValueError) as ex:
            errors.append(str(ex))
    raise BspError("Unable to decode Valve LZMA lump; " + "; ".join(errors[:2]))


def read_lump(data: bytes, entry: dict, endian: str) -> bytes:
    offset, size, actual = (entry[k] for k in ("offset", "size", "uncompressed_size"))
    if not entry["valid"] or size > MAX_LUMP_BYTES:
        raise BspError(f"Lump {entry['index']} has unsafe or invalid size")
    if not size:
        return b""
    payload = data[offset:offset+size]
    if payload.startswith(b"LZMA"):
        return decode_valve_lzma(payload, actual, endian)
    if payload.startswith(b"AMZL"):
        raise BspError(f"Lump {entry['index']} uses unhandled AMZL wrapper")
    if actual and actual != size:
        raise BspError(f"Lump {entry['index']} declares uncompressed {actual}, "
                       f"on disk {size}, but no supported compression wrapper was found "
                       f"(signature {payload[:8].hex(' ')})")
    return payload


def convert(data: bytes, layout: str = "auto", max_triangles: int = 600000) -> dict:
    endian, directory, detected = read_directory(data, layout)
    face_index = next((n for n in (58, 7, 27) if directory[n]["size"]), None)
    if face_index is None:
        raise BspError("No HDR, standard or original face lump. Cannot build brush geometry.")
    chunks = {n: read_lump(data, directory[n], endian) for n in (3, 12, 13, face_index)}
    vertices_raw, edges_raw, surf_raw, faces_raw = (chunks[i] for i in (3,12,13,face_index))
    if not vertices_raw or len(vertices_raw) % 12:
        raise BspError(f"Vertex lump size {len(vertices_raw)} not divisible by 12. "
                       "Xbox format may require additional decoding.")
    if not edges_raw or len(edges_raw) % 4 or not surf_raw or len(surf_raw) % 4:
        raise BspError("Edge or surfedge lump size not aligned to its expected structure")
    if not faces_raw or len(faces_raw) % 56:
        raise BspError(f"Face lump {face_index} size {len(faces_raw)} is not a "
                       "multiple of Source v20 dface_t (56 bytes). Layout needs further research.")
    verts = list(struct.iter_unpack(endian+"3f", vertices_raw))
    if not all(math.isfinite(value) for vertex in verts for value in vertex):
        raise BspError("Nonfinite BSP vertices; stop instead of exporting invalid geometry")
    edges = list(struct.iter_unpack(endian+"2H", edges_raw))
    surf = [p[0] for p in struct.iter_unpack(endian+"i",surf_raw)]
    pos = []
    tris = []
    skips = {"invalid_refs":0, "displacement":0, "degenerate":0}
    for record in range(len(faces_raw)//56):
        ofs=record*56
        firstedge = struct.unpack_from(endian+"i", faces_raw, ofs+4)[0]
        nedge = struct.unpack_from(endian+"h", faces_raw, ofs+8)[0]
        displacement = struct.unpack_from(endian+"h", faces_raw, ofs+12)[0]
        if displacement >= 0:
            skips["displacement"]+=1
            continue
        if nedge<3 or nedge>512 or firstedge<0 or firstedge+nedge>len(surf):
            skips["invalid_refs"]+=1
            continue
        polygon=[]
        for se in surf[firstedge:firstedge+nedge]:
            edgeid=abs(se)
            if edgeid>=len(edges):
                polygon=[];break
            a,b=edges[edgeid]
            vi=a if se>=0 else b
            if vi>=len(verts):
                polygon=[];break
            if not polygon or vi!=polygon[-1]:
                polygon.append(vi)
        if len(polygon)>1 and polygon[0]==polygon[-1]:polygon.pop()
        if len(polygon)<3:
            skips["invalid_refs"]+=1;continue
        for j in range(1,len(polygon)-1):
            a,b,c=polygon[0],polygon[j],polygon[j+1]
            va,vb,vc=verts[a],verts[b],verts[c]
            ux,uy,uz=(vb[k]-va[k] for k in range(3))
            vx,vy,vz=(vc[k]-va[k] for k in range(3))
            area2=(uy*vz-uz*vy)**2+(uz*vx-ux*vz)**2+(ux*vy-uy*vx)**2
            if area2 < 1e-8:
                skips["degenerate"]+=1;continue
            tris.extend((a,b,c))
            if len(tris)//3 >= max_triangles:
                raise BspError(f"Geometry exceeded max {max_triangles:,} triangles. "
                               "Use a larger --max-triangles deliberately.")
    if not tris:
        raise BspError(f"No usable brush triangles from face lump {face_index}. "
                       f"Skipped: {skips}. Needs layout validation before browser preview.")
    used=sorted(set(tris));reindex={old:i for i,old in enumerate(used)}
    flat=[]
    for vi in used:
        flat.extend(round(v,3) for v in verts[vi])
    xs=flat[::3];ys=flat[1::3];zs=flat[2::3]
    return {"format":"source-brush-mesh-0.1", "name":"Local Source BSP brush geometry",
            "source_magic":data[:4].decode("ascii"), "header_layout":detected,
            "face_lump":face_index, "source_vertex_count":len(verts),
            "source_face_count":len(faces_raw)//56,"triangle_count":len(tris)//3,
            "skip_counts":skips,
            "bounds":[[min(xs),min(ys),min(zs)],[max(xs),max(ys),max(zs)]],
            "vertices":flat,"indices":[reindex[n] for n in tris]}


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bsp",type=Path,default=MAP,help="Locally extracted map file")
    p.add_argument("--output",type=Path,default=OUTPUT,help="Private research/local JSON output")
    p.add_argument("--layout",choices=["auto","offset_length_version","version_offset_length"],default="auto")
    p.add_argument("--max-triangles",type=int,default=600000)
    args=p.parse_args()
    path=args.bsp.expanduser().resolve()
    output=args.output.expanduser().resolve()
    if not output.is_relative_to(ROOT/"research"/"local"):
        p.error("Output must stay inside research/local/; never commit game geometry to GitHub")
    if output.exists():
        p.error(f"Refusing to overwrite existing private output: {output}")
    if args.max_triangles<1 or args.max_triangles>3000000:
        p.error("--max-triangles must be 1..3000000")
    try:
        if not path.is_file():raise BspError(f"Missing local map: {path}")
        result=convert(path.read_bytes(),args.layout,args.max_triangles)
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open("x",encoding="utf-8") as stream:
            json.dump(result,stream,separators=(",",":"))
        print(f"Converted locally: {path.name}")
        print(f"Source faces: {result['source_face_count']:,}; triangle mesh: {result['triangle_count']:,}")
        print(f"Selected face lump: {result['face_lump']}; layout: {result['header_layout']}")
        print(f"Bounds: {result['bounds']}")
        print(f"Skipped: {result['skip_counts']}")
        print(f"Private mesh saved: {output} ({output.stat().st_size:,} bytes)")
        print("Next: open docs/map-viewer.html in Chrome and choose this .mesh.json file.")
        print("No textures, props, gameplay, collision, or game executable are included.")
        return 0
    except (OSError,BspError,struct.error,lzma.LZMAError) as ex:
        print(f"Conversion stopped safely: {ex}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
