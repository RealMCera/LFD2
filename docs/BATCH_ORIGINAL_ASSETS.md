# Automated original Xbox hotel model pipeline

The first chair was a binary-format proof of concept. It is **not** the intended workflow for every object.

## Run one batch for every model referenced by the hotel

On Windows PowerShell:

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\build_hotel_scene_bundle.py --run
```

The importer reads the existing ignored `research/local/hotel-all-props.json`,
scans the original local Xbox archive once, matches the 228 unique model
references, converts supported original MDL/VVD/VTX assets, and writes a
private `research/local/hotel-auto-props/` folder containing `scene.json`
plus an individual mesh JSON for each successfully decoded model.

It preserves all 2,164 authored positions in the original manifest; the
batch scene includes positions only for models decoded successfully.
Malformed/unsupported model files are skipped with reasons in scene.json.
The command processes all supported models, rather than stopping on
the first unsupported chair, door, lamp, table, or prop.

Already existing output folders are not overwritten. Repeat with an unused
`--output research/local/hotel-auto-props-2` when rebuilding later.

## One folder selection in Chrome

1. Open `docs/map-viewer.html` and choose the original hotel `.mesh.json`.
2. Under **ALL ORIGINAL HOTEL MODELS · ONE FOLDER**, click
   **LOAD ENTIRE HOTEL AUTO-PROPS FOLDER**.
3. Select `research/local/hotel-auto-props` once. Press **B** to jump
   between loaded model types, or explore normally with WASD.

Chrome uses WebGL2 GPU instancing to reuse the model's original geometry
across all occurrences. It bounds rendering cost and reports skipped
model formats; no placeholder geometry is invented.

Existing single-chair controls are optional debug tools and no longer
part of the routine workflow.

## What remains

This is an automated original-asset import pipeline, not a playable
Left 4 Dead 2 port. The complete game still requires portable Source
engine/gameplay implementation, original animations, AI, physics,
scripts, audio and faithful material rendering. Generic fixes to shared
formats benefit many assets; do not debug every model individually.

All original commercial assets remain under gitignored `research/local/`.
Neither source game data nor generated original meshes are uploaded to GitHub.

## October 27 first full Xbox hotel batch — owner-verified

The first one-command Windows batch completed successfully with **228/228**
original hotel model references inspected; **96** Source model types
converted to `research/local/hotel-auto-props` and **132** skipped
with machine-readable reasons. The resulting private `scene.json` includes
**1,022 of the original 2,164 prop placements** (47.2%). No original assets
were committed to GitHub. This does not mean all 96 are visually confirmed
in Chrome yet; folder-import verification is next.

For the next iteration, **do not repeat the full export**. The private
folder already exists and the converter refuses overwrites. Run the new
read-only diagnosis on the existing output:

```powershell
git pull
py tools\report_hotel_scene_bundle.py
```

It groups the 132 rejected model types by generic decoder failure and
ranks each family by how many originally placed hotel objects it affects,
using the original private placement manifest. This guides shared
format fixes instead of manual per-object conversions.

For the Chrome preview, load the same original hotel UV map as before,
then choose the entire `research/local/hotel-auto-props` folder using
**LOAD ENTIRE HOTEL AUTO-PROPS FOLDER** in the map loader.

## Browser batch-import visual confirmation

October 27 user screenshot confirms the existing local `hotel-auto-props`
bundle was loaded with the original hotel BSP in Chrome. Multiple original
prop forms (including debris and other hallway objects) visibly appear,
the NEXT MODEL control is active, and the user's original BSP texture folder
continues rendering 53 map materials. This confirms the batch loader is
functional, **not** that every supported model's shading, orientation,
skin, animation or placement has been fully verified.

Next shared improvements: use `py tools\report_hotel_scene_bundle.py`
on the existing scene report to find failures with the largest number
of affected original instances, then add model material/texture binding
at the studio-format level. No per-object manual conversion needed.

## Shared 132-model issue: Xbox LZMA no-EOS one-byte overflow

The October 27 owner-side report found that **all 132 skipped model types**
(affecting **1,142 original hotel prop references**) failed at the same
Valve LZMA decoding stage. Example errors include 'expected 1740 bytes;
got 1741', 'expected 19281 bytes; got 19282', and
'expected 92202 bytes; got 92203'. This suggests a Source Xbox studio
raw-LZMA range coder that produces one surplus trailing byte without
an end-of-stream marker. This has not yet been verified against every
original model after the change.

The central decoder now has an **explicit studio-only compatibility option**
for precisely that condition. It accepts the declared uncompressed length
only when the output is exactly one byte longer, the LZMA end marker is
absent, and the compressed member occupies the full wrapper payload.
The normal map/BSP LZMA path remains strict. Studio MDL/VVD/VTX
callers opt in, and the existing Source-version, MDL/VVD/VTX checksums,
vertex bounds and strip-index validation remain mandatory.

Regenerate the scene into a **new private folder**, because the original
`hotel-auto-props` output is intentionally preserved and cannot be overwritten:

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\build_hotel_scene_bundle.py --run --output research\local\hotel-auto-props-v2
```

Then choose `research/local/hotel-auto-props-v2` in the Chrome viewer's
**LOAD ENTIRE HOTEL AUTO-PROPS FOLDER** picker. Do not delete or
re-upload the v1 folder. The first owner run of this decoder modification
is still pending; success is measured by real decoded model and placement
counts and a browser visual check, not by an assertion that all 228
models are automatically recovered.

## Verified 100% original studio geometry conversion, October 27

The owner's new local batch status is **228 attempted, 228 decoded,
0 skipped, 2,164 original placements included out of 2,164 total**.
The earlier first-pass 96/228 coverage is preserved in v1; the v2 output
is private under `research/local/hotel-auto-props-v2`.

The upcoming visual bottleneck is model materials and original Source skin
mapping, not missing referenced model meshes. The new
`tools/inventory_hotel_studio_materials.py` uses one safe, read-only pass
to catalog the original Source v49 MDL material-table names, CDTexture
search paths and skin family mappings for all hotel referenced model types.
This inventories paths only: it does not pretend to resolve original
material images, nor change the working v2 scene.

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\inventory_hotel_studio_materials.py
```

Optional `--export` creates an ignored local metadata catalog without
overwriting. The next shared pipeline stage should resolve exact VMT
material paths and associated Xbox VTFX images, then use mesh material
IDs + studio skin tables to render faithful model textures across the hotel.

## October 27: verified MDL material headers and automatic original VMT/VTFX matching

The owner's Windows run passed **172 synthetic Python tests** and
scanned **228 original hotel models**. Material names and skin-family tables
parsed for **223**, with **5 checkpoint-door family MDLs** rejected at
the material-name validation stage. There are **268 candidate material
paths**, not yet 268 physically verified Xbox texture images.

The next stage, `tools/resolve_hotel_studio_textures.py`, is a single
read-only model-material pass. It reuses the original model catalog
and existing stored VMT/BSP-pak/Xbox ZIP readers. A match requires the
original studio candidate material's **exact VMT path**, that VMT's
`$basetexture`, and an **exact original Xbox VTFX path**. It reports
unresolved/missing/ambiguous slots rather than selecting near matches.

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\resolve_hotel_studio_textures.py
```

The optional `--export` saves material-asset reference metadata only in
`research/local/hotel-studio-texture-matches.json`, not game textures.
Existing `hotel-auto-props-v2` geometry remains untouched. The next
separate implementation milestone is batching original VTFX conversion
and assigning decoded PNGs by original model mesh/skin material IDs.

## October 27: Xbox material contents not yet decoded — shared VMT diagnostic

The owner-side exact-match resolver passed all five isolated Python tests
and scanned **393 original Source studio material slots**: **zero** had
a verified VMT `$basetexture` plus an original VTFX link.
**388 slots** had a VMT source entry, but its bytes yielded no usable
`$basetexture`; five had missing/ambiguous VMT source names.
This is not evidence that all those textures are absent. The current
VMT parser assumes uncompressed, plain-text Source KeyValues,
while the actual Xbox payload encoding remains unverified.

Use the new `tools/diagnose_hotel_vmt_payloads.py` to inspect a
few bounded byte signatures across all original referenced VMT files
in **one read-only pass** (no extraction or game uploads):

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -p "test_diagnose_hotel_vmt_payloads.py" -v
py tools\diagnose_hotel_vmt_payloads.py
```

The report distinguishes likely binary, NUL-heavy, LZMA-wrapped and
ordinary-text materials and shows just file names, short hex prefixes,
byte ratios and parser flags. It also separately reports direct same-name
VTFX filename *candidates*, without pretending those are verified
shader material bindings. Once the format is established, implement
a shared decoder and retry exact matching, then batch texture conversion.

## October 27: original Xbox material scripts are binary — provisional whole-hotel texture preview

The owner's read-only diagnostic successfully inventoried **257**
original VMT scripts. Example material bytes start with
`AA 4F F4 D8`, including 25-byte metal-door/ceiling files and
52-byte infected apparel files. These are neither plain-text VMT
scripts nor Valve LZMA-wrapped materials according to the byte check;
the exact proprietary Xbox compiled material encoding is **not decoded**.

The same scan found **219 material slots** with an independently exact-name
VTFX filename candidate, covering **2,340 slot × placement references**
(not 2,340 distinct props and not a verified shader binding).
Generic names, similar-name heuristics, and manual one-by-one conversions
are **not** used.

To make visual progress without inventing shader parameters, the
`tools/build_hotel_model_texture_candidates.py` pipeline requires:

- A valid original studio MDL material path from the existing batch inventory
- A unique exact-name VMT archive entry with the *observed* Xbox binary prefix
- A unique exact-name original Xbox VTFX image file; VTFX headers validated by the existing converter

The first command runs read-only and prints prospective count. The second
converts original VTFX files into a **new private directory**; it does
not touch `research/local/hotel-auto-props-v2`. The converter uses your
existing offline `research/local/tools/vtfx_reader.exe`, never downloads
anything or commits commercial assets:

```powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\build_hotel_model_texture_candidates.py
py tools\build_hotel_model_texture_candidates.py --run
```

If the default output folder already exists, choose a new folder via
`--output research/local/hotel-model-textures-v2`. Outputs remain ignored
by Git in `research/local`.

### Chrome: two folders total, not hundreds of assets

1. Load original hotel BSP as before and choose
   `research/local/hotel-auto-props-v2` once using the original model folder button.
2. Using **LOAD ALL PROVISIONAL ORIGINAL MODEL TEXTURES · ONE FOLDER**,
   choose `research/local/hotel-model-textures-v1` once. The viewer
   uses original model UVs and per-triangle studio material IDs with
   WebGL2 instancing; missing/unsupported image slots stay diagnostic colored.

**IMPORTANT:** Original material shader assignments, transparent/blended
rendering, skin-family choices, animations, and full game logic are still
unfinished. These textures are a *provisional exact-filename visual preview*,
not a verified reproduction of the binary Xbox VMT parameter tree.
