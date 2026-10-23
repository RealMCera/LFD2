# Xbox 360 Left 4 Dead 2 — module map

## Confirmed file inventory — October 23, 2026

The archive contains **96 files**. The owner's extraction inventory found **21 .dll files containing XEX2 signatures**, plus **default.xex**, giving **22 Xbox 360 executable modules**. These DLL-named modules are Xbox 360 executable containers, NOT standard Windows DLL binaries. File sizes below are container sizes, not necessarily amounts of executable code.

| Module | Container size | Hypothesized responsibility |
|---|---:|---|
| left4dead2/bin/server_360.dll | 7,774,208 B | Server-side gameplay, infected AI |
| left4dead2/bin/client_360.dll | 6,823,936 B | Client behavior, interface |
| bin/engine_360.dll | 4,468,736 B | Engine |
| bin/shaderapidx9_360.dll | 2,039,808 B | Graphics |
| bin/GameUI_360.dll | 1,417,216 B | Menus |
| bin/vphysics_360.dll | 1,052,672 B | Physics |
| bin/vguimatsurface_360.dll | 856,064 B | UI surfaces |
| bin/MaterialSystem_360.dll | 827,392 B | Materials |
| default.xex | 757,760 B | Program entry/launcher |

Responsibilities are **working hypotheses based on filenames**. The actual functions have not been examined or decompiled.

Other extracted data includes eight ZIP-named files (2.74 GB), eleven Bink video files (1.65 GB), 24 BSP maps, and supporting assets.

## Inspect all module headers first

Open PowerShell inside C:\Users\FrontDesk\LFD2 and run:

    git pull
    py -m unittest discover -s tests -v
    py tools\catalog_modules.py

The catalog script uses existing local XEX header inspection, including DLL-named Xbox executables. It reports only non-secret metadata and does not write or upload game files.

## Decode and inspect the first gameplay module

Choose the **server_360.dll** module for first-pass game-logic investigation:

    py tools\prepare_xex.py --xex "game-extracted\left4dead2\bin\server_360.dll" --extract --output "research\local\server_360.basefile"
    py tools\inspect_pe.py "research\local\server_360.basefile"

The extracted basefile remains under the Git-ignored research/local directory. If an output file already exists, the preparation script refuses to overwrite it. If extraction fails, capture the error messages and stop rather than guessing a workaround.

After this succeeds, repeat separately for client_360.dll or engine_360.dll as needed. Compare PE image-base, architecture, entry point, and code section size. Use the [Ghidra setup guide](GHIDRA_SETUP.md) to load the original XEX2 module with an Xbox-aware loader, rather than assuming a regular Windows PE loader has the right imports and memory mapping.

## Server module verified — October 23, 2026

The owner successfully decoded and inspected the **server_360.dll** module on Windows:

| Attribute | Observed value |
|---|---|
| Original encrypted XEX2 module | 7,774,208 bytes |
| Local decoded basefile | 7,798,784 bytes (MZ/PE32) |
| Machine | 0x01F2 — PowerPC FP |
| XEX module flags | 0x00000009 — Title, DLL |
| XEX load address / PE image base | 0x89780000 |
| XEX entry point / PE entry VA | 0x89DED900 (**match**) |
| PE entry RVA | 0x66D900 |
| PE section count | 7 |
| PE .text size | **5,740,436 bytes** (about 5.47 MiB) |
| PE .text RVA | 0x170000 |
| PE .pdata size | 151,488 bytes |
| XEX image size | 0x830000 |
| PE SizeOfImage | 0x850200 |
| Import libraries | xam.xex (1), xboxkrnl.exe (49), tier0_360.dll (49), vstdlib_360.dll (9) |

The **PE entry RVA lies within the .text virtual range** (0x170000 to 0x6E9794). There are **108 import entries in total** across the four libraries. The difference between PE SizeOfImage and the XEX image-size field is recorded, not treated as failure.

These are **header-level observations**, not decompiled functions. No Ghidra import has yet been confirmed.

The existing PE inspection script formerly printed the *launcher* address when inspecting the server. This has been corrected with optional module-specific verification:

```powershell
git pull
py tools\inspect_pe.py "research\local\server_360.basefile" --expected-xex-base 0x89780000 --expected-xex-entry 0x89DED900
```

**Do not repeat the basefile extraction**; the local file is already available and the extraction tool deliberately refuses overwrites.

For the first function-analysis step, follow [GHIDRA_SETUP.md](GHIDRA_SETUP.md) and import the **original** `game-extracted/left4dead2/bin/server_360.dll` with XEXLoaderWV. The loader may use XEX-specific imports and metadata unavailable in the standalone PE.

## Later stages

- Locate engine and gameplay functions, interface boundaries, and dependencies.
- Distinguish decompiler-generated pseudocode from actual source.
- Record independently written findings and tests without publishing game binaries or proprietary code.
- Evaluate a reproducible recreation only after substantial function-level analysis.
