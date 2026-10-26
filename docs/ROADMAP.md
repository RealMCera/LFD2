# Xbox 360 Left 4 Dead 2 reverse-engineering roadmap

> **Chrome target clarified (October 26, 2026):** The project goal is a genuine game port modeled technically on the BO1 Zombies browser effort, **not** an improved raycasting mini-game. See [WEB_PORT_PLAN.md](WEB_PORT_PLAN.md).
>
> The original game does **not** yet run in Chrome. The current HTML demo is unrelated placeholder technology.


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
- **13 synthetic tests passed** in the owner's latest run, including two PE/XEX comparison tests. Ghidra disassembly and source reconstruction have **NOT** begun.

### Module discovery update — 2026-10-23

The inventory identified **21 DLL-named Xbox XEX2 modules plus default.xex (22 total)**. Major potential code modules include:

- `left4dead2/bin/server_360.dll` — 7,774,208 bytes
- `left4dead2/bin/client_360.dll` — 6,823,936 bytes
- `bin/engine_360.dll` — 4,468,736 bytes
- `bin/shaderapidx9_360.dll` — 2,039,808 bytes
- `bin/GameUI_360.dll` — 1,417,216 bytes

Responsibilities based on file names are hypotheses, not verified disassembly. Detailed inventory and next commands: [MODULE_MAP.md](MODULE_MAP.md).

### Server gameplay module verified — 2026-10-23

The owner successfully ran xex2ool and the PE inspector on `left4dead2/bin/server_360.dll`:

- Module flag `0x00000009` (Title + DLL), normal encryption, basic compression.
- Decoded local basefile `research/local/server_360.basefile`: **7,798,784 bytes**, valid PE32, **PowerPC FP (0x01F2)**.
- XEX/PE load address: `0x89780000`, entry point: `0x89DED900`, matching across formats.
- PE entry RVA `0x66D900` is within the executable `.text` section.
- **7 sections**; `.text` contains **5,740,436 bytes** of executable instructions (about 5.47 MiB).
- Four imported libraries: xam.xex **1**, xboxkrnl.exe **49**, tier0_360.dll **49**, vstdlib_360.dll **9** (108 import entries total).
- XEX image size `0x830000`; PE SizeOfImage `0x850200`. These fields differ; do not assume they are identical.
- **Follow-up verification:** the two explicit server address checks returned **MATCH** for base `0x89780000` and entry `0x89DED900`; **13 of 13 unit tests passed**.
- This is executable extraction/metadata verification, **not a source decompilation**.

See [module map](MODULE_MAP.md) for the full PE section report and server-specific address-check command.

### Important scope check

The `default.xex` launcher has only about **32 KiB** of code, but the newly verified **server_360.dll has 5.74 MB of code**. This confirms the launcher alone was not a sensible whole-game target. The other 20 DLL-named XEX2 modules still need separate analysis; successful decoding of the server module does not imply the game has been fully decompiled.

## Milestones

- [x] Extract ZArchive and locate XEX2 executable.
- [x] Determine XEX encryption and compression.
- [x] Run xex2ool `info`, `imports`, `basefile`.
- [x] Verify PE32 machine, sections, image base, and entry point.
- [x] Add lightweight extracted-file inventory: `tools/summarize_extract.py`.
- [x] Inventory extracted files and locate the 21 DLL-named XEX2 modules.
- [x] Add `tools/catalog_modules.py` and synthetic tests for DLL/XEX detection.
- [x] Scan XEX security/header metadata across all 22 modules (all normal-encrypted, basic-compressed; Title ID 454108D4).
- [x] Decode the server_360.dll basefile locally and verify its PE code sections and entry point.
- [x] Replace hard-coded launcher address comparison with optional module-specific PE/XEX checks.
- [ ] Install **Ghidra 12.1.3** and **XEXLoaderWV 12.1.3** (matching versions).
- [ ] Import `left4dead2/bin/server_360.dll` with the Xbox-aware loader.
- [ ] Validate loader memory map, PowerPC function boundaries, and import tables.
- [ ] Identify server DLL entry function and gameplay-related function boundaries, then study dependencies.
- [x] Document a real C++ → WASM, local game-data, browser-graphics architecture.
- [x] Add a read-only BSP/.360.zip header-probing script and synthetic tests.
- [x] Inspect actual BSP/ZIP signatures: PSBV big-endian v20; asset packs begin PK ZIP headers.
- [x] Add a WebGL2 brush-geometry viewer, experimental private BSP converter, and synthetic tests.
- [x] Validate BSP-to-mesh converter against actual hotel map: big-endian v20, LZMA-wrapped lumps, HDR face lump 58, 27,374 brush triangles in a local 777,248-byte file.
- [x] Verify all 23 synthetic tests pass on the owner's PC.
- [x] Load and render the original hotel's 27,374-triangle geometry in Chrome; screenshot confirmed an untextured aerial view.
- [x] Build private Source entity spawn extraction and browser start-position controls (awaiting owner testing).
- [x] Confirm a real first-person hotel corridor appears in Chrome from `info_player_start` (screenshot, October 26).
- [x] Verify material mapping on owner's hotel BSP: 228 texdata, 3,392 texinfos, 189 unique referenced materials, zero unmapped faces.
- [x] Document the Python ZIP extra-field compatibility issue; build a safe custom central-directory parser and synthetic tests (awaiting owner validation on Xbox ZIP).
- [ ] Identify original material paths, console texture payload format, and valid Xbox archive directory structure.
- [ ] Add mesh UVs and material indices, convert original textures locally, then render them in WebGL2.
- [ ] Add displacements, props, collision, and navigation.
- [ ] Evaluate native portable reimplementation/recompiler feasibility and missing Xbox/Source engine services.
- [ ] Build a limited original-game C++ subsystem as WebAssembly, then integrate gameplay, audio, asset loading, controls, and networking.
- [ ] Assess scope of a complete buildable port; write independent research and tests.

See [Ghidra setup](GHIDRA_SETUP.md). No proprietary executable or decompiler output is checked into this public repo.

**Status: hotel BSP material names mapped; custom Xbox ZIP directory reader is next to verify. Original textures and actual L4D2 game code are not yet rendered/running in Chrome.**

### New full-disc ISO input (pending local verification)

- [x] Add a read-only XDVDFS/XGD disc-layout probe and safe xdvdfs extraction wrapper, with nine synthetic tests.
- [x] Add a private Ghidra pseudocode export helper with bounded function counts.
- [ ] Inspect the actual 7.84 GB ISO on Windows, extract to ignored game-iso-extracted/, and compare module inventories with the prior archive.
- [ ] Run Ghidra's Xbox loader on one verified ISO module and export sample functions to ignored research/local/ files.

See [ISO_DECOMPILATION.md](ISO_DECOMPILATION.md). Neither a complete decompilation nor a playable browser port is done.
