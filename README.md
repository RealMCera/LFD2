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
- Verified original XEX/PE memory addresses and **23 synthetic tests** in the owner's latest report.
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


## Next milestone — original Source material paths and Xbox textures

The October 26 Chrome screenshot confirms an eye-level hotel corridor with original brush geometry. Now the largest missing visual feature is **real Source material/texture mapping**, not more camera changes.

I've added [tools/inspect_map_materials.py](tools/inspect_map_materials.py) and synthetic tests to look up the original material names in the BSP, then attempt to list asset filenames in the user's local Xbox \`.360.zip\` (without unpacking or uploading files):

    cd C:\Users\FrontDesk\LFD2
    git pull
    py -m unittest discover -s tests -v
    py tools\inspect_map_materials.py --pack

Share only the printed metadata. This will tell us which L4D2 wall/floor material references are actually used, and whether the Xbox package exposes a standard ZIP directory. The next engineering step is a local texture converter and UV/material mapping, not a fake texture overlay.

[Material pipeline details](docs/MATERIAL_PIPELINE.md)

## Further research and options

- [Ghidra / Xbox module setup](docs/GHIDRA_SETUP.md)
- [Verified executable/module map](docs/MODULE_MAP.md)
- [Detailed reverse-engineering roadmap](docs/ROADMAP.md)
- [Legacy standalone original zombie demo](docs/PLAY.md)

Research tools include `tools/inspect_xex.py`, `tools/prepare_xex.py`, `tools/inspect_pe.py`, and `tools/catalog_modules.py`.

The publicly released [Valve Source SDK 2013](https://github.com/ValveSoftware/source-sdk-2013) includes HL2/HL2:DM/TF2 code, **not a complete L4D2 engine**; it has license restrictions. Any Source/L4D2-derived project must respect the rights of the game publisher and third-party authors.

**Never commit Xbox game executables, decrypted binaries, maps, textures, models, music, or other commercial assets to this public GitHub repository.**
