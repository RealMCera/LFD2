#!/usr/bin/env python3
"""Read Xbox Source ZIP central-directory metadata without extracting any files.

Some Xbox 360 Source 360.zip archives contain unusual or malformed *extra
field payloads*. Python zipfile validates their internals and rejects them.
This inspector reads only the fixed ZIP directory records and skips extras
according to the outer byte counts. It does not read or decompress payloads.

Strict input bounds and size limits are intentional; ZIP64 and multi-disk
archives are reported as unsupported rather than guessed at.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent.parent
DEFAULT = HERE / "game-extracted" / "left4dead2" / "zip0.360.zip"
EOCD_MAGIC = b"PK\x05\x06"
CENTRAL_MAGIC = b"PK\x01\x02"
MAX_DIRECTORY = 128 * 1024 * 1024
MAX_FILES = 150_000
MAX_NAME = 1024
MAX_TAIL = 22 + 65535
INTERESTING = {".vmt", ".vtf", ".vtfx", ".mdl", ".vtx", ".vvd", ".vtx360",
               ".phy", ".wav", ".mp3", ".pcf", ".vcd"}


class XboxZipError(ValueError):
    pass


def _eocd(stream, filesize: int) -> dict:
    size = min(filesize, MAX_TAIL)
    stream.seek(filesize - size)
    tail = stream.read(size)
    for pos in range(len(tail) - 22, -1, -1):
        if tail[pos:pos + 4] != EOCD_MAGIC:
            continue
        if pos + 22 > len(tail):
            continue
        sig, disk, cd_disk, disk_count, total_count, cd_size, cd_offset, comment_len = (
            struct.unpack_from("<4s4H2IH", tail, pos)
        )
        if pos + 22 + comment_len != len(tail):
            continue
        if disk or cd_disk or disk_count != total_count:
            raise XboxZipError("Multi-disk/spanned ZIP unsupported; no payload touched")
        if 0xffff in (total_count, disk_count) or 0xffffffff in (cd_size, cd_offset):
            raise XboxZipError("ZIP64 central directory unsupported by this metadata probe")
        if not (0 <= total_count <= MAX_FILES and 0 <= cd_size <= MAX_DIRECTORY):
            raise XboxZipError("Directory exceeds safe file/count limit")
        return {"offset": cd_offset, "size": cd_size, "count": total_count,
                "eocd_pos": filesize - size + pos}
    raise XboxZipError("Standard ZIP end-of-central-directory record not found in final 65557 bytes")


def parse_directory(stream, filesize: int) -> dict:
    """Read only ZIP central records and filenames (skip raw extra/comment bytes)."""
    eocd = _eocd(stream, filesize)
    offset, size = eocd["offset"], eocd["size"]
    actual = eocd["eocd_pos"] - size
    # Prefer EOCD directory offset where valid; tolerate prepended bytes when
    # the directory lies immediately before the EOCD.
    def sig_at(candidate):
        if candidate < 0 or candidate + 4 > filesize:
            return b""
        stream.seek(candidate)
        return stream.read(4)
    if sig_at(offset) != CENTRAL_MAGIC:
        if sig_at(actual) != CENTRAL_MAGIC:
            raise XboxZipError(f"Central header missing at EOCD offset {offset:,} "
                               f"or computed position {actual:,}")
        offset = actual
    if offset + size > filesize or offset + size > eocd["eocd_pos"]:
        raise XboxZipError("Central directory points beyond ZIP file bounds")
    end = offset + size
    stream.seek(offset)
    by_extension = Counter()
    names = []
    sample = []
    total_compressed = 0
    skipped_extra_bytes = 0
    for index in range(eocd["count"]):
        if stream.tell() + 46 > end:
            raise XboxZipError(f"Central entry {index} extends beyond directory")
        record = stream.read(46)
        if len(record) != 46 or record[:4] != CENTRAL_MAGIC:
            raise XboxZipError(f"Invalid central header at entry {index}")
        fields = struct.unpack("<I6H3I5H2I", record)
        flags, method, compressed = fields[3], fields[4], fields[8]
        nlen, elen, clen = fields[10], fields[11], fields[12]
        if nlen > MAX_NAME or stream.tell() + nlen + elen + clen > end:
            raise XboxZipError(f"Filename/extra lengths are unsafe at entry {index}")
        filename = stream.read(nlen)
        stream.seek(elen + clen, 1)  # Do not parse unusual Xbox extra fields.
        name = filename.decode("utf-8" if flags & 0x800 else "cp437",
                               errors="replace").replace("\\", "/")
        if not name.endswith("/"):
            suffix = Path(name).suffix.lower()
            by_extension[suffix] += 1
            names.append(name)
            total_compressed += compressed
            if suffix in INTERESTING and len(sample) < 25:
                sample.append(name)
        skipped_extra_bytes += elen
    if stream.tell() > end:
        raise XboxZipError("Central directory overread")
    return {"count":len(names), "entries_declared":eocd["count"],
            "directory_offset":offset,"directory_size":size,
            "extension_counts":by_extension,"sample_assets":sample,
            "filenames":names,"skipped_extra_bytes":skipped_extra_bytes,
            "compressed_bytes_header_total":total_compressed}


def inspect_xbox_zip(path: Path) -> dict:
    filesize=path.stat().st_size
    with path.open("rb") as stream:
        return parse_directory(stream, filesize)


def diagnose_alignment(stream, filesize: int, max_records: int = 4) -> list[str]:
    """Explain an Xbox central directory mismatch using header metadata only.

    Never reads entry contents. At most 8192 bytes are searched after a lost
    central-directory record; any candidate is only diagnostic, not accepted.
    """
    eocd = _eocd(stream, filesize)
    declared = eocd["offset"]
    computed = eocd["eocd_pos"] - eocd["size"]
    results = [
        f"EOCD central offset={declared:,}, size={eocd['size']:,}, "
        f"entry count={eocd['count']:,}",
        f"Directory position computed from EOCD={computed:,} "
        f"(difference={computed-declared:+,})",
    ]
    positions = []
    for pos in (declared, computed):
        if 0 <= pos <= filesize-4 and pos not in positions:
            positions.append(pos)
    for pos in positions:
        stream.seek(pos)
        results.append(f"At offset {pos:,}: signature={stream.read(4).hex(' ')}")
    offset = next((pos for pos in positions
                   if _sig_at(stream, pos, filesize) == CENTRAL_MAGIC), None)
    if offset is None:
        results.append("No fixed central-directory signature at either candidate start.")
        return results
    limit = min(filesize, eocd["eocd_pos"])
    for index in range(min(max_records, eocd["count"])):
        if offset + 46 > limit:
            results.append(f"Entry {index}: header exceeds directory bounds.")
            break
        stream.seek(offset)
        header = stream.read(46)
        if header[:4] != CENTRAL_MAGIC:
            results.append(f"Entry {index}: expected central header at {offset:,}; "
                           f"found {header[:8].hex(' ')}")
            # Search nearby metadata *only*, not archive payloads.
            n = min(8192, max(0, limit-offset))
            stream.seek(offset)
            preview = stream.read(n)
            possible = []
            start = 0
            while len(possible)<4:
                at = preview.find(CENTRAL_MAGIC, start)
                if at < 0: break
                candidate = offset+at
                if candidate + 46 <= limit:
                    stream.seek(candidate)
                    c = stream.read(46)
                    nums = struct.unpack("<I6H3I5H2I",c)
                    name, extra, comment=nums[10],nums[11],nums[12]
                    if 0 < name <= MAX_NAME and candidate+46+name+extra+comment<=limit:
                        possible.append(candidate)
                start=at+4
            results.append(f"Nearby plausible central-header offsets: "
                           + (", ".join(str(p) for p in possible) if possible else "(none in 8192 bytes)"))
            if possible:
                results.append(f"First candidate delta from expected: "
                               f"{possible[0]-offset:+,} bytes")
            break
        fields = struct.unpack("<I6H3I5H2I", header)
        nlen, elen, clen=fields[10],fields[11],fields[12]
        method,flags=fields[4],fields[3]
        following=offset+46+nlen+elen+clen
        results.append(f"Entry {index}: at={offset:,}, flags=0x{flags:04X}, method={method}, "
                       f"filename_bytes={nlen}, extra_bytes={elen}, comment_bytes={clen}, "
                       f"predicted_next={following:,}")
        if nlen > MAX_NAME or following > limit:
            results.append("Entry lengths exceed safe bounds; stop.")
            break
        offset = following
    return results


def _sig_at(stream, offset: int, filesize: int) -> bytes:
    if offset < 0 or offset+4>filesize:
        return b""
    stream.seek(offset)
    return stream.read(4)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path",nargs="?",type=Path,default=DEFAULT)
    parser.add_argument("--limit",type=int,default=20)
    parser.add_argument("--diagnose",action="store_true",
                        help="Show header offsets for first few entries (never archive contents)")
    args=parser.parse_args()
    if not 1<=args.limit<=40:
        parser.error("--limit must be 1..40")
    try:
        path=args.path.expanduser().resolve()
        if args.diagnose:
            with path.open("rb") as stream:
                print(f"Xbox ZIP header alignment diagnosis: {path.name}")
                for line in diagnose_alignment(stream, path.stat().st_size):
                    print("  "+line)
            print("Header metadata only; no game assets were read or extracted.")
            return 0
        record=inspect_xbox_zip(path)
        print(f"Xbox ZIP directory probe: {path.name} ({path.stat().st_size:,} bytes)")
        print(f"Directory offset: {record['directory_offset']:,}; "
              f"size: {record['directory_size']:,}; records: {record['entries_declared']:,}")
        print(f"Directory extras skipped without decoding: {record['skipped_extra_bytes']:,} bytes")
        print(f"File entries found: {record['count']:,}")
        print("EXTENSIONS:")
        for suffix,count in record["extension_counts"].most_common(args.limit):
            print(f"  {suffix or '(none)':<11} {count:>7,}")
        print("FIRST RECOGNIZED MATERIAL/MODEL PATHS:")
        for name in record["sample_assets"][:args.limit]:
            print("  "+name)
        print("\nRead-only directory metadata. No archive entries were extracted or uploaded.")
        return 0
    except (OSError,XboxZipError,struct.error) as error:
        print(f"Xbox ZIP inspection stopped: {error}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
