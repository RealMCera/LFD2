#!/usr/bin/env python3
"""Catalog local Xbox 360 XEX2 modules without extracting code or game assets.

Scans game-extracted/ for XEX2 signatures, including modules named .dll.
Reports sizes and selected metadata. Nothing is uploaded or changed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__:
    from .inspect_xex import inspect_xex
else:
    from inspect_xex import inspect_xex

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = REPO_ROOT / "game-extracted"

def catalog(root: Path) -> tuple[list[dict], list[str]]:
    records = []
    errors = []
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open("rb") as stream:
            magic = stream.read(4)
        if magic != b"XEX2":
            continue
        relative = path.relative_to(root).as_posix()
        try:
            result = inspect_xex(path)
            records.append({
                "path": relative,
                "bytes": result["size"],
                "module_flags": result["module_flags"],
                "title_id": result.get("title_id", "n/a"),
                "encryption": result.get("encryption_type", "unknown"),
                "compression": result.get("compression_type", "unknown"),
            })
        except (OSError, ValueError) as exc:
            errors.append(f"{relative}: {exc}")
    records.sort(key=lambda item: (-item["bytes"], item["path"].lower()))
    return records, errors

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=DEFAULT_ROOT,
                        help="Extraction root (default: game-extracted)")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        parser.error(f"Extraction folder not found: {root}")

    try:
        records, errors = catalog(root)
    except OSError as exc:
        print(f"Cannot scan extraction: {exc}", file=sys.stderr)
        return 1
    print(f"Xbox 360 XEX2 modules found: {len(records)}")
    print(f"Combined on-disk size: {sum(r['bytes'] for r in records):,} bytes")
    print("")
    for rec in records:
        print(f"{rec['bytes']:>12,} B  {rec['path']}")
        print(f"               flags={rec['module_flags']}  title={rec['title_id']}"
              f"  encryption={rec['encryption']}  compression={rec['compression']}")
    if errors:
        print("\nModules with header inspection errors:", file=sys.stderr)
        for error in errors:
            print("  " + error, file=sys.stderr)
    print("\nRead-only metadata. Do not publish original modules or decoded code.")
    return 0 if not errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
