# Left 4 Dead 2 — Xbox 360 reverse-engineering workspace

**Current status: Xbox 360 XEX decoded into a local MZ basefile; PE structure and Ghidra import are next. This is NOT a complete decompilation or playable build.**

This public repo contains independent research tools, documentation, and synthetic tests. All proprietary data stays in local, Git-ignored directories.

## Verified Windows results — October 23, 2026

- Extracted **96 files** from a 3.81 GB ZArchive.
- Xbox 360 **XEX2** `game-extracted/default.xex`: **757,760 bytes**.
- Title ID `454108D4`, Media ID `0E79403B`.
- XEX encryption: **normal**; compression: **basic**.
- xex2ool **v0.4.0** reported the load address `0x82000000`, image size `0xC0000`, entry point `0x82010CB8`.
- Imported system libraries: **xam.xex (7)** and **xboxkrnl.exe (43)**.
- The `basefile` command wrote `research/local/default.basefile` (**786,432 bytes**) and the file begins with **MZ**.
- PE/COFF sections and architecture have **not yet been verified**. Game functions have **not been decompiled**.

## Next: validate the PE and install Ghidra

Open PowerShell inside `C:\Users\FrontDesk\LFD2`:

```powershell
git pull
py -m unittest discover -s tests -v
py tools\inspect_pe.py
```

The new `inspect_pe.py` reads only header and section metadata from the local basefile. It does not upload game code.

See the [step-by-step Ghidra setup guide](docs/GHIDRA_SETUP.md) for **Ghidra 12.1.3** paired with **XEXLoaderWV 12.1.3** (version-matched). The Xbox-specific loader is designed to import the original `default.xex` so imports and memory mapping can be handled correctly.

## Local tooling

- `tools/extract_local.py` — local ZArchive identification/extraction with xVerter.
- `tools/inspect_xex.py` — XEX2 metadata inspection.
- `tools/install_xex2ool.ps1` — install upstream xex2ool (Windows).
- `tools/prepare_xex.py` — query xex2ool and optionally extract an ignored local basefile.
- `tools/inspect_pe.py` — new header-only PE inspector.
- `tools/inventory.py` — optional SHA-256 file manifest of extracted data.

Research history and milestones: [ROADMAP](docs/ROADMAP.md).

**Do not upload the original XEX, decrypted basefile, extracted game assets, or copies of proprietary decompiler output to this public repository.**
