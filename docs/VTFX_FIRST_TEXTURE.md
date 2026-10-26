# First original L4D2 texture: Xbox VTFX → private image

## Confirmed original game data (October 26, 2026)

The owner ran all **66** Python tests successfully and confirmed full filename-level coverage of the hotel: **189/189 materials**, **10,840/10,840 face references**, and **zero cross-pack duplicates**.

The locally owned original Xbox archive \`left4dead2/zip1.360.zip\` contains \`materials/plaster/plaster_int_14.360.vtf\`. Its ZIP local header exists, matches the filename, and the payload starts with \`56 54 46 58 00 00 03 60\` (ASCII \`VTFX\` plus big-endian version \`0x360\`). Nine other sampled texture files from zip1 and the hotel's BSP PAKFILE also have VTFX signatures.

## Step A — inspect a single VTFX header

\`\`\`powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\extract_single_vtfx.py
\`\`\`

The default reads only the VTFX header for the original \`plaster/plaster_int_14\` wall texture. It reports width/height, format ID, header size and resource count from Valve's **big-endian \`VTFFileHeaderX360_t\`** layout. No original data is written.

If the read-only header check succeeds, explicitly copy just that original texture into an ignored private folder:

\`\`\`powershell
py tools\extract_single_vtfx.py --extract
\`\`\`

Expected private destination:

    C:\Users\FrontDesk\LFD2\research\local\vtfx\plaster_int_14.360.vtf

The tool checks the local ZIP header, exact filename, unencrypted/stored member status, maximum 8 MB single-entry size, archive bounds, and VTFX version. It refuses overwrites. It does not modify ZIP archives, perform image conversion, or communicate with external services.

For a map-specific asset in the hotel's embedded BSP PAK, pass \`--source map\` and an exact filename, such as:

\`\`\`powershell
py tools\extract_single_vtfx.py --source map --material "materials/maps/c1m1_hotel/c-200_5022_1257.hdr.360.vtf"
\`\`\`

This defaults to read-only too. Use \`--extract\` only when the header is valid and you want the specific asset privately.

## Step B — convert VTFX to PNG (external open-source converter)

One community-maintained converter is [rob5300/vtfx_reader](https://github.com/rob5300/vtfx_reader), which supports Xbox 360 VTFX including DXT1/DXT5, endianness correction and LZMA resources. Windows binaries are offered on the [project release page](https://github.com/rob5300/vtfx_reader/releases/latest). Inspect the release and trust the publisher before running any downloaded executable.

Example, **after** downloading and extracting the Windows utility into a folder (adjust path to where it was saved):

\`\`\`powershell
.\vtfx_reader.exe -i "C:\Users\FrontDesk\LFD2\research\local\vtfx\plaster_int_14.360.vtf" -o "C:\Users\FrontDesk\LFD2\research\local\vtfx\png"
\`\`\`

The resulting PNG is private original game artwork and must stay in gitignored \`research/local/\`. **Do not put VTFX, PNG, original maps, or engine files into the public GitHub repo.**

## What remains before the browser can use the texture

1. Visually verify that the first converted PNG is correct, not inverted, corrupt or off-color.
2. Export per-face Source texinfo texture vectors and normalized UV coordinates (current browser mesh contains positions only).
3. Preserve a material ID for each emitted triangle and map the 189 names to their VMT/VTFX dependencies. Some VMTs refer to *other* basetextures, and tool/skybox materials should not be treated as opaque wall surfaces.
4. Add local-only PNG file loading, WebGL2 texture bindings/atlases, and material batching.
5. Add displacements, static props, decals, lighting, collision, and later engine behavior.

A valid VTFX signature or header is **not** a converted image, and a rendered hotel mesh is **not** full Left 4 Dead 2 gameplay.

## References

- [Valve Source SDK 2013 vtf.h, VTFFileHeaderX360_t](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/public/vtf/vtf.h)
- [rob5300/vtfx_reader](https://github.com/rob5300/vtfx_reader)
