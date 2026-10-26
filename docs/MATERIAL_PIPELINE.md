# Xbox 360 L4D2 map materials — first inspection

## Confirmed so far

The original Dead Center hotel's big-endian \`PSBV\` BSP v20 converted to **27,374 brush triangles**. The browser first-person view is screenshot-confirmed from an \`info_player_start\` point. This exposes the correct corridor/room shape but every surface has generic material shading.

To move toward the *original* game appearance, we need to find the per-face Source texture references and determine how their corresponding Xbox material/texture assets are stored.

Valve's published Source BSP structures identify:
- Lump **2** \`TEXDATA\`: 32-byte records pointing into texture-name string table IDs.
- Lump **6** \`TEXINFO\`: 72-byte records linking geometry UV transforms to texdata IDs.
- Lump **43** \`TEXDATA_STRING_DATA\`: zero-terminated material/texture paths.
- Lump **44** \`TEXDATA_STRING_TABLE\`: 4-byte byte offsets into lump 43.
- Lump **58** \`FACES_HDR\`: 56-byte faces on this Xbox map, using texinfo IDs.

The new read-only inspector connects these references and counts the original materials on the rendered faces. It also optionally asks Python's ZIP reader to list filenames (without extraction) from the local \`zip0.360.zip\` archive.

## Run on the owner's PC

    cd C:\Users\FrontDesk\LFD2
    git pull
    py -m unittest discover -s tests -v
    py tools\inspect_map_materials.py --pack

The output should give counts for Source texinfo/texdata, the 14 most-referenced real material paths, and—if the Xbox package has a readable ZIP central directory—an extension summary and a few asset names. **The inspector does not export textures, maps, or model files.**

If Python reports \`BadZipFile\`, that does **not** mean your Xbox archive is corrupt: Xbox XZIP can differ from the standard ZIP directory format. We will need a specific local archive-directory reader.

## October 26 material and Xbox archive findings

The owner's latest PowerShell report confirms:

- All **32** existing synthetic tests pass.
- `c1m1_hotel.360.bsp` has **228 texdata records**, **3,392 texinfos**, **10,840 HDR faces**, and **189 referenced original material names**.
- **0 unmapped faces** in the material-name lookup.
- Top visual surface references include plaster, ceiling tile, and concrete; there are also engine/tool materials such as `TOOLS/TOOLSTRIGGER`, `TOOLS/FOGVOLUME`, and `TOOLS/TOOLSSKYBOX` that should not be mistaken for normal wall textures.
- Python's ordinary `zipfile` reports `Corrupt extra field 0e00 (size=24781)` for the local `zip0.360.zip`. This does **not** prove the archive is corrupt.

**New tool:** `tools/inspect_xbox_zip.py`. This reads ZIP end-of-central-directory and fixed central-directory records, skips per-entry extra field bytes without decoding them, and never reads or extracts entry payloads. `tools/inspect_map_materials.py --pack` automatically tries it if the standard ZIP library refuses the archive.

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\inspect_map_materials.py --pack
```

The new inspector is supported by synthetic ZIP tests but **has not yet been tried on the user's console archive**. Matching `.vmt` names in a ZIP still does not validate the VTFX image payload format or mean texture rendering works.

## ZIP central directory misalignment investigation

The second owner run used the new ZIP fallback and reported:

    Standard ZIP reader rejected extra data: Corrupt extra field 0e00 (size=24781)
    Xbox ZIP directory probe also stopped: Invalid central header at entry 1

The archive may have padding, console-specific central metadata, or a different directory layout. **The cause is not established.** We should not blindly scan/extract payload data or invent a successful match.

The helper now provides a bounded diagnostic that reads only fixed header fields and at most 8192 bytes near the failed central directory offset:

    git pull
    py -m unittest discover -s tests -v
    py tools\inspect_xbox_zip.py --diagnose

Separately, one Windows ISO extraction unit test compared the short Windows 8.3 path against a resolved long path; its expectation has been corrected. This did not involve any ISO data or game extraction.

## October 26 ZIP directory alignment evidence

The read-only diagnostic confirmed:

- EOCD offset: **1,083,750,400**
- Directory size: **2,355,200** bytes
- Declared central records: **24,435**
- First record: filename 21 bytes, extra field 1,997 bytes, file comment 0 bytes.
- Expected second header: **1,083,752,464**, but actual bytes are zeros.
- First plausible next central header: **1,083,752,522**, a **+58 byte** gap.

The standard ZIP specification uses variable-length filename, extra field, and comment sections. This diagnostic suggests an unusual directory gap or console-specific alignment, but **does not yet prove why**. The new reader scans at most **128 bytes** forward *within the confirmed central directory*, requires structurally plausible central headers, and counts recovered gaps. It does not parse or extract compressed file payloads. If it encounters more than 128 unknown bytes, it refuses to guess.

    cd C:\Users\FrontDesk\LFD2
    git pull
    py -m unittest discover -s tests -v
    py tools\inspect_map_materials.py --pack

Results for the real archive are still pending. Avoid claiming full support until the reader successfully validates and counts its entries.

## New: independent Xbox ZIP central-directory scan

The latest Windows run passed **51/51 tests**. The safe sequential Xbox ZIP reader advanced to entry **1,470** before refusing a header near the end of the directory. However, the EOCD declares **24,435 records in 2,355,200 bytes** (~96 bytes/record), which is incompatible with trusting many oversized "extra length" values to step between records.

Instead of widening the 128-byte gap allowance, we've added [tools/scan_xbox_zip_directory.py](tools/scan_xbox_zip_directory.py). It scans only the **EOCD-bounded central directory** for PK central signatures, validates fixed header and filename bounds, and reports how many plausible candidates exist, including potential VMT/VTFX paths. It **never reads compressed game file data**. Synthetic tests are committed; the scanner is not yet verified on the owner's Xbox archive.

    cd C:\Users\FrontDesk\LFD2
    git pull
    py -m unittest discover -s tests -v
    py tools\scan_xbox_zip_directory.py

Share only the printed metadata report. Candidate filenames are a diagnostic, not proof of successful archive decoding.


## Latest confirmed archive index and next research step

The owner's new 55-test run and independent raw scan give **24,435 / 24,435 plausible central headers** in \`zip0.360.zip\`, with zero rejected candidates. The very large "extra-length" values cause 24,434 **declared-span overlaps** when interpreted as ordinary ZIP extra fields. Consequently, our earlier sequential parser's reported "+58-byte gap" was **not a reliable physical gap**; it skipped genuine intervening directory headers.

\`zip0.360.zip\` appears to hold primarily audio and models and contained no apparent \`.vmt\` filenames in this raw scan. Modding research indicates \`zip1.360.zip\` is likely to hold console-format textures.

**Use the all-pack scanner now instead of the old sequential ZIP reader:**

\`\`\`powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\scan_source_asset_packs.py --include-map-pak
\`\`\`

It checks all eight \`.360.zip\` files and optionally the embedded hotel BSP PAKFILE lump 40. The script is metadata-only, looks for \`materials/\` paths and common VTFX-related file suffixes, and compares filenames to the BSP's 189 hotel material names. Results from the real asset packs still need to be observed. See [XBOX_PACK_DISCOVERY.md](XBOX_PACK_DISCOVERY.md).

## Next engineering milestones

1. Verify Source texture-name paths and matching material files in the console archives or BSP pakfile.
2. Determine whether textures use ordinary PC VTF, console VTFX, or some other payload format. Do not assume \`.vtf\` is PC-compatible on Xbox.
3. Write a **local** texture/metadata converter for formats actually encountered. It must use only locally owned inputs and keep decoded output under \`research/local/\`.
4. Export mesh UV coordinates and per-face material IDs. The current simple mesh deduplicates positions and does not yet contain texture coordinates, so adding JPG/PNG files alone will not texture the walls properly.
5. Update WebGL2 to bind original material textures/atlases, then add static props, displacements and collision.

**No third-party game assets or decompiled code belong in the public repository.** Copyrights and license restrictions must be respected. Even successfully rendered original textures would still be only a level viewer, not a full browser game engine.

## References

- [Valve Source SDK 2013 — bspfile.h](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/public/bspfile.h) (BSP lump IDs/structures)
- [ValveBSP lump reference](https://pysourcesdk.github.io/ValveBSP/api/lumps.html)
- [Community research on Xbox 360 VTFX and 360.zip formats](https://open-source-modding.github.io/docs/left4dead/left4dead-formats/) (background only; variants must be validated locally)
