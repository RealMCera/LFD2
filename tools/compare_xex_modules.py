#!/usr/bin/env python3
"""Read-only comparison of executable modules from two local Xbox 360 extracts.

Scans for XEX2 magic (even when filenames end in .dll) and compares file
sizes and streaming SHA-256 digests. Does not publish or modify game files.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARCHIVE = REPO_ROOT / "game-extracted"
DEFAULT_DISC = REPO_ROOT / "game-iso-extracted"
READ_SIZE = 1024 * 1024


def get_modules(root: Path) -> dict[str, Path]:
    """Return relative path -> file of XEX2 modules, ignoring symlinks."""
    result: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open("rb") as f:
            if f.read(4) == b"XEX2":
                result[path.relative_to(root).as_posix().lower()] = path
    return result


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as f:
        while data := f.read(READ_SIZE):
            value.update(data)
    return value.hexdigest()


def compare(left: dict[str, Path], right: dict[str, Path]) -> dict[str, list[str]]:
    """Categorize module matches using path, size and exact SHA-256 bytes."""
    results: dict[str, list[str]] = {"identical": [], "different": [], "archive_only": [], "disc_only": []}
    for key in sorted(left.keys() | right.keys()):
        if key not in right:
            results["archive_only"].append(key)
        elif key not in left:
            results["disc_only"].append(key)
        elif left[key].stat().st_size != right[key].stat().st_size:
            results["different"].append(key)
        elif digest(left[key]) == digest(right[key]):
            results["identical"].append(key)
        else:
            results["different"].append(key)
    return results


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE,
                   help="Previously extracted .zar contents (default: game-extracted)")
    p.add_argument("--disc", type=Path, default=DEFAULT_DISC,
                   help="Extracted .iso contents (default: game-iso-extracted)")
    p.add_argument("--all", action="store_true", help="Include matching module paths in console report")
    args = p.parse_args(argv)
    archive = args.archive.expanduser().resolve()
    disc = args.disc.expanduser().resolve()
    if not archive.is_dir() or not disc.is_dir():
        print("Missing extraction folder; check --archive and --disc paths.", file=sys.stderr)
        return 2
    if archive == disc:
        print("Extraction folders are the same; comparison is not meaningful.", file=sys.stderr)
        return 2
    try:
        left = get_modules(archive)
        right = get_modules(disc)
        if not left or not right:
            print(f"No XEX2 modules: archive={len(left)}, disc={len(right)}. Verify extracted files.", file=sys.stderr)
            return 2
        result = compare(left, right)
    except OSError as exc:
        print(f"Cannot inspect modules: {exc}", file=sys.stderr)
        return 1

    print("Read-only Xbox 360 XEX2 comparison (no executable content exported)")
    print(f"Archive extract: {len(left)} modules")
    print(f"Disc extract:    {len(right)} modules")
    for category, label in (("identical", "Byte-identical"), ("different", "Changed"),
                            ("archive_only", "Archive only"), ("disc_only", "Disc only")):
        matches = result[category]
        print(f"{label:15}: {len(matches)}")
        if category != "identical" or args.all:
            for path in matches:
                print("  " + path)
    print("No files changed. Do not commit extracted modules or decompiled pseudocode.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
