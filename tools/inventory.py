#!/usr/bin/env python3
"""Make a local file listing with sizes and SHA-256 for extracted files."""
import argparse
import hashlib
import json
from pathlib import Path

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--out", type=Path, default=Path("research/inventory.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"Not a directory: {root}")
    entries = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            entries.append({"path": path.relative_to(root).as_posix(),
                            "size": path.stat().st_size,
                            "sha256": sha256_file(path)})
            print(entries[-1]["path"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"file_count": len(entries), "files": entries}, indent=2), encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {args.out}")

if __name__ == "__main__":
    main()
