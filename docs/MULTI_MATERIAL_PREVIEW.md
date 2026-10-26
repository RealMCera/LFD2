# Multiple original hotel materials in Chrome

## What was verified on October 26

The owner's screenshot shows the original Dead Center hotel brush geometry in Chrome with an authentic Xbox VTFX-derived PNG applied to **1,404 PLASTER/PLASTER_INT_14 triangles**. The full geometry remains **27,374 triangles**, and the private UV mesh contains **82,122 corner UV pairs**. The user had previously passed **82 Python unit tests**; new multi-material tests have not yet been run on the user's PC.

Other surfaces remain gray because only one material had been chosen. This is not evidence of missing geometry; full original materials, displacements, props and lightmaps are still outstanding.

## New read-only material list

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\prepare_hotel_textures.py
```

The tool selects up to **8 high-frequency non-tool original hotel surface materials** that have matching `.360.vtf` filenames in the owner's `left4dead2/zip1.360.zip`, without extracting or converting anything. This is an exact filename match, not interpretation of VMT `$basetexture` dependencies.

## Convert the selected material textures locally

If your personally installed VTFX Reader executable is at `research\local\tools\vtfx_reader.exe`:

```powershell
py tools\prepare_hotel_textures.py --run
```

For a smaller trial:

```powershell
py tools\prepare_hotel_textures.py --count 4 --run
```

The script uses the existing original Xbox ZIP and Source BSP under ignored `game-extracted/`, validates the local file headers and VTFX magic, copies only the specified original materials to private `research/local/hotel-textures/vtfx/`, invokes the trusted local converter per asset, and copies the selected matching-size PNGs into **`research\local\hotel-textures\png\`**. It will not modify the source ZIP, overwrite existing PNG files, download anything, or upload copyrighted data. If some unsupported textures fail to convert, the program reports them and continues with the others.

Using a file under the materials path does not guarantee that it is the actual texture used by a VMT: a proper Source material dependency resolver is a separate project milestone. The preview is a first approximation driven by exact names, not full Source shader emulation.

## Use all the converted PNGs in the browser

```powershell
Start-Process (Resolve-Path '.\docs\map-viewer.html').Path
```

1. Load `research\local\c1m1_hotel_spawns_uv.mesh.json` as before.
2. Click **OPEN MAP LOADER** to reopen the controls.
3. Under **MULTIPLE ORIGINAL MATERIALS**, click **SELECT UP TO 16 LOCAL PNGs**.
4. Browse to `research\local\hotel-textures\png`, press **Ctrl+A** in the file chooser, and open those PNGs.
5. Close the loader and look around. The new texture overlay renders each unique matched material on its corresponding original Source triangles; other surfaces remain gray.

The multi-material loader is capped at **16 textures per selection**. It matches by PNG basename: for example `plaster_ext_20.360_resource_0.png` is assigned only if `plaster_ext_20` maps to exactly one BSP material. Duplicate or ambiguous basenames are skipped rather than guessed. No image is ever transmitted over the network; Chrome loads it into local WebGL2 textures from its native file picker.

The existing **single-material mode remains available** and both overlays may be used independently. If a material is loaded in both, the new multi-material overlay renders over the old one. Toggle either preview off to compare against the gray geometry.

**Not yet validated in Chrome:** the multi-material overlay, its full texture dimensions/orientation and the new batch converter's behavior on all selected original Xbox assets. Please verify with a screenshot after the test commands succeed.

## Larger next milestones

Resolve VMT `$basetexture` mappings instead of relying on equivalent filenames; exclude tool/skybox surfaces correctly; support map-specific BSP PAK resources, displacements and props; add lightmaps, collision and eventual gameplay code. Textured brush geometry alone is not a playable L4D2 port.
