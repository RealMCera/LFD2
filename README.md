# Left 4 Dead 2 Xbox 360 → Chrome port research

**Target: a genuine Left 4 Dead 2 browser port using original game behavior and the user's locally owned game files, closer in architecture to the BO1 Zombies browser project at vel.gg/bsz. This does NOT run in Chrome yet.**

The archived [After the Siren demo](docs/legacy-demo.html) is a **separate, basic JavaScript raycasting experiment**. It is NOT the original game, does not use Source, and is **not the target implementation**. We will stop treating improvements to the demo's graphics as progress toward running actual L4D2.

## The browser-port architecture

The BO1 Zombies project runs native C++ game-engine code recompiled into WebAssembly with custom web graphics, sound and game-data systems. See the [technical description of bo1z-client](https://github.com/jplot/bo1z-client).

Our equivalent would require:
1. Validating the Xbox 360 Source engine maps, model and asset formats.
2. Rendering **locally supplied original maps** using WebGL2/WebGPU.
3. Recovering or recreating the portable C++ functionality of the L4D2 client, server, engine and dependencies.
4. Compiling functioning portable code to WebAssembly through Emscripten and implementing the browser-facing system services.
5. Keeping proprietary game data local, not bundling it into this public repository.

The Xbox 360 **PowerPC XEX2** binaries cannot themselves be compiled by Emscripten, and Ghidra decompiler output is not automatically buildable source.

**Full porting strategy and completion gates: [WEB_PORT_PLAN.md](docs/WEB_PORT_PLAN.md).**

## Full Xbox 360 ISO: local extraction and private decompilation

The full-disc ISO is **7.84 GB** and has been identified by **Drive metadata only**. Follow [ISO_DECOMPILATION.md](docs/ISO_DECOMPILATION.md): use `tools/import_disc_iso.py` to inspect the local XDVDFS image and optionally unpack with the external xdvdfs CLI; `tools/ghidra/ExportPseudocode.py` can export a limited set of analyzed functions **privately**, never into this public repo. The disc contents and actual decompilation remain unverified.

## First Chrome preview: original L4D2 BSP geometry (experimental)

**New tools:** [local BSP-to-mesh converter](tools/bsp_to_browser_mesh.py), [HDR/compression lump diagnostics](tools/inspect_bsp_lumps.py), and the [WebGL2 local map viewer](docs/map-viewer.html). **The owner has converted the original Xbox hotel map successfully:** 27,374 triangles from 10,840 Source faces, and WebGL2 display is now screenshot-confirmed (untextured, distant overview). The converter is designed to fail with an explanation if another map variant needs further decoding.

From Windows PowerShell:

    cd C:\Users\FrontDesk\LFD2
    git pull
    py -m unittest discover -s tests -v
    py tools\inspect_bsp_lumps.py

The hotel mesh **already exists** locally. Do not re-run conversion unless intentionally using a different output filename. Open the local viewer:

    Start-Process (Resolve-Path ".\docs\map-viewer.html").Path

Choose **SELECT A LOCAL .MESH.JSON FILE** and select the existing private output: research\local\c1m1_hotel.mesh.json. The entire process stays local. **No actual Left 4 Dead 2 game runtime, AI, collision or Source engine is running in Chrome yet.**

Full local setup: [MAP_VIEWER.md](docs/MAP_VIEWER.md).

## Completed original-game research

- Local `.zar` unpack: **96 files**, including **22 Xbox 360 XEX2 modules**, **24 BSP maps**, and **8 .360.zip packages**.
- Extracted and inspected XEX2 loader and gameplay-related server module.
- `left4dead2/bin/server_360.dll` local decoded PE32/PowerPC image: **5,740,436 bytes of .text**, base `0x89780000`, entry `0x89DED900`.
- Verified original XEX/PE memory addresses and **32 synthetic tests** in the owner's latest report (before new Xbox ZIP tests).
- **Successfully converted the original Dead Center hotel BSP to a local 777,248-byte JSON mesh** (27,374 triangles, HDR lump 58, 43 displacement surfaces skipped). The owner's screenshots confirm both an aerial view and a recognizable first-person hotel corridor rendered in Chrome. No engine source recovered; actual L4D2 is not playable in Chrome.

## Improve the real map viewpoint — player/survivor start

The owner's screenshot **confirmed successful Chrome/WebGL2 rendering of the 27,374-triangle hotel brush mesh**. The giant gray faces were viewed from the automated camera high above the whole level, not from a character's position.

A **new** local helper reads the *original BSP entity lump* and adds survivor/player start locations to a **new private mesh file**, preserving the original successful output:

    cd C:\Users\FrontDesk\LFD2
    git pull
    py -m unittest discover -s tests -v
    py tools\add_bsp_spawns.py

Private output: research\local\c1m1_hotel_spawns.mesh.json

Open docs/map-viewer.html in Chrome (refresh an already-open tab). Select the **new** mesh. The updated viewer starts near a player/survivor start when one is available and adds **1: START POSITION**, **2: OVERVIEW**, **N: NEXT START**, a dropdown, and a close button for the loader. Only local browser memory is used.

This is still a **geometry inspection tool, not a game**: the brush faces lack textures, static props, collision, lighting and gameplay. The survivor/player start locations are camera guides only; the owner's latest screenshot confirmed an eye-level corridor view.


## Next milestone — locate the original Xbox texture files

**Confirmed on the owner's Windows PC:** 32 synthetic tests passed; the hotel BSP has **228 texture records**, **3,392 texinfos**, **189 referenced materials**, and **10,840 mapped faces**. Sample paths include `PLASTER/PLASTER_INT_14`, `TILE/TILE_CEILING_01`, and `CONCRETE/CONCRETE_FLOOR_10`.

The standard Python ZIP reader stopped on an unusually formatted internal extra field within the Xbox `zip0.360.zip` archive. That is not evidence of file corruption.

**New:** [tools/inspect_xbox_zip.py](tools/inspect_xbox_zip.py) reads the central directory without decoding these problematic extra fields. [tools/inspect_map_materials.py](tools/inspect_map_materials.py) now uses it as a fallback to compare `.vmt` archive names with the BSP's material references. The fallback is **not yet tested on the actual Xbox archive**.

In Windows PowerShell:

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\inspect_map_materials.py --pack
```

If the ZIP format requires additional Xbox-specific handling, capture the printed error and stop rather than trying to unpack the 1 GB archive. No game payloads are read, extracted or uploaded by the new inspector.

Read the [material pipeline](docs/MATERIAL_PIPELINE.md). The eventual Chrome texture renderer will require original mesh UV coordinates, local asset conversion and actual materials; the generic gray shader alone isn't enough.


## Latest Xbox ZIP investigation (October 26)

**46/47 of the owner's tests passed** before the fix to the Windows ISO path-test expectation. Material references remain confirmed: 189 distinct names, 10,840 mapped faces.

The new bounded ZIP parser finds the archive's first central record but fails at entry 1, so skipping malformed internal extra fields alone is not enough. We have NOT confirmed the cause or successfully listed this Xbox package yet.

The next command adds precise metadata-only central-directory alignment diagnostics. **Do not upload the game ZIP or attempt bulk extraction**:

    cd C:\Users\FrontDesk\LFD2
    git pull
    py -m unittest discover -s tests -v
    py tools\inspect_xbox_zip.py --diagnose

The report prints the EOCD offset/size, the first record's fixed lengths, the predicted second-record position, and any nearby alternative header offset. It does not read or print texture/game payloads. Share that diagnostic output to distinguish Xbox alignment/padding from an incorrectly interpreted directory header.

## Xbox ZIP central-directory recovery (October 26)

The latest header diagnostic confirmed that the Xbox archive's central-directory EOCD offset and size agree exactly, and its first central record parses. The predicted second header is all zeros, but the first plausible replacement starts **58 bytes later**.

I've updated the read-only ZIP directory reader to recover only a **small forward gap (up to 128 bytes)** between otherwise valid central records, tracking each gap rather than assuming the entire archive is aligned that way. Synthetic tests cover 3-byte and 58-byte gaps and rejection of larger unknown offsets. **This reader has not yet been verified against the full Xbox archive.**

Run:

    cd C:\Users\FrontDesk\LFD2
    git pull
    py -m unittest discover -s tests -v
    py tools\inspect_map_materials.py --pack

If parsing succeeds, report the recovered-entry count, gap totals, material extension counts and VMT matches. If it stops at a later record, report the exact error; no game payload is touched.

## New: independent Xbox ZIP central-directory scan

The latest Windows run passed **51/51 tests**. The safe sequential Xbox ZIP reader advanced to entry **1,470** before refusing a header near the end of the directory. However, the EOCD declares **24,435 records in 2,355,200 bytes** (~96 bytes/record), which is incompatible with trusting many oversized "extra length" values to step between records.

Instead of widening the 128-byte gap allowance, we've added [tools/scan_xbox_zip_directory.py](tools/scan_xbox_zip_directory.py). It scans only the **EOCD-bounded central directory** for PK central signatures, validates fixed header and filename bounds, and reports how many plausible candidates exist, including potential VMT/VTFX paths. It **never reads compressed game file data**. Synthetic tests are committed; the scanner is not yet verified on the owner's Xbox archive.

    cd C:\Users\FrontDesk\LFD2
    git pull
    py -m unittest discover -s tests -v
    py tools\scan_xbox_zip_directory.py

Share only the printed metadata report. Candidate filenames are a diagnostic, not proof of successful archive decoding.

## Confirmed: all 24,435 Xbox ZIP index entries and the real texture-pack lead

The owner's latest PowerShell run passed **55/55 tests**, and a read-only independent scan of \`left4dead2/zip0.360.zip\` found **24,435 plausible central-directory headers**, exactly matching its declared **24,435 entries**. No candidates were rejected. Its dominant extensions are audio and model types (\`.wav\`, \`.mdl\`, \`.vvd\`, \`.vtx\`, \`.phy\`); no apparent \`.vmt\` filenames were reported.

**Correction to earlier hypotheses:** the old "58-byte ZIP gap" was a consequence of interpreting unusual Xbox extra-length values as normal ZIP sizes and skipping valid records. It was not evidence of a real 58-byte gap. We should no longer build on that explanation. The actual compressed file contents and local offsets have not been validated.

Xbox L4D2 modding documentation specifically points to \`zip1.360.zip\` for console textures. We've added [tools/scan_source_asset_packs.py](tools/scan_source_asset_packs.py) and synthetic tests to inspect **all eight local Xbox archives**, optionally including the hotel's internal BSP PAKFILE ZIP. Only ZIP *directory metadata* is read. Its results are pending.

\`\`\`powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\scan_source_asset_packs.py --include-map-pak
\`\`\`

Full details: [Xbox pack discovery](docs/XBOX_PACK_DISCOVERY.md). This is still filename discovery, not texture extraction or a playable browser game.

## Texture files found — verify file offsets and VTFX headers

**Owner-confirmed (October 26):** All **59 Python tests passed**, and the all-pack scan found the original hotel textures/materials in the local Xbox archives.

- \`left4dead2/zip1.360.zip\`: **4,640 VMT** and **3,922 VTF** directory candidates, with **69 of 189 hotel material names** accounting for **10,315 of 10,840 face references**.
- \`c1m1_hotel.360.bsp\` embedded PAKFILE: **217 VMT** and **85 VTF** candidates, with **120 of 189 hotel material names** accounting for **525 face references**.
- The matched-name totals (69+120) and face-reference totals (10,315+525) exactly equal the source totals. **A new exact union/overlap report** now tests whether any matching IDs are duplicated or missing.
- These are directory filename matches. The actual ZIP member offsets, image signatures and texture decode support have **NOT** yet been verified.

**New read-only tool:** [tools/probe_xbox_texture_headers.py](tools/probe_xbox_texture_headers.py) checks a few top referenced \`.360.vtf\` samples from \`zip1\` and from the BSP's embedded PAKFILE. It reads only a 30-byte ZIP local header, a bounded filename and **up to 16 bytes of candidate texture magic** per sample. It never decompresses or exports the game textures. The extended multi-pack scanner prints precise union and overlap counts.

Run on the owner's Windows PC:

    cd C:\Users\FrontDesk\LFD2
    git pull
    py -m unittest discover -s tests -v
    py tools\scan_source_asset_packs.py --include-map-pak
    py tools\probe_xbox_texture_headers.py --include-map-pak

If the local file headers and VTFX magic are valid, the next engineering phase can implement local-only image conversion and UV/material rendering; until then, do not assume ordinary ZIP extraction works. Full report: [XBOX_PACK_DISCOVERY.md](docs/XBOX_PACK_DISCOVERY.md).

## First real Xbox texture → private VTFX file

**New verified owner results:** **66/66 synthetic tests passed**; the hotel has **189/189 material filename matches**, **10,840/10,840 face references**, and **zero duplicated or missing IDs**. The Xbox \`zip1.360.zip\` and the hotel map's embedded pak both have validated local ZIP file headers and the original Xbox **VTFX** texture signature.

We've added [tools/extract_single_vtfx.py](tools/extract_single_vtfx.py) and synthetic tests. It inspects the **Xbox VTFX big-endian header** (dimensions, format, mip/resource metadata) for one original hotel-wall texture. It can optionally copy only that validated, uncompressed ZIP member to ignored \`research/local/vtfx/\` — **no bulk extraction, no image decoding, no upload**. New tests need to be run on the owner's Windows PC.

    cd C:\Users\FrontDesk\LFD2
    git pull
    py -m unittest discover -s tests -v
    py tools\extract_single_vtfx.py

If that reports valid header fields, optionally copy the private texture locally:

    py tools\extract_single_vtfx.py --extract

An existing community-supported [VTFX Reader](https://github.com/rob5300/vtfx_reader) can convert Xbox DXT1/DXT5 and LZMA-resource VTFX files to PNG. The original texture **has not yet been decoded or shown in Chrome**; proper map UV and material-binding support will still be needed.

Step-by-step guide: [VTFX_FIRST_TEXTURE.md](docs/VTFX_FIRST_TEXTURE.md).

## Further research and options

- [Ghidra / Xbox module setup](docs/GHIDRA_SETUP.md)
- [Verified executable/module map](docs/MODULE_MAP.md)
- [Detailed reverse-engineering roadmap](docs/ROADMAP.md)
- [Legacy standalone original zombie demo](docs/PLAY.md)

Research tools include `tools/inspect_xex.py`, `tools/prepare_xex.py`, `tools/inspect_pe.py`, and `tools/catalog_modules.py`.

The publicly released [Valve Source SDK 2013](https://github.com/ValveSoftware/source-sdk-2013) includes HL2/HL2:DM/TF2 code, **not a complete L4D2 engine**; it has license restrictions. Any Source/L4D2-derived project must respect the rights of the game publisher and third-party authors.

**Never commit Xbox game executables, decrypted binaries, maps, textures, models, music, or other commercial assets to this public GitHub repository.**
