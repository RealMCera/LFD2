# Left 4 Dead 2 — Xbox 360 reverse-engineering workspace

**Status: ZArchive extracted, XEX2 identity verified, base-file encryption/compression identified. This is NOT a finished decompilation or playable build.**

This public repo holds tools and independently written research notes—not copyrighted game binaries, extracted assets, decryption keys, or recovered source dumps.

## Verified October 23, 2026

- **96 files** extracted from a 3.81 GB ZArchive; `game-extracted/default.xex` located.
- `default.xex` is an Xbox 360 **XEX2**, size **757,760 bytes**.
- Title ID **`454108D4`**, Media ID **`0E79403B`**, 16 optional headers.
- Base-file descriptor: encryption **normal (1)**, compression **basic (1)**.
- All five synthetic XEX inspector tests passed.
- **Not yet decrypted or decompiled.**

## Next step on Windows

Download the Windows `xex2ool.exe` from [landaire/acceleration releases](https://github.com/landaire/acceleration/releases), and put it in `tools/bin/` (ignored by Git).

Then open PowerShell in `C:\Users\FrontDesk\LFD2` and run:

```powershell
git pull
py tools\prepare_xex.py
```

It will print metadata and import information locally without modifying `default.xex`. Once that succeeds, the optional `py tools\prepare_xex.py --extract` creates an ignored, local basefile for further analysis.

See [full XEX workflow](docs/XEX_ANALYSIS.md), [roadmap](docs/ROADMAP.md), and [extraction guide](docs/EXTRACTION.md).

## Local tools

- `tools/extract_local.py`: reads/extracts a local ZArchive via xVerter.
- `tools/inspect_xex.py`: inspects XEX2 execution, encryption, and compression headers.
- `tools/prepare_xex.py`: calls third-party xex2ool for local info/imports and optional basefile extraction.
- `tools/inventory.py`: optional SHA-256 inventory of extracted files.

Tests (synthetic data only):

```powershell
py -m unittest discover -s tests -v
```

**Never commit original XEX files, decrypted basefiles, game assets, decompiler dumps, or keys to this repository.**
