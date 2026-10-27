#!/usr/bin/env python3
"""Inspect and optionally copy ONE verified original Xbox studio model triplet.

Uses only the owner's local left4dead2/zip0.360.zip. The default reads bounded
ZIP header metadata and 36-byte Source MDL/VVD/VTX payload headers. --extract
explicitly copies the unmodified three original model files into ignored
research/local/original-models/ for subsequent private mesh decoding.

It does not render or decode geometry, download, upload, modify the ZIP, copy
the whole game, or write files into the public Git repository.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import struct
import sys

try:
    from .bsp_to_browser_mesh import ROOT,decode_valve_lzma,BspError
    from .inspect_hotel_model_assets import PACK, model_files
    from .scan_xbox_zip_directory import scan_xbox_zip
    from .probe_xbox_texture_headers import inspect_local_header
    from .inspect_xbox_zip import XboxZipError
except ImportError:
    from bsp_to_browser_mesh import ROOT,decode_valve_lzma,BspError
    from inspect_hotel_model_assets import PACK, model_files
    from scan_xbox_zip_directory import scan_xbox_zip
    from probe_xbox_texture_headers import inspect_local_header
    from inspect_xbox_zip import XboxZipError

OUT_DIR = (ROOT / "research" / "local" / "original-models").resolve()
DEFAULT_MODEL = "models/props_furniture/hotel_chair.mdl"
MAX_MEMBER = 32 * 1024 * 1024
HEADER_BYTES = 64
MAX_DECODED_MDL = 32 * 1024 * 1024


def validate_name(name: str) -> str:
    normalized = name.casefold().replace("\\", "/")
    if (not normalized.startswith("models/") or
        not normalized.endswith(".mdl") or len(normalized) > 220 or
        any(part in ("", ".", "..") for part in normalized.split("/")) or
        any(not (ch.isascii() and (ch.isalnum() or ch in "_./-"))
            for ch in normalized)):
        raise XboxZipError(f"Invalid Source model path: {name!r}")
    return normalized


def find_components(entries: list[dict], model: str) -> dict[str,dict]:
    paths = model_files(validate_name(model))
    lookup = {}
    duplicates = set()
    for entry in entries:
        key = entry["name"].casefold().replace("\\", "/")
        if key in lookup:
            duplicates.add(key)
        else:
            lookup[key] = entry
    found = {}
    for part in ("mdl", "vvd", "vtx"):
        options = [lookup[name] for name in paths[part]
                   if name in lookup and name not in duplicates]
        if len(options) != 1:
            raise XboxZipError(
                f"{part} requires exactly one unambiguous companion "
                f"for {model}; found {len(options)}")
        found[part] = options[0]
    return found


def bounded_member(stream, size: int, directory_start: int, entry: dict) -> dict:
    if entry["method"] != 0 or entry["flags"] & 1:
        raise XboxZipError("Encrypted/compressed Xbox ZIP member not supported")
    size_in_zip = entry["compressed_size"]
    if (size_in_zip != entry["uncompressed_size"] or
        not 64 <= size_in_zip <= MAX_MEMBER):
        raise XboxZipError("Model member has invalid size or exceeds 32 MB safety limit")
    local = inspect_local_header(stream, size, directory_start, entry)
    if (local["status"] != "local_header_found" or
        not local.get("local_filename_matches") or
        local.get("local_method") != 0 or
        local.get("local_flags", 0) & 1):
        raise XboxZipError(f"Model local ZIP header mismatch: {entry['name']}")
    if (local.get("local_compressed_bytes") not in (0, size_in_zip) or
        local.get("local_uncompressed_bytes") not in (0, size_in_zip)):
        raise XboxZipError("Model local ZIP byte length mismatch")
    offset = local["candidate_payload_offset"]
    if offset + size_in_zip > directory_start:
        raise XboxZipError("Model payload overlaps ZIP directory")
    stream.seek(offset)
    prefix = stream.read(HEADER_BYTES)
    if len(prefix) != HEADER_BYTES:
        raise XboxZipError("Truncated model header")
    return {"entry":entry,"offset":offset,"length":size_in_zip,"header":prefix}


def parse_source_header(prefix: bytes, kind: str) -> dict:
    """Interpret conservative Source header fields, trying both byte orders."""
    if kind in ("mdl", "vvd"):
        valid_magic = (b"IDST", b"TSDI") if kind=="mdl" else (b"IDSV", b"VSDI")
        if prefix[:4] not in valid_magic:
            return {"kind":kind,"magic_hex":prefix[:4].hex(" "),
                    "note":"Unrecognized studio-file signature; no format assumed"}
        version_offset, checksum_offset = 4,8
        plausible=range(36,81) if kind=="mdl" else range(3,7)
    else:
        version_offset, checksum_offset=0,16
        plausible=range(6,10)
    possible=[]
    for byteorder in ("<",">"):
        version=struct.unpack_from(byteorder+"I",prefix,version_offset)[0]
        if version in plausible:
            possible.append((byteorder,version))
    if len(possible)!=1:
        return {"kind":kind,"magic_hex":prefix[:4].hex(" "),
                "note":"Version/endian is not uniquely plausible",
                "little_version":struct.unpack_from("<I",prefix,version_offset)[0],
                "big_version":struct.unpack_from(">I",prefix,version_offset)[0]}
    order,version=possible[0]
    checksum=struct.unpack_from(order+"I",prefix,checksum_offset)[0]
    result={"kind":kind,"version":version,
            "endian":"little" if order=="<" else "big",
            "checksum":f"{checksum:08x}"}
    if kind=="vvd":
        result["lod_count"]=struct.unpack_from(order+"I",prefix,12)[0]
    if kind=="vtx":
        result["lod_count"]=struct.unpack_from(order+"I",prefix,20)[0]
        result["bodypart_count"]=struct.unpack_from(order+"I",prefix,28)[0]
    return result


def decode_xbox_mdl(stream, record: dict) -> bytes:
    """Decode a Source LZMA-wrapped .360.mdl locally with size bounds.

    This is a compressed *model payload* inside a stored Xbox ZIP member.
    Do not confuse that wrapper with ZIP deflate or an invalid MDL.
    """
    stream.seek(record["offset"])
    payload=stream.read(record["length"])
    if len(payload)!=record["length"]:
        raise XboxZipError("Short read of private compressed studio model")
    if payload.startswith(b"LZMA"):
        if len(payload)<17:
            raise XboxZipError("Truncated LZMA-wrapped Xbox MDL")
        sizes=(struct.unpack_from(">I",payload,4)[0],
               struct.unpack_from("<I",payload,4)[0])
        if not any(64<=n<=MAX_DECODED_MDL for n in sizes):
            raise XboxZipError("Decoded MDL size exceeds safe 32MB limit")
        try:
            decoded=decode_valve_lzma(payload,0,">")
        except (BspError,ValueError) as error:
            raise XboxZipError("Unable to decode Xbox LZMA-wrapped MDL: "+str(error)) from error
    else:
        decoded=payload
    if len(decoded)>MAX_DECODED_MDL or len(decoded)<HEADER_BYTES:
        raise XboxZipError("Decoded MDL size outside studio model limits")
    return decoded


def save_decoded_mdl(studio: bytes, model: str, root: Path = OUT_DIR) -> Path:
    """Save only an already validated MDL under ignored local research.

    The unmodified .360.mdl extracted previously is not changed.
    """
    model=validate_name(model)
    folder=root.resolve()
    if not folder.is_relative_to(OUT_DIR):
        raise XboxZipError("Decoded MDL must stay in original-models private folder")
    output=(folder/"decoded"/model).resolve()
    if not output.is_relative_to(folder) or output.exists():
        raise XboxZipError("Decoded MDL output already exists or escapes private folder")
    if (len(studio)<HEADER_BYTES or len(studio)>MAX_DECODED_MDL or
            studio[:4] not in (b"IDST",b"TSDI")):
        raise XboxZipError("Not a validated decompressed Source MDL")
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("xb") as dest:
        dest.write(studio)
    return output


def studio_model_summary(data: bytes, parsed: dict) -> dict:
    """Probe conservative studiohdr_t offsets only after MDL decode.

    Source v48-v49 studiohdr_t has a 408-byte header; header arrays contain
    model topology metadata, not the actual VVD vertices / VTX triangles.
    Bounds-check relative offsets before suggesting they are valid.
    """
    if "version" not in parsed or len(data)<408:
        return {"status":"no supported 408-byte studiohdr_t available"}
    order="<" if parsed["endian"]=="little" else ">"
    declared=struct.unpack_from(order+"I",data,76)[0]
    bones,bone_offset=struct.unpack_from(order+"II",data,156)
    materials,material_offset=struct.unpack_from(order+"II",data,204)
    bodyparts,bodypart_offset=struct.unpack_from(order+"II",data,232)
    def bounds(n,at,minimum_size):
        return (n==0 or (0<at<len(data) and n<=4096 and
                         n*minimum_size<=len(data)-at))
    if not all((bounds(bones,bone_offset,216),
                bounds(materials,material_offset,64),
                bounds(bodyparts,bodypart_offset,16))):
        return {"status":"studiohdr arrays outside decoded MDL; format needs inspection",
                "bones":bones,"textures":materials,"bodyparts":bodyparts,
                "bodypart_offset":bodypart_offset}
    return {"status":"studiohdr counts and table bounds plausible",
            "declared_mdl_bytes":declared,"decoded_mdl_bytes":len(data),
            "name":data[12:76].split(b"\0",1)[0].decode("ascii","replace"),
            "bones":bones,"textures":materials,"bodyparts":bodyparts,
            "bodypart_offset":bodypart_offset,"texture_offset":material_offset}


def inspect_model(stream, filesize: int, directory: dict,
                  model: str) -> tuple[dict[str,dict],dict]:
    items=find_components(directory["entries"],model)
    records={part:bounded_member(stream,filesize,directory["directory_offset"],entry)
             for part,entry in items.items()}
    model_payload=decode_xbox_mdl(stream,records["mdl"])
    headers={part:parse_source_header(
                model_payload if part=="mdl" else record["header"],part)
             for part,record in records.items()}
    headers["mdl"]["on_disk_encoding"]=(
        "Valve LZMA" if records["mdl"]["header"].startswith(b"LZMA")
        else "uncompressed")
    headers["mdl"]["decoded_bytes"]=len(model_payload)
    headers["mdl"]["studio"]=studio_model_summary(model_payload,headers["mdl"])
    checks=[hdr["checksum"] for hdr in headers.values() if "checksum" in hdr]
    matches=(len(checks)==3 and len(set(checks))==1)
    return records,{"parts":headers,"checksum_match":matches,
                    "all_headers_recognized":len(checks)==3}


def extract_model(stream, records: dict[str,dict], directory: Path) -> list[Path]:
    """Preserve original names privately; reject overwrite or unsafe path."""
    directory=directory.expanduser().resolve()
    if not directory.is_relative_to(OUT_DIR):
        raise XboxZipError("Original model extraction must stay under ignored research/local/original-models")
    selected=[]
    for item in records.values():
        name=item["entry"]["name"].replace("\\","/")
        if (not name.startswith("models/") or
            any(x in ("", ".", "..") for x in name.split("/")) or
            any(not (ch.isascii() and (ch.isalnum() or ch in "_./-"))
                for ch in name)):
            raise XboxZipError("Unsafe original model filename")
        target=(directory/name).resolve()
        if not target.is_relative_to(directory) or target.exists():
            raise XboxZipError("Refusing unsafe or already existing private model output")
        selected.append((item,target))
    saved=[]
    for item,target in selected:
        target.parent.mkdir(parents=True,exist_ok=True)
        stream.seek(item["offset"])
        with target.open("xb") as out:
            remaining=item["length"]
            while remaining:
                buf=stream.read(min(65536,remaining))
                if not buf:
                    raise XboxZipError("Unexpected short original model data")
                out.write(buf)
                remaining-=len(buf)
        saved.append(target)
    return saved


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model",default=DEFAULT_MODEL,
                   help="Original BSP model path; defaults to hotel chair")
    p.add_argument("--pack",type=Path,default=PACK)
    p.add_argument("--extract",action="store_true",
                   help="Opt in to extracting one original model trio privately")
    p.add_argument("--write-decoded-mdl",action="store_true",
                   help="Save decompressed Source .mdl in ignored research/local (never overwrites)")
    args=p.parse_args()
    try:
        source=args.pack.expanduser().resolve()
        report=scan_xbox_zip(source)
        with source.open("rb") as stream:
            records,header=inspect_model(stream,source.stat().st_size,report,args.model)
            print("ORIGINAL XBOX STUDIO MODEL:",args.model)
            for part,record in records.items():
                print(f"  {part.upper()}: {record['entry']['name']} "
                      f"({record['length']:,} bytes)")
                print(f"    header: {header['parts'][part]}")
            print("  All three studio headers plausibly decoded:",
                  header["all_headers_recognized"])
            print("  Original Source checksum matches between all three:",
                  header["checksum_match"])
            if args.write_decoded_mdl:
                if not header["all_headers_recognized"] or not header["checksum_match"]:
                    raise XboxZipError("Decoded model header or triplet checksums failed; refusing to save")
                decoded=decode_xbox_mdl(stream,records["mdl"])
                out=save_decoded_mdl(decoded,args.model)
                print(f"  PRIVATE DECOMPRESSED MDL: {out} ({len(decoded):,} bytes)")
            if args.extract:
                saved=extract_model(stream,records,OUT_DIR)
                for path in saved:
                    print(f"  PRIVATE FILE: {path}")
                print("Only these three original model files copied locally.")
            else:
                print("Read-only header probe complete. --write-decoded-mdl saves only "
                      "the decompressed MDL privately; --extract copies raw trio.")
        return 0
    except (OSError,ValueError,struct.error,XboxZipError,BspError) as error:
        print(f"Xbox original model probe stopped: {error}",file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
