#!/usr/bin/env python3
"""Print non-proprietary BSP lump metadata, especially HDR faces and compression."""
from __future__ import annotations
import argparse
from pathlib import Path
from bsp_to_browser_mesh import MAP, read_directory, BspError, LUMP_NAMES

INSPECT=(0,1,2,3,6,7,12,13,26,27,40,53,58)
ALIASES={1:"planes",2:"texdata",6:"texinfo",26:"displacements",53:"lighting_hdr"}
def report(path:Path)->None:
    data=path.read_bytes()
    endian,dirs,layout=read_directory(data)
    print(f"Map: {path.name} ({len(data):,} bytes)")
    print(f"Magic: {data[:4].decode('ascii')}; BSP v{int.from_bytes(data[4:8], 'big' if endian=='>' else 'little')}")
    print(f"Selected directory: {layout} ({endian} endian)")
    for i in INSPECT:
        e=dirs[i]
        prefix=data[e["offset"]:e["offset"]+8] if e["size"] and e["valid"] else b""
        sig=prefix[:4].decode("ascii",errors="backslashreplace")
        compressed=e["uncompressed_size"]!=0 or prefix.startswith(b"LZMA")
        print(f" {i:02d} {LUMP_NAMES.get(i,ALIASES.get(i,'unknown')):<16}"
              f" bytes={e['size']:>10,}  expected_decoded={e['uncompressed_size']:>10,}"
              f" ver={e['version']:>3}  signature={prefix.hex(' ')}"
              f"  {'compressed?' if compressed else 'plain/empty'}")
    if dirs[58]["size"] and not dirs[7]["size"]:
        print("HDR face lump 58 is present; standard faces lump 7 is empty.")
    elif not dirs[7]["size"] and not dirs[58]["size"]:
        print("Both rendered face lumps appear empty: inspect map variant.")
    else:
        print("A rendered face lump is present.")
    print("Header metadata only; no original geometry, code, textures or map files exported.")

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("path",nargs="?",type=Path,default=MAP)
    a=p.parse_args()
    try:report(a.path.expanduser().resolve());return 0
    except (OSError,BspError,ValueError) as ex:
        p.exit(1,f"Probe error: {ex}\n")

if __name__=="__main__":
    raise SystemExit(main())
