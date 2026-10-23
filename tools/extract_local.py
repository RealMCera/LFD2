#!/usr/bin/env python3
"""Inspect and locally extract an Xbox ZArchive using xVerter.

Requires a locally downloaded archive and an installed xverter CLI.
No original game files are uploaded to GitHub by this script.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def find_xverter() -> str | None:
    """Locate the xverter CLI, including Python's Windows Scripts folder."""
    command = shutil.which("xverter")
    if command:
        return command
    scripts = Path(sysconfig.get_path("scripts"))
    for name in ("xverter.exe", "xverter"):
        candidate = scripts / name
        if candidate.is_file():
            return str(candidate)
    return None


def run_command(args: list[str]) -> None:
    print("\n> " + subprocess.list2cmdline(args), flush=True)
    subprocess.run(args, check=True)


def describe_archive(path: Path) -> None:
    with path.open("rb") as handle:
        header = handle.read(32)
    print(f"Archive: {path}")
    print(f"Size: {path.stat().st_size:,} bytes")
    print(f"First 32 bytes (hex): {header.hex(' ')}")
    print("Note: the file extension alone does not prove its format.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", nargs="?", help="Path to your local .zar file")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "game-extracted",
        help="Local extraction directory (default: game-extracted)",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="Also run xverter verify (reads the full archive)",
    )
    parser.add_argument(
        "--inventory", action="store_true",
        help="Hash all extracted files locally; can take additional time",
    )
    parser.add_argument(
        "--info-only", action="store_true",
        help="Identify the archive without extracting it",
    )
    args = parser.parse_args()

    try:
        raw = args.archive or input("Full path to your downloaded .zar file: ").strip().strip('"')
        archive = Path(raw).expanduser().resolve()
        if not archive.is_file():
            print(f"Archive not found: {archive}", file=sys.stderr)
            return 2
        describe_archive(archive)

        xverter = find_xverter()
        if not xverter:
            print(
                "xVerter is not installed or was not found.\n"
                "On Windows, run: py -m pip install --upgrade xverter\n"
                "Or get the standalone Windows release from:\n"
                "https://github.com/blank-query/xverter/releases",
                file=sys.stderr,
            )
            return 2

        run_command([xverter, "info", str(archive)])
        if args.verify:
            run_command([xverter, "verify", str(archive)])
        if args.info_only:
            print("\nInfo-only check complete. No game files were extracted.")
            return 0

        output = args.output.expanduser().resolve()
        if output.exists() and any(output.iterdir()):
            print(
                f"Extraction destination is not empty: {output}\n"
                "Use --output with an empty/new folder to avoid overwriting files.",
                file=sys.stderr,
            )
            return 2

        output.mkdir(parents=True, exist_ok=True)
        # The trailing forward slash tells xVerter to output an extracted directory.
        out_arg = output.as_posix().rstrip("/") + "/"
        run_command([xverter, "convert", str(archive), "-o", out_arg])

        xex_files = sorted(
            p for p in output.rglob("*")
            if p.is_file() and p.suffix.lower() == ".xex"
        )
        print(f"\nExtraction directory: {output}")
        print(f"Xbox 360 XEX files found: {len(xex_files)}")
        for p in xex_files[:20]:
            print("  " + p.relative_to(output).as_posix())
        if not xex_files:
            print("No XEX files detected. Review the xVerter output before continuing.")

        if args.inventory:
            inventory = REPO_ROOT / "research" / "inventory.json"
            run_command([
                sys.executable, str(REPO_ROOT / "tools" / "inventory.py"),
                str(output), "--out", str(inventory),
            ])
            print(f"Local inventory written to: {inventory}")

        print("\nDo not commit or upload the extracted game files or executable.")
        print("Share only the console messages and non-proprietary metadata for next steps.")
        return 0
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"\nFailed: {exc}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
