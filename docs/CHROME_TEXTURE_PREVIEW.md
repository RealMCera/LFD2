# First original texture in Chrome — one-material preview

## Latest confirmed results

The owner's Windows PowerShell report on October 26, 2026 confirms:
- **82/82 synthetic Python tests passed**.
- The new \`py tools\add_bsp_material_uvs.py\` finished successfully, creating \`research/local/c1m1_hotel_spawns_uv.mesh.json\`.
- That private mesh contains **27,374 triangles**, **187 actually rendered Source material IDs**, and **82,122 per-triangle-corner UV pairs**. The older 189 count includes BSP material references outside this triangle mesh; 187 is not necessarily an error.
- The original Xbox plaster interior texture is extracted privately (\`research/local/vtfx/plaster_int_14.360.vtf\`, VTFX version 864.8, 512×512, DXT1).
- **The PNG conversion did not run** because the Windows converter executable \`research/local/tools/vtfx_reader.exe\` has not been installed.

## Step 1 — install the Windows VTFX converter manually

1. Open the publisher's [VTFX Reader releases page](https://github.com/rob5300/vtfx_reader/releases/latest).
2. Under **Assets**, download the Windows release. If you download a ZIP, extract it on your computer.
3. Find **\`vtfx_reader.exe\`** inside what you downloaded.
4. Create \`C:\Users\FrontDesk\LFD2\research\local\tools\` and copy only the executable there. This folder is private and gitignored.

In PowerShell:

\`\`\`powershell
cd C:\Users\FrontDesk\LFD2
New-Item -ItemType Directory -Force ".\research\local\tools" | Out-Null
Test-Path ".\research\local\tools\vtfx_reader.exe"
\`\`\`

The last command must print \`True\` before conversion can work. Do not rename a ZIP file to .exe, or mistake the GitHub source-code download for a prebuilt Windows release. The code uses no network and will not download or install third-party applications for you.

If your trusted release executable is in another location, you can keep it there and supply the path:

\`\`\`powershell
py tools\convert_local_vtfx.py --converter "C:\full\path\to\vtfx_reader.exe"
\`\`\`

## Step 2 — decode the single original wall texture

\`\`\`powershell
py tools\convert_local_vtfx.py
\`\`\`

The wrapper runs the converter with the verified \`-i\` and \`-o\` options for this one privately extracted texture. It validates that at least one PNG is produced with the expected **512×512** dimensions.

Private output folder: \`research/local/vtfx/png/\`. The script refuses overwriting a nonempty destination.

## Step 3 — load the UV-enriched mesh in Chrome

\`\`\`powershell
Start-Process (Resolve-Path ".\docs\map-viewer.html").Path
\`\`\`

In Chrome:

1. Click **SELECT A LOCAL .MESH.JSON FILE** and select **\`research\local\c1m1_hotel_spawns_uv.mesh.json\`**.
2. The browser moves to the original survivor/player start as before. Click **OPEN MAP LOADER** again.
3. Under **OPTIONAL ORIGINAL TEXTURE PREVIEW**, select **\`PLASTER/PLASTER_INT_14\`** (the viewer chooses it automatically when present).
4. Click **SELECT MATCHING LOCAL PNG** and select the PNG produced in Step 2.
5. Close the loader (X) and look around. Only triangles whose material ID matches **\`PLASTER/PLASTER_INT_14\`** will have this PNG. Everything else remains gray.

The PNG is read using the browser's local file picker and uploaded only to local WebGL2 memory. No server request is made. Existing older meshes still render in the original gray-geometry mode.

The material preview uses Source-engine UVs and tiled WebGL texture sampling. Visual orientation and tiling still need to be verified from a screenshot. Texture loading works only after the user supplies a real PNG; the preview does **not** yet resolve VMT basetexture dependencies, batch all materials, render props/lighting, or implement gameplay.

## Subsequent work

- Confirm visual output of \`PLASTER/PLASTER_INT_14\` PNG.
- Add metadata-based dependency resolution for VMT \`$basetexture\`, plus safe opt-in local batch conversion of selected original VTFX textures.
- Improve original Source material batching, tool surfaces, lightmaps, props, and physically plausible navigation.
- Research a genuine portable rendering and gameplay engine; a textured viewer alone is not Left 4 Dead 2 running in the browser.
