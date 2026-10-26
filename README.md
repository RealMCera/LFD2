# Left 4 Dead 2 — Xbox 360 reverse-engineering workspace

**Status: Xbox 360 server executable decoded and PE verified, but not decompiled. A separate original browser survival demo is playable from docs/index.html; no original L4D2 port exists.**

This repository contains original research utilities, documentation, and synthetic tests. Xbox binaries, extracted assets, keys, decoded basefiles, and Ghidra project files stay on your Windows PC.

## Verified facts — 2026-10-23

- Extracted a ZArchive of **96 files**.
- `default.xex`: **757,760 bytes**, XEX2, encryption **normal**, compression **basic**.
- Title ID `454108D4`, Media ID `0E79403B`.
- Loaded at `0x82000000`, with entry point `0x82010CB8` and imports from `xam.xex` (7) and `xboxkrnl.exe` (43).
- xex2ool produced local `research/local/default.basefile`: **786,432 bytes**.
- PE inspector verified **PE32, PowerPC FP (`0x01F2`), 6 sections**, and an entry-point address matching the XEX.
- The launcher PE `.text` is only **32,872 bytes**, but the project found **21 additional XEX2 DLL modules**. The gameplay-oriented `server_360.dll` was successfully decoded locally: **PE32, PowerPC FP, 7 sections, 5,740,436 bytes of .text code**. Its XEX/PE entry is **`0x89DED900`**, base **`0x89780000`**. Other DLL code sections remain to be examined.
- All **13** synthetic unit tests passed; the server XEX/PE load address and entry-point comparisons both returned **MATCH**.

## Play the Chrome browser prototype

**New:** [After the Siren — playable first-person zombie survival demo](docs/index.html). This is a separate, original browser proof of concept. It is **not** an emulation or port of the commercial Left 4 Dead 2 game, and it does not bundle game assets.

To play directly in Chrome on Windows:

    cd C:\Users\FrontDesk\LFD2
    git pull
    & "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" (Resolve-Path ".\docs\index.html").Path

The one-file demo includes WASD movement, mouse-look, shooting, AI teammates, pickups and five waves. To make it playable at a shareable web address, see [Chrome play and GitHub Pages setup](docs/PLAY.md) (choose branch main and /docs in GitHub Settings → Pages).

## Next step: import server_360.dll in Ghidra

**The 13 tests and both server address comparisons have passed. No more extraction is required.**

Install **64-bit JDK 21**, **Ghidra 12.1.3**, and the matching **XEXLoaderWV 12.1.3** release extension. Follow the [Ghidra setup guide](docs/GHIDRA_SETUP.md).

In a non-shared Ghidra project outside the repo, import the **original XEX2 container** at `game-extracted/left4dead2/bin/server_360.dll`, not `research/local/server_360.basefile`. Confirm the loader's image base `0x89780000` and entry `0x89DED900`, run auto-analysis, then view the entry point in the decompiler.

If the Xbox loader is missing or an import fails, capture Ghidra's exact message. Keep all executable contents and the Ghidra project local.

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
