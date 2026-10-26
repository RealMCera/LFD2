# First real L4D2 level → Chrome WebGL2 preview

**EXPERIMENTAL / the owner's original hotel map conversion and basic WebGL2 rendering are now screenshot-confirmed on October 26, 2026.** The next milestone is a useful eye-level viewpoint. This is the first local BSP geometry experiment, not playable Left 4 Dead 2. It reads the user's legitimately obtained Xbox BSP, attempts to reconstruct brush-face triangles, and opens them as an untextured fly-through in a standalone WebGL2 viewer. No Valve binaries, maps, models, textures or game data are uploaded to GitHub.

## Improved start position after the first screenshot

The owner's October 26 screenshots confirm **27,374 triangles render in Chrome**, including a recognizable eye-level hotel corridor from `info_player_start`. The earlier camera was above the entire map, so only giant flat gray surfaces were visible. This is not a geometry conversion failure. The existing untextured mesh remains valid.

To generate a NEW enriched private mesh using spawn points from the compressed original BSP entity lump, without overwriting the already successful mesh:

    cd C:\Users\FrontDesk\LFD2
    git pull
    py -m unittest discover -s tests -v
    py tools\add_bsp_spawns.py

Expected new output:

    C:\Users\FrontDesk\LFD2\research\local\c1m1_hotel_spawns.mesh.json

If the tool reports no survivor or player starts, keep using **Overview** and share the console counts; no coordinates should be invented.

Reload `docs/map-viewer.html` in Chrome and choose the **new** file. The viewer automatically starts at the first available camera start when supplied, and offers:

- **1:** camera to selected start (if extracted)
- **2:** high-level overview
- **N:** cycle to next spawn
- **3:** toggle highlighted brush edges to make the untextured rooms/corridors more legible
- **WASD / mouse:** free-flight inspection, with Space/Ctrl vertical movement
- **OPEN MAP LOADER:** reselect local mesh; the panel now has an × close button.

The earlier `c1m1_hotel.mesh.json` still works but contains **no spawn metadata**, so the viewer will begin in overview mode. Neither file should be committed to public GitHub.

## Step 1 — Confirm Xbox header details

Open Windows PowerShell inside the checkout and run:

    cd C:\Users\FrontDesk\LFD2
    git pull
    py -m unittest discover -s tests -v
    py tools\inspect_bsp_lumps.py

Check especially lump **58: hdr_faces**, **7: faces**, **3: vertices**, **12: edges**, and **13: surfedges**. The original probe saw version **20**, big-endian **PSBV**, and **0 bytes for lump 7**, so the new inspector reports whether lump 58 holds HDR render faces. Several compressed lump sizes need not be divisible by structure size.

## Step 2 — Convert the local hotel map to a private JSON mesh

    py tools\bsp_to_browser_mesh.py

Input (already extracted):

    game-extracted\left4dead2\maps\c1m1_hotel.360.bsp

Output (Git-ignored, local only):

    research\local\c1m1_hotel.mesh.json

The converter chooses the BSP header layout by bounds checks, tries lump 58 first, then 7 or 27, and recognizes the **Valve LZMA** compression wrapper when present. It validates vertex structure sizes and triangulates ordinary Source brush faces. The default triangle cap is 600,000 as a safety check; it refuses to overwrite an existing mesh.

**Hotel map conversion already succeeded on the owner's PC** with 10,840 Source faces, 27,374 rendered brush triangles, and a private 777,248-byte mesh. If the file already exists, the converter intentionally refuses to overwrite it; **do not run conversion again unless intentionally selecting a new output filename**.

**If conversion stops for another map, read the error and share the text output only.** Do not upload the map. Xbox variants may use different compression, face layouts, or nonstandard geometry that need explicit support; do not assume conversion will succeed.

## Step 3 — View in Chrome using local files

    Start-Process (Resolve-Path ".\docs\map-viewer.html").Path

If this opens Edge, right-click docs\map-viewer.html → Open with → Google Chrome.

In the viewer choose **SELECT A LOCAL .MESH.JSON FILE**, then browse to:

    C:\Users\FrontDesk\LFD2\research\local\c1m1_hotel.mesh.json

Click the scene to lock the pointer; WASD to fly, mouse/arrow keys to look, Space/Control to fly vertically, Shift to speed up, Escape to release pointer. Since the browser uses a file picker, the map geometry is not hosted or requested from GitHub.

### Known limitations

- No textures, props, static models, NPCs, campaign scripting, physics, ground collision or true L4D2 play yet
- Displacements currently skipped, so terrain may have holes; brush faces may have gaps or incorrect orientation
- Browser's GPU and the converter's JSON memory usage may limit map size; Chrome on Windows with WebGL2 needed
- The original mesh starts above the level; the enriched mesh uses Source player/survivor start metadata as a camera guide. Users fly without collision in either mode
- This does not use or execute the PowerPC modules; a real Chrome game port requires extensive engine reimplementation/recompilation

## Confirmed local conversion results

- Source file: `c1m1_hotel.360.bsp` (PSBV big-endian BSP v20)
- Required geometry lumps are LZMA-wrapped, with HDR faces in lump **58**; standard faces lump **7** is empty.
- Decoded **10,840** HDR faces into **27,374** triangles, skipping 43 displacement faces and 2,012 degenerate triangles.
- Bounds: `[-2284.8, -748, -1616]` to `[11616, 16320, 3584]`.
- Private output: `research/local/c1m1_hotel.mesh.json` (**777,248 bytes**).
- All **23 earlier synthetic Python tests passed**; new spawn helper tests still need to run on the owner's PC. The old distant untextured geometry has now been visually confirmed in Chrome.

## Current milestone

The owner's latest screenshot confirms a real eye-level hotel hallway built from the Xbox Source brush geometry. The next step is finding original materials and texture data: see [MATERIAL_PIPELINE.md](MATERIAL_PIPELINE.md) and run `py tools\inspect_map_materials.py --pack` after pulling the latest changes.

## After the first successful geometry preview

Validate the geometry in hotel, streets, and mall. Add static-prop decoding, displacement meshes, material/texture rendering, spawn entities, movement with collision, and much later the original gameplay via a compatible portable engine. The [real port plan](WEB_PORT_PLAN.md) describes that longer path.
