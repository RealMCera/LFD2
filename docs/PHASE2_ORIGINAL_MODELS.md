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

The inspector reports total entity classes and example coordinates, Source GAME_LUMP version/flags, static model dictionary and static prop count if safely recognized, and displacement metadata sizes. It does not write game data or perform unsafe model decoding. The owner has not yet run this new inspector on the actual Xbox hotel BSP.

Valve Source BSP source reference: https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/public/bspfile.h
Source static-prop version caution: https://srctools.readthedocs.io/en/stable/modules/bsp.html
