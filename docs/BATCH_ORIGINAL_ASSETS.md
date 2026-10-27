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
