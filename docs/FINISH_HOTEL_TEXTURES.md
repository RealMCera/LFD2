# Finish the Dead Center hotel texture stage

## Final verified result — October 26, 2026

The owner provided a screenshot of the **completed local folder-loading workflow** running in Chrome. It rendered **53 original materials on 20,198 of the original 27,374 hotel brush triangles (73.8%)**, with **0 unavailable files reported**. Wallpaper, carpet, floor borders and ceiling tiles are in place. This validates the one-command/original material manifest and one-folder Chrome loader end-to-end.

We are **closing the brush geometry + supported original material phase** here. The remaining 7,176 triangles are not necessarily 7,176 missing normal textures; some represent Source special/tool/debug surfaces. That remainder also does not measure separately missing model props, BSP displacements, lighting or gameplay.

Next practical action: `py tools\inspect_hotel_elements.py` to inspect static prop model dictionaries, dynamic prop/door entity class counts, and displacement metadata from the original local BSP. All original models/game data remain private.

## What is complete

Your screenshot has already verified real Xbox-derived textures on the original browser hotel: **14 texture materials and 13,696 of 27,374 brush triangles**. This was a manually selected preview. The new finalization tool and browser folder loader eliminate most repetitive one-by-one conversion and file picking.

**Scope:** finish loading every *supported original brush material texture* that can be resolved from the extracted Xbox ZIP and hotel embedded BSP PAKFILE. It is not a complete engine port and will not invent props, displacements, lighting, sounds, physics or zombies.

## One command to prepare original textures

Use your existing Windows folder (the original game files stay private and ignored by Git):

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\finish_hotel_materials.py --run
```

The builder reads `research/local/c1m1_hotel_spawns_uv.mesh.json` and the original game's `left4dead2/zip1.360.zip` plus the embedded `c1m1_hotel.360.bsp` PAKFILE. It reads VMT `$basetexture` references, resolves original Xbox `.360.vtf` images, reuses the PNGs you previously decoded, and uses the installed `research/local/tools/vtfx_reader.exe` for new supported textures. The input game archives aren't modified.

It writes the private directory:

```text
research/local/hotel-complete/
    texture-manifest.json
    textures/
        plaster/
            plaster_int_14.png
        concrete/
            concrete_floor_10.png
        ... additional original material image paths
    original-vtfx/       (private local copy, only when needed)
    conversion-work/     (private converter output, only when needed)
```

**This folder and its artwork must remain under `research/local/`; never commit or upload it to the public repository.** It can be processed again without overwriting existing valid PNGs. The tool prints an exact report of mapped brush triangles, unresolved materials, and unsupported conversions; failed textures are listed instead of being given the wrong artwork.

To check what can be resolved **without writing any files**, run `py tools\finish_hotel_materials.py` (without `--run`).

## One folder selection to load the hotel in Chrome

```powershell
Start-Process (Resolve-Path '.\docs\map-viewer.html').Path
```

1. Refresh Chrome with **Ctrl+Shift+R** to use the updated local JavaScript files.
2. Choose the previously working `research\local\c1m1_hotel_spawns_uv.mesh.json` mesh.
3. Reopen **MAP LOADER**. In **FINAL HOTEL TEXTURE SETUP**, choose **LOAD COMPLETE LOCAL TEXTURE FOLDER**.
4. Select the **`research\local\hotel-complete` folder** itself. Chrome will read the private texture manifest and all matching local PNGs; it won't upload them or request any network resource.
5. Close the loader. All successfully resolved materials display simultaneously, without the old 8- or 16-file selection loop.

The renderer accepts up to **256 Source material IDs and 80 million image pixels**, to avoid unbounded WebGL memory usage. It matches full Source paths, so two same-named materials from different directories won't be incorrectly combined. The **MATERIAL COVERAGE** panel reports what actually loaded; not everything in the Source BSP is meant to have a visible texture.

## Tool/debug geometry

**HIDE TOOLS / DEV / SKY / EFFECTS** defaults on in the loader. These special Source brush materials are not ordinary hotel wall textures; rendering them as opaque gray triangles can create artificial walls. You can turn the checkbox off to compare with the original gray prototype. The toggle filters only the browser draw indices; original BSP geometry, material IDs, UV data and crosshair inspection remain intact.

## Definition of done for this phase

We can close the **original brush geometry + material textures** phase when the local builder produces a texture-manifest report, Chrome loads the resulting folder and the remaining gaps have documented explanations (unsupported image encoding, nonvisual Source material, missing BSP displacements/props, or other Source shader work).

An unresolved material or missing surface is not automatically fixed by a PNG. This stage also does **not** make Left 4 Dead 2 playable in Chrome. The next independent stage is BSP displacements, static props, doors and collision; subsequently game-engine behavior and gameplay.

### Testing and limitations

The first versions of these finalization tools are committed with synthetic Python and JavaScript tests. They have **not yet been exercised on your complete private Xbox texture files or confirmed in your Chrome screenshot**. A GitHub Actions workflow runs synthetic Python tests, JavaScript syntax checks and manifest matching tests. If your Windows command reports unresolved files, those are genuine format or dependency limits to investigate rather than reasons to resume blind manual PNG selection.