#!/usr/bin/env python3
"""Examine Xbox Valve ZIP central-directory headers independently of entry lengths.

This is a *diagnostic*, not a ZIP extractor. It reads only the bounded central
directory indicated by EOCD, never compressed asset bodies or local file data.
It scans every PK 01 02 signature and validates filename / fixed-field bounds,
rather than trusting Xbox-specific extra fields to locate subsequent records.
Candidate filenames are metadata, not proof of an extractable archive.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import struct
import sys

try:
    from .inspect_xbox_zip import (_eocd, CENTRAL_MAGIC, MAX_DIRECTORY,
                                   MAX_NAME, DEFAULT, XboxZipError)
except ImportError:
    from inspect_xbox_zip import (_eocd, CENTRAL_MAGIC, MAX_DIRECTORY,
                                  MAX_NAME, DEFAULT, XboxZipError)

MAX_CANDIDATES = 150_000


def scan_directory(stream, filesize: int) -> dict:
    """Scan *only* the EOCD-bounded directory for plausible fixed ZIP headers."""
    eocd = _eocd(stream, filesize)
    start, size = eocd["offset"], eocd["size"]
    end = start + size
    if size > MAX_DIRECTORY or end > eocd["eocd_pos"] or end > filesize:
        raise XboxZipError("EOCD directory bounds are unsafe")
    stream.seek(start)
    directory = stream.read(size)
    if len(directory) != size or not directory.startswith(CENTRAL_MAGIC):
        raise XboxZipError("EOCD directory does not begin with a central-header signature")
    entries = []
    occurrences = 0
    rejected = Counter()
    nextpos = 0
    while True:
        pos = directory.find(CENTRAL_MAGIC, nextpos)
        if pos < 0:
            break
        occurrences += 1
        if occurrences > MAX_CANDIDATES:
            raise XboxZipError("Too many central signature candidates")
        nextpos = pos + 4
        if pos + 46 > size:
            rejected["truncated_header"] += 1
            continue
        fields = struct.unpack_from("<I6H3I5H2I", directory, pos)
        flags, method = fields[3], fields[4]
        nlen, elen, clen = fields[10], fields[11], fields[12]
        disk, local_offset = fields[13], fields[16]
        name_start = pos + 46
        name_end = name_start + nlen
        entry_end = name_end + elen + clen
        if not 1 <= nlen <= MAX_NAME:
            rejected["filename_size"] += 1
            continue
        if entry_end > size or name_end > size:
            rejected["out_of_bounds"] += 1
            continue
        if disk != 0 or local_offset >= start:
            rejected["unsupported_disk_or_offset"] += 1
            continue
        name_bytes = directory[name_start:name_end]
        if any(b < 32 or b == 127 for b in name_bytes):
            rejected["nonprintable_filename"] += 1
            continue
        name = name_bytes.decode("utf-8" if flags & 0x800 else "cp437",
                                 errors="replace").replace("\\", "/")
        entries.append({"offset": start+pos, "end": start+entry_end,
                        "name": name, "extra": elen,
                        "flags": flags, "method": method,
                        "local_offset": local_offset,
                        "compressed_size": fields[8],
                        "uncompressed_size": fields[9]})
    if not entries:
        raise XboxZipError("No structurally plausible central headers in EOCD region")
    suffixes = Counter(Path(item["name"]).suffix.lower()
                       for item in entries if not item["name"].endswith("/"))
    extras = Counter(item["extra"] for item in entries)
    methods = Counter(item["method"] for item in entries)
    adjacent = overlapping = small_gaps = big_gaps = 0
    largest_gap = 0
    for previous, current in zip(entries, entries[1:]):
        gap = current["offset"] - previous["end"]
        if gap == 0:
            adjacent += 1
        elif gap < 0:
            overlapping += 1
        else:
            if gap <= 128:
                small_gaps += 1
            else:
                big_gaps += 1
            largest_gap = max(largest_gap, gap)
    names = [item["name"] for item in entries if not item["name"].endswith("/")]
    return {"eocd_count": eocd["count"], "directory_offset": start,
            "directory_size": size, "raw_signatures": occurrences,
            "candidate_headers": len(entries), "rejected": rejected,
            "adjacent_pairs": adjacent, "overlapping_pairs": overlapping,
            "small_gap_pairs": small_gaps, "large_gap_pairs": big_gaps,
            "largest_gap": largest_gap,
            "first_offset": entries[0]["offset"], "last_offset": entries[-1]["offset"],
            "last_declared_end": entries[-1]["end"], "directory_end": end,
            "extra_lengths": extras, "methods": methods,
            "extensions": suffixes, "filenames": names, "entries": entries}


def scan_xbox_zip(path: Path) -> dict:
    size = path.stat().st_size
    with path.open("rb") as stream:
        return scan_directory(stream, size)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", nargs="?", type=Path, default=DEFAULT)
    p.add_argument("--limit", type=int, default=12,
                   help="Top extension and material filename samples (1-30)")
    args = p.parse_args()
    if not 1 <= args.limit <= 30:
        p.error("--limit must be 1..30")
    try:
        path = args.path.expanduser().resolve()
        r = scan_xbox_zip(path)
        print(f"Xbox ZIP central-directory independent scan: {path.name}")
        print("Read-only: central directory only, no original file payloads.")
        print(f"Directory offset: {r['directory_offset']:,}; size: {r['directory_size']:,}")
        print(f"EOCD declared files: {r['eocd_count']:,}")
        print(f"Raw PK central signatures: {r['raw_signatures']:,}")
        print(f"Structurally plausible header candidates: {r['candidate_headers']:,}")
        print(f"Rejected signatures: {dict(r['rejected'])}")
        print(f"Between consecutive candidates: {r['adjacent_pairs']:,} adjacent, "
              f"{r['overlapping_pairs']:,} overlapping, "
              f"{r['small_gap_pairs']:,} small gaps (1-128B), "
              f"{r['large_gap_pairs']:,} larger gaps")
        print(f"Largest positive gap: {r['largest_gap']:,} bytes")
        print(f"Most common extra lengths: {r['extra_lengths'].most_common(8)}")
        print(f"Compression methods in candidate headers: {r['methods'].most_common(8)}")
        print("Most common candidate filename extensions:")
        for suffix, count in r["extensions"].most_common(args.limit):
            print(f"  {suffix or '(none)':<10} {count:>7,}")
        print("Sample original material-file paths, if present:")
        shown = 0
        for name in r["filenames"]:
            if name.lower().startswith("materials/") and name.lower().endswith(".vmt"):
                print("  " + name)
                shown += 1
                if shown >= args.limit:
                    break
        if shown == 0:
            print("  (no plausible .vmt candidates)")
        if r["candidate_headers"] != r["eocd_count"]:
            print("WARNING: Candidate count differs from EOCD; directory layout remains unverified.")
        else:
            print("Candidate count agrees with EOCD; additional format validation still required.")
        print("Metadata-only probe finished. No assets exported, decoded, or uploaded.")
        return 0
    except (OSError, XboxZipError, struct.error) as error:
        print(f"ZIP signature probe stopped: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
