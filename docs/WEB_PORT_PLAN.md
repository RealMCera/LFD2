# LFD2 Chrome port — real-game architecture and milestones

## Target

**A browser port of the actual Xbox 360 Left 4 Dead 2 gameplay, not a loosely inspired mini-game.**

The existing `docs/index.html` is an early original raycasting *visual prototype*, not the target engine. It has no link to the extracted XEX2 code, Source BSP maps, archive textures, or commercial gameplay. Refining its CSS cannot turn it into an accurate port.

## What vel.gg/bsz demonstrates

The BO1 Zombies browser project uses an existing C++ game-engine reimplementation compiled into **WebAssembly**, with browser platform layers for graphics, sound, multiplayer, and file storage. A publicly documented fork separates a game engine, web frontend, and map downloads; this is not an HTML-only recreation.

Source: https://github.com/jplot/bo1z-client — technical README on its `engine/`, `client/`, `server/` structure.

This does **not** mean we can copy the BO1 executable, engine binary, compiled WebAssembly, or map assets and substitute L4D2 files. The engines are unrelated, and neither repository provides a drop-in L4D2 port.

## What we actually have

The owner extracted and locally verified 22 Xbox 360 **PowerPC XEX2** modules, including:

- `left4dead2/bin/server_360.dll`: 5,740,436 bytes of `.text` instructions within decoded PE32; base `0x89780000`, entry `0x89DED900`.
- `left4dead2/bin/client_360.dll`: original XEX2 present, but not yet decoded/analyzed.
- `bin/engine_360.dll`: original XEX2 present, but not yet decoded/analyzed.
- 24 BSP maps and eight Xbox `.360.zip` packs containing game resources.
- The `default.xex` launcher and the rest of the original modules.

**These are not native browser/WebAssembly modules.** Xbox PowerPC machine instructions cannot be passed directly to Emscripten and compiled for WebAssembly. The reverse-engineering/recompilation path must first produce executable portable code and reproduce missing Xbox and Source engine services. That is substantial work, not a one-command conversion.

Ghidra-derived C-like pseudocode is not automatically correct or buildable C++.

## Workstreams and completion gates

### Stage 1 — inspect original content formats (NOW)

- [x] Inventory local L4D2 archive, 22 XEX2 modules, 24 maps and eight ZIP-named packages.
- [x] Decode and inspect one server module with PE/XEX base/entry verification.
- [x] Add a **header-only** Source BSP / Xbox package probe (no data export).
- [ ] Run `tools/probe_source_assets.py` on the user's actual extracted files and identify the BSP byte order, header fields, and container signatures.

From PowerShell in the repository:

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\probe_source_assets.py
```

Share the short console report, not maps or zipped game data.

### Stage 2 — display a real locally owned L4D2 map in 3D

- [ ] Confirm Source BSP version and 64-lump layout from local metadata.
- [ ] Build a **local-only BSP-to-WebGL2 viewer**: world geometry, basic camera and collision, with temporary materials.
- [ ] Decode original Xbox ZIP asset manifests locally. The `.360.zip` packages can be a modified Source ZIP format; standard unzip may not work.
- [ ] Build a local importer for Source models, textures and materials; preserve original assets only in the user's browser/local storage.

**Visual acceptance criterion:** Walk around a real user-supplied L4D2 map, rather than our made-up rectangular maze. No textures/assets hosted publicly.

### Stage 3 — restore actual behavior

- [ ] Validate `client_360.dll` and `engine_360.dll` code section layouts.
- [ ] Use Ghidra to identify key exports and subsystem boundaries across server, client, engine and shared modules.
- [ ] Evaluate a game-specific clean-room/native-C++ reimplementation and suitable recompiler/runtime research tools. Existing Xbox recompilation tools may rely on x86-specific intrinsics/runtime and **are not assumed WebAssembly compatible**.
- [ ] Port real Source/L4D2 movement, collision, renderer, audio and gameplay subsystems as independently verified C++ components where rights permit.
- [ ] Compile reconstructed portable code with Emscripten to WASM and connect browser graphics/input/audio.

**Behavior acceptance criterion:** Native engine functionality runs in WebAssembly, tested against observed original behavior—not a replacement zombie game written only in JavaScript.

### Stage 4 — browser sessions and packaging

- [ ] Load only game files the user explicitly supplies locally; do not ship the copyrighted executable, maps, character models, music or textures on GitHub Pages.
- [ ] Optimize WebGL2 rendering, input pointer lock, audio and map streaming.
- [ ] Add network transport and co-op only after a working local single-player session.
- [ ] Consider WebGPU as an optional renderer. Hosting WebAssembly with shared memory may require cross-origin isolation and special HTTP headers, so GitHub Pages may not be sufficient for a full engine build.

## Licensing and source availability

Valve's public [Source SDK 2013](https://github.com/ValveSoftware/source-sdk-2013) has source for HL2/HL2:DM/TF2, **not a complete L4D2 Source engine implementation**. It uses Valve's **non-commercial Source 1 SDK License**; its availability does not give permission to distribute the retail L4D2 code or assets. Any third-party open source components must have their licenses checked.

[ReXGlue](https://github.com/rexglue/rexglue-sdk), [Xenon-Recomp](https://github.com/nimauria/Xenon-Recomp) and similar projects are research possibilities, **not validated L4D2-to-browser solutions**. Confirm platform targets and missing instructions/runtime features before choosing any tool.

**Current state:** Only metadata analysis and original standalone HTML prototype are complete. A genuine browser L4D2 port is not playable yet. This plan exists to make progress without describing unfinished work as a finished port.
