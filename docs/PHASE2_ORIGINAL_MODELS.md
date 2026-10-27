# Phase 2 — Original hotel models, doors and displacement surfaces

## Completed starting point (October 26, 2026)

The hotel Chrome viewer loads original `c1m1_hotel.360.bsp` brush geometry, uses original Source UVs, and renders 53 locally converted Xbox materials on 20,198 of 27,374 brush triangles (73.8%). The one-folder manifest loader is screenshot-confirmed and required zero manual PNG selections after the private conversion run.

**Do not resume iterative texture conversions unless a specific visible surface is demonstrably missing.** Source `TOOLS/`, `DEV/`, `SKY/` and `EFFECTS/` brushes can be nonvisual triggers, fog volumes, debug fills and skybox placeholders. They should not all get arbitrary images.

## Next implementation: real authored model assets, not invented replacements

1. **Inventory** original map entity classes (dynamic/physics props, movable doors and similar objects), game-lump static prop model dictionary, model placement count and Source displacement lumps.
2. **Validate** game-lump static prop record version and stride from the actual local Xbox file before parsing rotations/positions. Different Source branches have incompatible record versions; never assume vanilla PC offsets for Xbox L4D2.
3. **Decode original local console model data** for a small visible object and its texture materials. Locate matching `.mdl`, `.vvd`, `.vtx` and `.phy` assets in the local Xbox archives. Keep generated geometry under ignored `research/local/`.
4. **Render real props** using model transform, UVs, materials and basic depth sorting. Prefer proper geometry to generic debug cubes, which would misrepresent the actual game.
5. **Implement doors and environmental motion** with properties derived from the original BSP entity definitions. Input/output linkage and Source game logic will require a later independent engine subsystem.
6. **Integrate displacements and lightmaps** before claiming the original environment is visually complete. Props, physics, navigation, characters and gameplay remain separate systems.

## Immediate read-only test

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\inspect_hotel_elements.py
```

The inspector reports total entity classes and example coordinates, Source GAME_LUMP version/flags, static model dictionary and static prop count if safely recognized, and displacement metadata sizes. It does not write game data or perform unsafe model decoding. The owner **has now run it** successfully on the real Xbox BSP; 112 tests passed. The compressed sprp payload was not decoded by the first read-only version.

Valve Source BSP source reference: https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/public/bspfile.h
Source static-prop version caution: https://srctools.readthedocs.io/en/stable/modules/bsp.html

## Verified October 26 Xbox BSP results

Original map `c1m1_hotel.360.bsp` contains **1,894 entity blocks**; **314 `prop_physics`**, **72 `prop_dynamic`**, **29 `prop_door_rotating` + 1 checkpoint variant**, **195 `func_brush`**, **8 `func_breakable`**, and **4 `func_movelinear`**. Other entities include weapons and survivor positions. Original model paths already include elevator buttons, elevator pulleys and metal doors.

The Xbox game lump directory lists **`sprp` v9 with compression flag 1** and an **uncompressed `filelen` of 156,212 bytes**, plus `dprp` v4 and an empty terminator. Source's official `GAMELUMPFLAG_COMPRESSED` means the next file offset or a compression wrapper is needed to establish the actual on-disk size. Our new bounded LZMA probe now attempts a true Valve wrapper and validates the static model dictionary; if the wrapper is different, it reports the observed header magic instead of guessing.

The original displacement data is **928 bytes of `DISPINFO` and 3,740 bytes of `DISPVERTS`**, which do not match the naive 176-byte info-record assumption. This must be decoded separately before reintroducing missing displacement surfaces.

## Next real-model audit and placement manifest

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\inspect_hotel_elements.py
py tools\inspect_hotel_model_assets.py --export
```

The new model audit scans only the **local Xbox `zip0.360.zip` central directory** to check which original `.mdl`, `.vvd`, `.vtx` and optional `.phy` companions exist, and probes 16-byte headers of one available model set. The optional export saves **`research/local/hotel-model-placements.json`**, containing only original entity model paths, world-space position/angle and class type, for future genuine asset rendering. It does **not** decode full model geometry or upload commercial data. The exported placements cover authored `prop_physics`, `prop_dynamic` and door models; static game-lump instances will be added only after their record layout has been verified.

Our browser already handles the real map geometry and materials. **The next milestone is actual original model decoding and placement**, not another texture experiment.

## Verified compressed static props — October 26, 2026

Owner's local run passed **120/120 tests**. The actual Xbox v9 `sprp` decompressed from the GAME_LUMP relative offset and yielded **188 dictionary entries, 1,748 instances and an apparent 72-byte per-instance stride**. Source format documentation independently identifies Left 4 Dead 2 v9 as **72 bytes** ([srctools](https://srctools.readthedocs.io/en/stable/modules/bsp.html)). An entity inventory separately confirmed **416 placed MDL models**: 314 physics, 72 dynamic and 30 rotating doors. The exported private entity-only manifest is `research/local/hotel-model-placements.json`.

**Important:** the previous 0/52 dynamic and 0/185 static model availability result was **only against `left4dead2/zip0.360.zip`**. It is too early to claim the game assets are missing. The new cross-package inventory examines all eight `.360.zip` archive directories, loose extracted files and the BSP embedded PAK. It also validates **all 1,748** records instead of relying on average stride alone.

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\build_hotel_prop_manifest.py --export
```

The new JSON `research/local/hotel-all-props.json` contains original static and entity placements, each with Source model path, position, orientation and class. Original commercial model geometry is not copied. If any record fails validation, the decoder aborts rather than exporting guessed positions. The first full-PC run is pending.

## October 27: Original 2,164 placements confirmed; companion name diagnostics

Owner ran **127/127 tests successfully**. Full local Xbox archive and map scan reported **10 sources examined, 0 failures**. The hotel map successfully decoded **all 1,748 static placements from genuine 72-byte L4D2 v9 records**, combined with **416 entity/door placements**, and wrote `research/local/hotel-all-props.json` privately. **All 228 unique referenced MDL model paths matched** their archive names.

The archive contains **3,211 MDL, 3,182 VVD, 3,182 VTX, and 2,383 PHY filenames** under `left4dead2/zip0.360.zip`. However, the current conventional matching rules returned **zero full MDL/VVD/VTX groups**. This is a filename/path matching diagnostic, **not** evidence that the thousands of companion files are absent. A Source Xbox 360 VTX is normally named `model.360.vtx`, but game/archive variants must be checked against actual names.

The updated `tools/build_hotel_prop_manifest.py` prints read-only samples of actual VVD/VTX names, and the exact companion suffixes and nearby file candidates for the hotel's most frequently placed models. No need to export again; the combined manifest already exists.

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py tools\build_hotel_prop_manifest.py
```

**Next milestone:** resolve actual Xbox companion filename naming, then verify the first MDL/VVD/VTX binary headers, decode one genuine chair/door mesh privately and finally render that model at an original decoded Source position in Chrome. No original commercial model bytes belong in GitHub.

## October 27: Correct Xbox studio model names and first-chair binary inspection

Owner's read-only run passed **128/128 Python tests** and found model filename suffixes beside each referenced `*.mdl`. The model files are present: Source Xbox VTX indexes are named **`*.dx90.360.vtx`**, not the assumed `*.dx90.vtx`, and physics files are `*.360.phy`. VVD files retain `*.vvd`, MDL retain `*.mdl`. Model mesh companion matching is now fixed.

The new single-model tool `tools/probe_original_hotel_model.py` safely reads at most **64 bytes of binary headers for each of the original chair MDL, VVD and VTX**, checks plausible Xbox byte order and their common Source checksums, and reports the original file sizes. It does not itself decode triangle strips or vertex weights; these must be interpreted using the source studio structures before any accurate 3D rendering.

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\build_hotel_prop_manifest.py
py tools\probe_original_hotel_model.py
```

If that succeeds, use `py tools\probe_original_hotel_model.py --extract` to copy **just the three original chair files** into ignored `research/local/original-models/models/props_furniture/` (never the public GitHub repo). The tool will refuse overwrites and unknown compressed ZIP members. If Source checksums do not agree, inspect the headers before writing any mesh-conversion logic; do not claim the object is renderable simply because three filenames match.

Reference material: [MDL studio headers](https://pysourcesdk.github.io/ValveMDL/datastructures/studiohdr.html), [VVD vertex headers](https://pysourcesdk.github.io/ValveMDL/datastructures/vvd.html), and [VTX optimized mesh header](https://pysourcesdk.github.io/ValveMDL/datastructures/vtx.html). The actual original Xbox data still needs the owner's local validation.

## October 27: First authentic hotel chair files extracted — MDL is Valve LZMA-wrapped

The owner's latest local console run successfully extracted exactly three private original Xbox 360 files from `left4dead2/zip0.360.zip`:

- `research/local/original-models/models/props_furniture/hotel_chair.360.mdl` — **482 bytes**, starts with `LZMA` (compressed Source studio model, **not** a corrupt `IDST` header)
- `research/local/original-models/models/props_furniture/hotel_chair.360.vvd` — **21,717 bytes**, Source `IDSV` version **4**, Xbox big-endian, checksum `f3737e00`
- `research/local/original-models/models/props_furniture/hotel_chair.dx90.360.vtx` — **3,876 bytes**, optimized mesh version **7**, Xbox big-endian, checksum `f3737e00`, one bodypart and one LOD

**The previous “all three headers recognized: False” was expected:** the old inspector treated the 482-byte compressed model file as raw `IDST`. Both uncompressed companion checksums already match. The original game/model file archive is untouched and all original bytes remain under Git-ignored `research/local/`.

`tools/probe_original_hotel_model.py` now detects the `LZMA` wrapper, decodes the model in memory through our already-tested bounded Valve LZMA parser, reads its actual Source model header and validates the full MDL/VVD/VTX checksum trio. It also reports bounded Source `studiohdr_t` bone/material/bodypart counts to prepare vertex/index conversion. Only `--write-decoded-mdl` writes the decompressed result privately; it refuses mismatched checksums and existing output.

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\probe_original_hotel_model.py
```

If the real decompressed MDL reports **all three headers recognized** and **checksum matches**, save the decoded file without extracting or overwriting the three raw files:

```powershell
py tools\probe_original_hotel_model.py --write-decoded-mdl
```

The result stays under `research/local/original-models/decoded/models/props_furniture/hotel_chair.mdl`. The user has **not yet run this new LZMA stage**; model vertices, triangle strips, material assignments and actual rendered chair remain further work. We will not substitute boxes or claim the game port is playable.


## October 27: Original chair MDL / VVD / VTX fully verified — real triangle mesh next

The owner ran **140 Python tests successfully** on Windows and confirmed the original chair's three Source checksums match **f3737e00**. The .360.mdl is 482 compressed bytes, LZMA-decoded into **1,792 bytes of real Source version 49 model data**. Its studiohdr tables passed validation: **1 bone, 1 texture, 1 bodypart**. Original VVD is big-endian v4 (21,717 bytes); VTX is big-endian v7 (3,876 bytes), 1 bodypart / 1 LOD. The decoded private model exists at \`research/local/original-models/decoded/models/props_furniture/hotel_chair.mdl\`.

We have now committed **tools/convert_original_hotel_chair.py**, a bounded one-original-model triangle converter. It reads that private trio, follows Source MDL bodypart/model/mesh tables, reads VVD vertex position/normal/UV records (including validated LOD0 fixups), follows VTX optimized stripgroup/strip original vertex IDs, validates common checksum and emits a **private JSON mesh** with original vertices and triangles. The first implementation targets Source v49 / VVD4 / VTX7 and **LOD0** with original simple/fixed chair geometry, not skinned animation, arbitrary models or fake approximations.

The Chrome browser viewer also has a first-phase **ORIGINAL SOURCE MODEL TRIANGLES** panel. It can load the converted \`hotel-chair.mesh.json\` and existing \`hotel-all-props.json\` locally. The browser rotates/translates exact chair triangle geometry to the **47 original BSP chair placements** and shows neutral lighting/shading so geometry can be inspected. Original chair VMT/texture bindings, reflections, lightmaps, collision and game logic are not yet implemented.

### Windows verification and first real geometry preview

\`\`\`powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\convert_original_hotel_chair.py
py tools\convert_original_hotel_chair.py --run
Start-Process (Resolve-Path ".\docs\map-viewer.html").Path
\`\`\`

The first converter run **without --run** validates and prints the exact original triangle and vertex counts without writing. Use \`--run\` only after it successfully reports geometry; it creates ignored \`research/local/hotel-chair.mesh.json\` and refuses overwrite. No game model bytes are uploaded to GitHub.

In the map viewer, choose the existing UV-enriched original hotel BSP mesh, optionally reload the private \`hotel-complete\` texture folder, then find **PHASE 2 · ORIGINAL SOURCE MODEL TRIANGLES** in MAP LOADER. Pick both \`research/local/hotel-chair.mesh.json\` and \`research/local/hotel-all-props.json\`. Chrome's first model overlay stays neutral gray until authentic model materials are supported. Toggle SHOW/HIDE ORIGINAL CHAIRS to compare with the bare map.

**Current validation boundary:** the Python converter and new WebGL viewer have been committed with synthetic tests and JavaScript syntax checks, but they have not yet been run against the user's complete actual VVD/VTX contents in a reported console run. If the decoder rejects an offset, index or unsupported strip layout, it stops rather than inventing coordinates or indices. Do not claim the actual chair renders until the owner's browser verification.

References: [Valve's Source optimization/VTX structures](https://swarm.workshop.perforce.com/files/guest/knut_wikstrom/ValveSDKCodepublic/optimize.h), [studio model hierarchy](https://pysourcesdk.github.io/ValveMDL/datastructures/mesh.html), [VVD vertex header](https://pysourcesdk.github.io/ValveMDL/datastructures/vvd.html).
