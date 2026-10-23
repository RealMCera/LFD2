#!/usr/bin/env python3
"""Summarize local extracted Xbox 360 game files without reading their contents.

Reports file counts, extension statistics, likely executable containers, and
the largest files. No code, assets, hashes, or original file data are copied.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = REPO_ROOT / "game-extracted"
LIKELY_CODE_SUFFIXES = {".xex", ".exe", ".dll", ".xbe", ".elf", ".self", ".prx"}
MAGIC_LABELS = {
    b"XEX2": "Xbox 360 XEX2",
    b"MZ": "MZ/PE candidate",
    b"\x7fELF": "ELF",
    b"XBEH": "Xbox XBE",
    b"CON ": "Xbox STFS CON container",
    b"LIVE": "Xbox STFS LIVE container",
    b"PIRS": "Xbox STFS PIRS container",
}


def detect_magic(first: bytes) -> str | None:
    for signature, description in MAGIC_LABELS.items():
        if first.startswith(signature):
            return description
    return None


def summarize(root: Path, count: int) -> int:
    if not root.is_dir():
        raise ValueError(f"Missing game extraction directory: {root}")
    rows: list[tuple[int, str, str, str | None]] = []
    by_suffix: Counter[str] = Counter()
    by_suffix_bytes: Counter[str] = Counter()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        stat = path.stat()
        rel = path.relative_to(root).as_posix()
        suffix = path.suffix.lower() or "(none)"
        with path.open("rb") as handle:
            magic = detect_magic(handle.read(4))
        rows.append((stat.st_size, rel, suffix, magic))
        by_suffix[suffix] += 1
        by_suffix_bytes[suffix] += stat.st_size

    print(f"Root: {root}")
    print(f"Total files: {len(rows)}")
    print(f"Total bytes: {sum(row[0] for row in rows):,}")
    print("\nExtensions (count; total size):")
    for suffix in sorted(by_suffix, key=lambda s: (-by_suffix_bytes[s], s)):
        print(f"  {suffix:<12} {by_suffix[suffix]:>4} files  {by_suffix_bytes[suffix]:>14,} bytes")

    print("\nLikely executable modules and recognizable file headers:")
    candidates = [(rel, size, suffix, magic) for size, rel, suffix, magic in rows
                  if suffix in LIKELY_CODE_SUFFIXES or magic]
    if not candidates:
        print("  (none detected by extension or first 4 bytes)")
    for rel, size, suffix, magic in candidates:
        print(f"  {rel} ({size:,} bytes; {magic or 'extension only'})")

    print(f"\nLargest {count} extracted files:")
    for size, rel, _suffix, magic in sorted(rows, reverse=True)[:count]:
        print(f"  {size:>14,}  {rel}" + (f" [{magic}]" if magic else ""))

    print("\nMetadata only. Do not upload game files or code to your public repo.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=DEFAULT_ROOT)
    parser.add_argument("--top", type=int, default=12, help="Number of largest files (1-100)")
    args = parser.parse_args()
    if not 1 <= args.top <= 100:
        parser.error("--top must be between 1 and 100")
    try:
        return summarize(args.root.expanduser().resolve(), args.top)
    except OSError as exc:
        parser.exit(1, f"File inspection failed: {exc}\n")
    except ValueError as exc:
        parser.exit(2, f"{exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
