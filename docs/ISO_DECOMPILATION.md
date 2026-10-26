# Xbox 360 disc ISO to private XEX analysis

## Status and limitations

The owner's full Left 4 Dead 2 Xbox 360 ISO is 7,838,695,424 bytes. **Its actual XDVDFS header and local extraction have now been confirmed (October 26, 2026)**: XGD2 format, partition offset 265,879,552, 24 BSP map files, 21 DLL-named candidate modules, the root default.xex, and eight Xbox ZIP-named resource archives. The extraction wrapper reported "Verified: default.xex exists in extracted root." The 21 DLL-named files still require independent XEX2 header inspection; the ISO's build and binary identity versus the earlier ZArchive have **not** been verified.

This pipeline adds a **read-only XDVDFS header probe** supporting standard XISO, XGD1, XGD2 and XGD3 game-partition offsets; optional **local extraction** through the external xdvdfs CLI; the existing PowerPC XEX2 metadata tools; and an optional **Ghidra Jython decompiler exporter**, writing pseudocode privately.

A decompiled function is not original C++ source. None of this automatically produces a working game or browser port.

## 1. Download the image to Windows

Download your ISO from your private Google Drive to the Windows machine that holds the repository, for example D:\Games\L4D2.iso. Keep the entire image on your own computer and allow substantial additional disk space for its extracted files.

Do not commit the ISO or extracted files. Both ISO images and game-iso-extracted/ are ignored by Git.

## 2. Inspect its disc layout without extracting

In PowerShell:

~~~powershell
cd C:\Users\FrontDesk\LFD2
git pull
py -m unittest discover -s tests -v
py tools\import_disc_iso.py "D:\Games\L4D2.iso"
~~~

The tool seeks to known XDVDFS volume-descriptor offsets and reports layout, root directory bounds and ISO size. It reads only a few 2 KiB sectors. For the owner's actual ISO, this inspection **passed** and reported an XGD2/XDVDFS volume descriptor with a 2,048-byte root directory.

If the probe says the volume descriptor is missing, do not guess the layout from the filename.

## 3. Extract with xdvdfs (locally only)

Get the **Windows xdvdfs CLI binary** from [antangelo/xdvdfs releases](https://github.com/antangelo/xdvdfs/releases). Add it to your PATH or provide its full filename:

~~~powershell
py tools\import_disc_iso.py "D:\Games\L4D2.iso" --extract

# When xdvdfs is not on PATH:
py tools\import_disc_iso.py "D:\Games\L4D2.iso" --extract --xdvdfs "C:\Tools\xdvdfs.exe"
~~~

The default output is game-iso-extracted/, **not** the earlier archive's game-extracted/. The wrapper refuses nonempty extraction directories. The xdvdfs CLI does the actual unpacking; our Python tool is not a filesystem extractor. If xdvdfs cannot read this disc, save the exact error.

**Completed:** xdvdfs successfully extracted the owner's ISO to game-iso-extracted/ and the script verified default.xex at the root. **Do not re-run --extract against that existing folder**: the tool intentionally refuses nonempty destinations. Do not upload anything from this directory to GitHub.

## 4. Inventory the executable modules

~~~powershell
py tools\catalog_modules.py game-iso-extracted
py tools\inspect_xex.py "game-iso-extracted\default.xex"
py tools\compare_xex_modules.py
~~~

Look for code-bearing XEX2 modules such as left4dead2/bin/server_360.dll, left4dead2/bin/client_360.dll and bin/engine_360.dll, **if present**. The previous extracted archive had 22 XEX2 modules. The ISO extraction log includes the launcher plus 21 DLL-named candidate modules, but their XEX2 headers still need validation. The comparison script checks both local extracts by XEX2 magic and compares matching files byte-for-byte via streaming SHA-256. It never uploads game data. Modules named DLL can still contain Xbox 360 XEX2 binaries rather than standard Windows DLLs.

The existing tools/prepare_xex.py and tools/inspect_pe.py can decode and inspect selected modules locally. Use fresh paths under research/local/ for ISO-specific results; do not overwrite earlier archive research.

## 5. Perform private Ghidra function decompilation

Follow [GHIDRA_SETUP.md](GHIDRA_SETUP.md) to install matching Ghidra and Xbox-aware XEXLoaderWV versions and make a Ghidra project **outside the Git repository**.

Import the **original** ISO-extracted server_360.dll using the Xbox 360 XEX loader, then allow automatic analysis to finish. Verify its memory base, imports and entry point; 0x89DED900 belongs to a previous dump and has not yet been verified against the new ISO.

The repo's [ExportPseudocode.py](../tools/ghidra/ExportPseudocode.py) is a Ghidra **Jython** script. Add tools/ghidra/ to Ghidra's Script Manager search paths. Run through Ghidra Script Manager with arguments, or use the headless analyzer with the postScript option. Example script arguments:

~~~text
C:\Users\FrontDesk\LFD2\research\local\server_pseudocode.txt 50
~~~

The first argument is the private output file; the second limits export to **50 analyzed functions**. The optional third argument is a verified start address such as 0x89DED900 (only if that module uses it). The script rejects overwrites, records failures, and depends on Ghidra identifying valid functions.

**The Ghidra script has not been run against the owner's ISO.** Generated pseudocode is imperfect and not automatically buildable; never commit it to this public repo.

## Public source and copyright boundary

The repo can contain original research tooling, independently written behavioral descriptions, tests and other non-proprietary material. Keep commercial game modules, maps, textures, sounds, decrypted binary data and raw decompiler dumps local. Ownership of a game image does not by itself permit redistribution.

A genuine browser port still requires verified portable engine/gameplay code, rendering, physics, AI, input, sound, user-local assets and replacements for Xbox platform services. Exporting functions alone cannot supply all of these.

## Tests

The new ISO tool has nine synthetic tests covering XISO, XGD1, XGD2, XGD3, malformed descriptors, bounds checks, read-only inspection and safe extraction. The real ISO layout and file extraction have been verified against the owner's console log, but module-by-module comparison and Ghidra decompilation still need local verification. Nine additional synthetic tests cover the new module-comparison tool.
