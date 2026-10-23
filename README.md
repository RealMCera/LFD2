# Left 4 Dead 2 — Xbox 360 reverse-engineering workspace

**Status: local executable decoded and PE headers verified. No code has yet been decompiled and no playable build exists.**

This repository contains original research utilities, documentation, and synthetic tests. Xbox binaries, extracted assets, keys, decoded basefiles, and Ghidra project files stay on your Windows PC.

## Verified facts — 2026-10-23

- Extracted a ZArchive of **96 files**.
- `default.xex`: **757,760 bytes**, XEX2, encryption **normal**, compression **basic**.
- Title ID `454108D4`, Media ID `0E79403B`.
- Loaded at `0x82000000`, with entry point `0x82010CB8` and imports from `xam.xex` (7) and `xboxkrnl.exe` (43).
- xex2ool produced local `research/local/default.basefile`: **786,432 bytes**.
- PE inspector verified **PE32, PowerPC FP (`0x01F2`), 6 sections**, and an entry-point address matching the XEX.
- PE `.text` virtual size is **32,872 bytes**. This is small for a full game executable, so the remaining extracted contents need inventory before assuming this file contains the full game code.
- All **9** synthetic unit tests passed.

## Next command on Windows

From the LFD2 checkout:

```powershell
git pull
py tools\summarize_extract.py
```

The new tool quickly reports extension totals, the largest extracted files, and likely executable-container signatures. It reads only the first four bytes of each extracted file and does not upload contents.

## Next stage: Ghidra

For the compatible **Ghidra 12.1.3** + **XEXLoaderWV 12.1.3** installation and `default.xex` import, follow [GHIDRA_SETUP.md](docs/GHIDRA_SETUP.md). Install JDK 21, use the official compiled Ghidra ZIP and matching XEXLoaderWV extension ZIP, and create a non-shared project outside this repo.

## Local utilities

- `tools/extract_local.py` — ZArchive extraction via xVerter
- `tools/inspect_xex.py` — XEX metadata
- `tools/install_xex2ool.ps1` — xex2ool Windows installer
- `tools/prepare_xex.py` — xex2ool info/import/basefile
- `tools/inspect_pe.py` — PE/COFF structure and sections
- `tools/summarize_extract.py` — extracted-file overview and possible executable modules
- `tools/inventory.py` — optional full SHA-256 inventory

Full verification details: [ROADMAP](docs/ROADMAP.md).

**Do not commit original executable or game data, decrypted basefiles, or proprietary disassembler outputs to this public GitHub repository.**
