# Xbox 360 Left 4 Dead 2 reverse-engineering roadmap

> **Chrome target clarified (October 26, 2026):** The project goal is a genuine game port modeled technically on the BO1 Zombies browser effort, **not** an improved raycasting mini-game. See [WEB_PORT_PLAN.md](WEB_PORT_PLAN.md).
>
> The original game does **not** yet run in Chrome. The current HTML demo is unrelated placeholder technology.


## October 26 milestone: hotel visual pipeline complete

- Original first-person hotel brush geometry: **27,374 triangles**
- Authenticated Xbox VTFX materials automatically resolved and rendered: **53**
- Textured brush geometry: **20,198 triangles (73.8%)**
- Untextured triangles: **7,176**; not necessarily drawable wall textures
- Multi-image folder loader successful, **0 unavailable**
- Next phase: inventory of Source game-lump static props, dynamic model entities, doors, displacement data (not yet rendered)

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
- [x] Document Python ZIP extra-field rejection and try a safe custom central-directory reader.
- [x] Diagnose Xbox ZIP directory: first central record valid; next candidate +58 bytes beyond predicted offset.
- [x] Implement bounded 128-byte recovery for unexpected central-directory gaps and synthetic 3/58-byte tests (awaiting run on owner's archive).
- [x] Confirm 51/51 synthetic tests passed. Bounded sequential ZIP parser reaches record 1,470 before directory exhaustion.
- [x] Add independent EOCD-bounded central signature scanner and synthetic tests; waiting for real archive report.
- [x] Confirm 55/55 unit tests and independent scan of zip0: all 24,435/24,435 central-header candidates structurally plausible; no .vmt filenames reported.
- [x] Correct erroneous 58-byte alignment hypothesis: old sequential parser was skipping valid central headers due unusual extra-length values.
- [x] Add multi-pack and embedded BSP PAKFILE directory scanner with synthetic tests (awaiting local results).
- [x] Confirm all 59 synthetic tests passed; find 4,640 VMT / 3,922 VTF file candidates in zip1.360.zip and 217 VMT / 85 VTF in hotel embedded PAK.
- [x] Match reported 69 hotel material IDs (10,315 face references) from zip1 and 120 IDs (525 faces) from embedded map PAK; totals suggest complete filename coverage.
- [x] Add exact union/overlap report and bounded ZIP local-header/VTFX magic probe with synthetic tests; actual owner results pending.
- [x] Confirm 66/66 tests; 189/189 unique material IDs and 10,840/10,840 face references covered with zero cross-pack duplicates.
- [x] Verify 10 local ZIP texture headers and Xbox VTFX signatures from zip1 and BSP PAK.
- [x] Add bounded VTFX metadata parser and opt-in single-file local extraction tool, synthetic tests and converter docs (awaiting owner validation).
- [x] Confirm 73/73 synthetic tests pass; extract original 512×512 DXT1 plaster_int_14 VTFX (174,844 bytes) locally.
- [x] Add separately installed VTFX Reader → PNG wrapper with local-only output validation and synthetic tests (awaiting owner use).
- [x] Add Source BSP UV/material-ID mesh enrichment and synthetic tests (awaiting owner use and WebGL rendering).
- [x] Owner confirmed 82/82 tests, UV-enriched 27,374-triangle hotel private mesh with 187 rendered material IDs and 82,122 UV pairs.
- [x] Add opt-in local PNG + material ID textured overlay to existing Chrome WebGL2 viewer (syntax and mock-data-flow checks pass; real Chrome validation pending).
- [x] Convert the first private 512×512 Xbox plaster VTFX to PNG; screenshot confirms original material on 1,404 triangles in Chrome.
- [x] Owner-verified complete Source UV-enriched private mesh and WebGL one-material overlay.
- [ ] Locate original Xbox material/texture files, especially in zip1.360.zip, and validate any actual texture decoder.
- [ ] Verify complete console ZIP directory parsing, original VMT material-file matches, and console texture format.
- [x] Correct Windows 8.3 short-path vs resolved long-path ISO unit-test expectation (re-run tests pending).
- [ ] Identify original material paths, console texture payload format, and valid Xbox archive directory structure.
- [x] Add optional multi-PNG WebGL overlay, safe non-ambiguous basename matching and opt-in local 8-material conversion, with synthetic tests; await owner results.
- [ ] Add displacements, props, collision, and navigation.
- [ ] Evaluate native portable reimplementation/recompiler feasibility and missing Xbox/Source engine services.
- [ ] Build a limited original-game C++ subsystem as WebAssembly, then integrate gameplay, audio, asset loading, controls, and networking.
- [ ] Assess scope of a complete buildable port; write independent research and tests.

- [x] Screenshot confirms original first-person hotel multi-material rendering: 8 PNGs, 11,872 textured triangles, 0 skipped.
- [x] Add read-only crosshair BSP material raycast inspector and UI shortcut I (synthetic mock-ray test passed; owner floor identification pending).
- [x] Add --focus floor and --material exact selection to opt-in local Xbox texture conversion with synthetic tests (owner run pending).
- [ ] Identify actual gray floor material using inspector; convert matching real texture, or investigate VMT basetexture/tool-material dependency.

- [x] Owner screenshot: 14 original material PNGs active on 13,696 of 27,374 original hotel brush triangles (50.0%) including floor.
- [x] Add live missing-material coverage panel, tool/debug categorization, and 48 total textures under 24M-pixel budget (owner validation pending).
- [x] Add popularity-offset `--start` to safe local converter, filename collision protection, and synthetic tests (owner validation pending).
- [ ] Diagnose high-count untextured tool/sky/brush materials versus missing prop/displacement geometry.

- [x] Build one-command original VMT `$basetexture` resolver and local-only PNG conversion against zip1 + embedded BSP Pak (owner run pending).
- [x] Add one-folder Chrome manifest loader for all resolved original Source brush material PNGs; safe memory bounds and duplicate path handling (owner visual validation pending).
- [x] Add optional toggle for hiding original TOOLS/DEV/SKY/EFFECTS brushes from gray base pass without modifying mesh.
- [x] Add Python/Node synthetic tests and GitHub Actions workflow.
- [x] Owner screenshot confirms final folder loader displays **53 original materials on 20,198/27,374 triangles (73.8%)**, zero unavailable in the loader.
- [x] Close automated original brush + material phase at supported-material coverage; nonvisual and unsupported surfaces are tracked separately.
- [x] Add bounded read-only original hotel BSP entity and static-prop game-lump inspector with synthetic tests (owner first inventory pending).
- [ ] Begin distinct phase: Source displacements, props, doors, lightmaps, then collision and actual engine/gameplay.

- [x] Owner verified 112/112 Python tests and inspected 1,894 entities in real c1m1_hotel.360.bsp (314 physics props, 72 dynamic props, 30 rotating doors).
- [x] Confirm original game lump `sprp` v9 with compression flag 1 and uncompressed length 156,212 bytes; 928B/3,740B displacement metadata.
- [x] Add bounded Valve LZMA compressed game lump dictionary probe and synthetic compression tests (owner validation pending).
- [x] Add original `.mdl`/`.vvd`/`.vtx` directory cross-check, up-to-16-byte model signature probe, and optional private entity placement JSON (owner validation pending).
- [x] Owner verified 120 passing tests, original compressed sprp v9 dictionary with 188 entries and 1,748 records with apparent 72-byte stride; entity placement manifest has 416 authored objects.
- [x] Add complete Source v9/72-byte static placement decoder with per-record validation and all-Xbox-pack + loose files + BSP Pak model discovery (synthetic tests committed, owner run pending).
- [ ] Confirm 1,748 static v9 placements against the real Xbox file with the new full-record validation and export private combined 2,164-placement manifest.
- [x] Owner's actual PC: 127 tests passed, decoded all 1,748 static 72-byte v9 records and 416 entity model placements; private hotel-all-props.json created.
- [x] Confirm 228/228 referenced MDL filenames across ten asset sources with zero package scan errors; zip0 includes 3,211 MDL, 3,182 VVD, 3,182 VTX, 2,383 PHY.
- [x] Add read-only exact suffix + nearby companion path diagnostics for models that failed current conventional match (owner output pending).
- [x] Owner-confirmed: 128/128 synthetic tests passed; real Xbox model files use the `.dx90.360.vtx` index suffix and optional `.360.phy`; zero matches was a matcher bug.
- [x] Fix exact Xbox model filename triplet detection, with synthetic hotel-chair test; commit private-only first chair MDL/VVD/VTX header/checksum probe plus explicit one-model extraction mode (owner validation pending).
- [x] User's original Xbox chair model trio extracted privately: compressed LZMA-wrapped `.360.mdl` (482 bytes), big-endian version 4 VVD (21,717 bytes), version 7 VTX (3,876 bytes). VVD/VTX checksum `f3737e00` matches.
- [x] Add bounded local Valve LZMA MDL decode, Source studiohdr bodypart/material counts, three-way checksum validation and opt-in ignored decoded-model output (new tests committed; owner validation pending).
- [ ] Validate decompressed MDL checksum against the known `f3737e00` companion checksum on user's actual Xbox chair; then implement vertex and triangle-strip decoding and actual chair rendering.
- [ ] Read original hotel's MDL/VVD/VTX binary versions, checksum consistency and Xbox endianness, then implement real chair geometry conversion and rendering.
- [ ] Locate and decode original .mdl/.vvd/.vtx triplet files before rendering genuine furniture and doors in Chrome.

See [Ghidra setup](GHIDRA_SETUP.md). No proprietary executable or decompiler output is checked into this public repo.

**Status (October 27, 2026): Hotel brush/textures phase screenshot-confirmed. Phase 2 has 2,164 verified original placements and 228/228 MDL definitions; owner confirmed 128 tests and resolved the real Xbox model companion naming `.dx90.360.vtx` / `.360.phy`. Matching code corrected and first chair MDL/VVD/VTX header probe committed, awaiting owner validation. No original prop meshes or L4D2 gameplay render in Chrome yet.**

### Full-disc ISO input (extraction confirmed; code analysis pending)

- [x] Add a read-only XDVDFS/XGD disc-layout probe and safe xdvdfs extraction wrapper, with nine synthetic tests.
- [x] Add a private Ghidra pseudocode export helper with bounded function counts.
- [x] Inspect actual 7.84 GB ISO as XGD2/XDVDFS; xdvdfs extraction completed with default.xex, 21 DLL-named candidate modules, 24 BSP maps and eight .360.zip packages.
- [x] Add read-only SHA-256 XEX2 comparison against the previous archive extraction, with nine synthetic tests.
- [ ] Run both module catalogs and byte-identity comparison on Windows to verify XEX2 modules and detect build differences.
- [ ] Run Ghidra's Xbox loader on one verified ISO module and export sample functions to ignored research/local/ files.

See [ISO_DECOMPILATION.md](ISO_DECOMPILATION.md). Neither a complete decompilation nor a playable browser port is done.
