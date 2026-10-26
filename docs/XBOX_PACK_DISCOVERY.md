# Locating original L4D2 Xbox 360 materials: archive index survey

## Verified owner results — October 26, 2026

The extracted Xbox Dead Center hotel BSP is a big-endian Source BSP v20 and produces **27,374 brush triangles** in Chrome. Its original BSP material references resolve to **189 distinct names** over **10,840 mapped faces**, including \`PLASTER/PLASTER_INT_14\`, \`TILE/TILE_CEILING_01\`, and \`CONCRETE/CONCRETE_FLOOR_10\`.

For \`left4dead2/zip0.360.zip\`:

- ZIP EOCD reports **24,435** central entries.
- Independent scanning found **24,435 PK central-header signatures**, all structurally plausible, with no rejected candidates.
- The directory is **2,355,200 bytes**. An average central entry is about **96 bytes**.
- Standard ZIP extra-length fields are typically around 1,960 bytes, which makes consecutive *declared spans* overlap. These are not ordinary ZIP extra fields in the sense assumed by the old sequential reader.
- The previous "58-byte gap" was a side effect of trusting those lengths and jumping over other valid headers. **Do not use a 58-byte alignment rule** or bulk extraction on this basis.
- This archive's dominant file extensions are \`.wav\` (11,264), \`.mdl\` (3,211), \`.vvd\` (3,182), \`.vtx\` (3,182), and \`.phy\` (2,383). The independent scan found no apparent \`.vmt\` paths in \`zip0.360.zip\`.

This is strong evidence that the *directory filenames* are recoverable. It does **not** yet prove its local file offsets, member content, or texture decoding work.

## Most promising next target

Xbox 360 L4D2 modding references say custom Xbox VTFX textures are normally stored in **\`zip1.360.zip\`**, with the \`.360\` extension used by Xbox-format texture files. That's a promising lead, not a guarantee about the owner's particular archive.

- [L4D2 Xbox texture converter notes](https://www.xpgamesaves.com/resources/l4d2-tf2-pc-to-xbox-texture-conversion-tool.4813/)
- [L4D1/2 VTFX and 360.zip archive research](https://open-source-modding.github.io/docs/left4dead/left4dead-formats/)

## Safe all-pack material scan

\`\`\`powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\scan_source_asset_packs.py --include-map-pak
\`\`\`

The scanner checks **all eight \`*.360.zip\` files** in \`game-extracted\`, then optionally the hotel's embedded BSP PAK lump 40. It reads only EOCD-bounded ZIP central-directory metadata and original BSP material-name metadata. No game archive member bodies are opened or extracted.

For each pack it prints:

1. Declared file count versus plausible recovered header count.
2. Reported file extensions, especially \`.vmt\`, \`.vtfx\`, \`.vtf\` or \`.360\`.
3. Number of filenames beneath \`materials/\`.
4. Candidate filename matches for the 189 hotel material IDs, accepting common \`.vmt\`, \`.vtf\`, \`.vtfx\`, \`.vtf.360\`, and \`.360\` suffix patterns.
5. A small selection of filenames (metadata only).

**Current status:** This new multi-pack script and its synthetic tests are committed but haven't yet been executed on the user's extracted archives.

## Next actual rendering work

Once we've confirmed the relevant archive, implement *local-only* file-body extraction and validate the first texture's file signature / format. We should not assume any entry can be safely decompressed merely because its name and central directory look valid.

The Source BSP face \`texinfo\` and \`texdata\` tables must next be converted to **per-vertex UV coordinates and per-face material IDs**. The existing browser mesh contains only 3D positions and triangle indices, so attaching image files without those changes would not render real textures correctly. No proprietary textures or game data should be committed to public GitHub.

## Owner-confirmed discovery and subsequent header probe

The latest all-pack scan (59/59 synthetic tests passed) located the hotel's **real material filenames** in two archives:

| Local archive | Total central candidates | VMT | VTF | Candidate matching hotel material IDs | Corresponding face references |
|---|---:|---:|---:|---:|---:|
| \`left4dead2/zip1.360.zip\` | 8,565 | 4,640 | 3,922 | 69 | 10,315 |
| Hotel BSP lump 40 embedded PAKFILE | 1,628 | 217 | 85 | 120 | 525 |
| Combined reported matches | — | — | — | **189** | **10,840** |

All eight external archive directories plus the embedded map PAK directory were scanned successfully. The console packs include names like \`materials/ads/burger.360.vtf\`, while the BSP PAK includes per-map materials such as \`materials/maps/c1m1_hotel/buildings/... .vmt\`. Multiple archives contain nonstandard ZIP extra-length fields; directory candidate counts can differ slightly from EOCD counts. These are read-only filename candidates, **not yet proof of valid extractable texture bodies**.

**New tools for the next local validation:**

\`\`\`powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\scan_source_asset_packs.py --include-map-pak
py tools\probe_xbox_texture_headers.py --include-map-pak
\`\`\`

The first tool now computes **exact unique coverage and overlap across all packages**, so it can verify whether the 69+120 equals 189 without duplication. The second reads only the central metadata, local ZIP headers and a 16-byte candidate payload signature per selected texture. A \`VTFX\` signature would be strong evidence about the Xbox texture format. A missing \`PK 03 04\` local header would mean the archive requires extra Xbox-specific offset decoding; it should not be blindly extracted.

The current Chrome renderer still lacks original image decoding, per-triangle UV/material attributes, and correct draw batching. We must implement all of those before the walls can display original textures. The player's local original game assets must remain untracked and never be committed to the public repo.


## First genuine VTFX signatures (owner validated)

The next PowerShell run passed **66 tests** and reported **189/189 unique material filename matches, 10,840/10,840 faces, 0 duplicated IDs and 0 missing IDs** across the Xbox archives and the hotel's PAKFILE.

All **10 sampled original texture files** reported a matching local ZIP filename and an authentic \`VTFX\` signature (\`56 54 46 58 00 00 03 60\`). Selected examples from \`left4dead2/zip1.360.zip\`:

- \`materials/plaster/plaster_ext_20.360.vtf\`, 174,844 bytes
- \`materials/tile/tile_ceiling_01.360.vtf\`, 174,844 bytes
- \`materials/plaster/plaster_int_14.360.vtf\`, 174,844 bytes
- \`materials/plaster/plaster_int_15.360.vtf\`, 174,844 bytes

The embedded PAK also had VTFX signatures for 5 map-specific \`materials/maps/c1m1_hotel/*.hdr.360.vtf\` files.

**Next:** inspect the actual big-endian VTFX dimensions/format and safely copy **one** original file into ignored \`research/local/vtfx/\` via \`tools/extract_single_vtfx.py\`. See [VTFX_FIRST_TEXTURE.md](VTFX_FIRST_TEXTURE.md). For image conversion, see [rob5300/vtfx_reader](https://github.com/rob5300/vtfx_reader), which documents Xbox image endianness repair and several compatible formats.

