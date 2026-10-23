# Left 4 Dead 2 — Xbox 360 reverse-engineering workspace

**Status: server game-module executable decoded and PE verified; Ghidra disassembly/decompilation is next. No playable build or recovered C++ source exists.**

This repository contains original research utilities, documentation, and synthetic tests. Xbox binaries, extracted assets, keys, decoded basefiles, and Ghidra project files stay on your Windows PC.

## Verified facts — 2026-10-23

- Extracted a ZArchive of **96 files**.
- `default.xex`: **757,760 bytes**, XEX2, encryption **normal**, compression **basic**.
- Title ID `454108D4`, Media ID `0E79403B`.
- Loaded at `0x82000000`, with entry point `0x82010CB8` and imports from `xam.xex` (7) and `xboxkrnl.exe` (43).
- xex2ool produced local `research/local/default.basefile`: **786,432 bytes**.
- PE inspector verified **PE32, PowerPC FP (`0x01F2`), 6 sections**, and an entry-point address matching the XEX.
- The launcher PE `.text` is only **32,872 bytes**, but the project found **21 additional XEX2 DLL modules**. The gameplay-oriented `server_360.dll` was successfully decoded locally: **PE32, PowerPC FP, 7 sections, 5,740,436 bytes of .text code**. Its XEX/PE entry is **`0x89DED900`**, base **`0x89780000`**. Other DLL code sections remain to be examined.
- All **11** synthetic unit tests passed in the latest owner's report, before two newly added address-comparison tests.

## Next command on Windows

From the LFD2 checkout:

```powershell
git pull
py -m unittest discover -s tests -v
py tools\inspect_pe.py "research\local\server_360.basefile" --expected-xex-base 0x89780000 --expected-xex-entry 0x89DED900
```

The decoded server basefile is already available; **do not rerun extraction**. These commands validate the module-specific address comparison and run the additional synthetic tests. Next, follow [GHIDRA_SETUP.md](docs/GHIDRA_SETUP.md) to import the original Xbox 360 `server_360.dll` using XEXLoaderWV.

## Next stage: Ghidra

For the compatible **Ghidra 12.1.3** + **XEXLoaderWV 12.1.3** installation and `server_360.dll` import, follow [GHIDRA_SETUP.md](docs/GHIDRA_SETUP.md). Install JDK 21, use the official compiled Ghidra ZIP and matching XEXLoaderWV extension ZIP, and create a non-shared project outside this repo.

## Local utilities

- `tools/extract_local.py` — ZArchive extraction via xVerter
- `tools/inspect_xex.py` — XEX metadata
- `tools/install_xex2ool.ps1` — xex2ool Windows installer
- `tools/prepare_xex.py` — xex2ool info/import/basefile
- `tools/inspect_pe.py` — PE/COFF structure and sections
- `tools/summarize_extract.py` — extracted-file overview and possible executable modules
- `tools/catalog_modules.py` — enumerate Xbox 360 modules and security metadata (including .dll files)
- `tools/inventory.py` — optional full SHA-256 inventory

Full verification details: [ROADMAP](docs/ROADMAP.md) and [MODULE_MAP](docs/MODULE_MAP.md).

**Do not commit original executable or game data, decrypted basefiles, or proprietary disassembler outputs to this public GitHub repository.**
