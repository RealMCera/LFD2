# Xbox 360 Left 4 Dead 2 reverse-engineering roadmap

## Verified local results — 2026-10-23

The following results were reported by the project owner's Windows tools:

- Source ZArchive: **3,809,468,161 bytes**; **96 files**, extraction completed successfully.
- Original `default.xex`: **757,760 bytes**, Xbox 360 **XEX2**, encryption **normal**, compression **basic**.
- Title ID `454108D4`, Media ID `0E79403B`, version 0.0.0.3.
- XEX load address `0x82000000`, entry `0x82010CB8`, reported image size `0xC0000`.
- Imports: `xam.xex` **7**, `xboxkrnl.exe` **43**.
- xex2ool extracted `research/local/default.basefile`: **786,432 bytes**, starts with `MZ`.
- PE inspector recognized **PE32**, machine `0x01F2` (**PowerPC FP**), **6 sections**.
- PE image base `0x82000000`, entry RVA `0x10CB8` => virtual entry `0x82010CB8`. **Matches XEX entry**.
- PE SizeOfImage `0x40200`, **different from** XEX image-size field `0xC0000`. This may reflect Xbox-specific packaging/mapping; do not assume equivalence.
- PE sections (virtual bytes): `.rdata` 8,100; `.pdata` 952; `.text` **32,872**; `.data` 4,184; `.idata` 326; `.XBLD` 48.
- **9 synthetic tests passed**. Ghidra disassembly and source reconstruction have **NOT** begun.

### Module discovery update — 2026-10-23

The inventory identified **21 DLL-named Xbox XEX2 modules plus default.xex (22 total)**. Major potential code modules include:

- `left4dead2/bin/server_360.dll` — 7,774,208 bytes
- `left4dead2/bin/client_360.dll` — 6,823,936 bytes
- `bin/engine_360.dll` — 4,468,736 bytes
- `bin/shaderapidx9_360.dll` — 2,039,808 bytes
- `bin/GameUI_360.dll` — 1,417,216 bytes

Responsibilities based on file names are hypotheses, not verified disassembly. Detailed inventory and next commands: [MODULE_MAP.md](MODULE_MAP.md).

### Important scope check

The `.text` section in this XEX is only about **32 KiB**. That is small for an entire commercial game engine, so do not assume `default.xex` contains all of Left 4 Dead 2's game code. It could be a small launcher/bootstrap component, or the game code could be packaged differently. The current evidence alone does not establish why. Before claiming a whole-game decompilation, inventory the other **95** extracted files and identify other code-bearing containers.

## Milestones

- [x] Extract ZArchive and locate XEX2 executable.
- [x] Determine XEX encryption and compression.
- [x] Run xex2ool `info`, `imports`, `basefile`.
- [x] Verify PE32 machine, sections, image base, and entry point.
- [x] Add lightweight extracted-file inventory: `tools/summarize_extract.py`.
- [x] Inventory extracted files and locate the 21 DLL-named XEX2 modules.
- [x] Add `tools/catalog_modules.py` and synthetic tests for DLL/XEX detection.
- [ ] Scan XEX security/header metadata across all executable modules.
- [ ] Decode the server_360.dll basefile locally and verify its PE code sections.
- [ ] Install **Ghidra 12.1.3** and **XEXLoaderWV 12.1.3** (matching versions).
- [ ] Import `default.xex` with the Xbox-aware loader.
- [ ] Validate loader memory map, PowerPC function boundaries, and import tables.
- [ ] Record first entry function and discover whether this XEX invokes other modules.
- [ ] Assess scope of a possible buildable decompilation; write independent research and tests.

See [Ghidra setup](GHIDRA_SETUP.md). No proprietary executable or decompiler output is checked into this public repo.

**Status: launcher PE metadata verified and actual gameplay/engine modules located; function-level code analysis pending.**
