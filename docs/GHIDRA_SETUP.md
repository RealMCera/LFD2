# Ghidra setup for the Left 4 Dead 2 Xbox 360 executable

## Status and scope

The owner has decoded and verified both the small launcher and the larger `server_360.dll`. The **server** basefile is **7,798,784 bytes**, PE32 PowerPC FP, with **7 sections** and **5,740,436 bytes** in its executable `.text` section. Its image base `0x89780000` and entry `0x89DED900` agree with the XEX header. XEX encryption is normal, with basic compression.

**This is not yet a decompilation.** The following steps verify the PE structure, install matching Ghidra components, and open the executable for analysis.

## 1. Validate the local basefile

In PowerShell, in `C:\Users\FrontDesk\LFD2`:

```powershell
git pull
py -m unittest discover -s tests -v
py tools\inspect_pe.py "research\local\server_360.basefile" --expected-xex-base 0x89780000 --expected-xex-entry 0x89DED900
```

The inspector prints only PE header fields and section metadata, not code. The `--expected` flags compare against the **server module**, rather than the launcher. Recorded values:

- Server XEX load address: `0x89780000`
- Server XEX image size: `0x00830000`
- Server XEX entry point: `0x89DED900`

**Completed in the owner's most recent report:** 13/13 unit tests passed and both server address comparisons displayed **MATCH**. If future versions of the files disagree, record that fact rather than assuming the PE is corrupted.

## 1b. Confirm where the rest of the game code lives

The **launcher** PE has a `.text` virtual size of only **32,872 bytes**, but we've now confirmed the `server_360.dll` PE has **5,740,436 bytes** of executable code. The game is split across 22 XEX2 modules. For a repeat local inventory, run:

```powershell
py tools\summarize_extract.py
```

Review other extracted files and possible code-bearing containers before assuming whole-game decompilation is possible from this XEX alone.

The server PE reports `SizeOfImage = 0x850200` versus the XEX image size `0x830000`. These are **different fields**; record their difference but do not assume this alone indicates a problem. The executable's entry RVA `0x66D900` lies inside its `.text` section.

## 1c. Game modules discovered

The inventory confirms that **21 DLL-named files are XEX2 executable modules**. The server has been decoded, while the client and engine remain to be examined. See [MODULE_MAP.md](MODULE_MAP.md) for the latest validated server metadata and the remaining targets.

## 2. Install a **matching** Ghidra and Xbox 360 loader pair

Choose these versions specifically for compatibility:

1. Install **64-bit JDK 21** (Temurin/Adoptium is a suitable provider). In PowerShell, run `java -version` and check that Java 21 is available.
2. Download **Ghidra 12.1.3** from its [official release](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.3_build). Download the compiled Ghidra ZIP under Assets, **not** the automatically generated GitHub source code archives. Extract to a convenient local folder. Launch `ghidraRun.bat` inside that folder.
3. Download the **XEXLoaderWV 12.1.3** extension ZIP from its [matching upstream release](https://github.com/zeroKilo/XEXLoaderWV/releases/tag/12.1.3). Keep the extension as a ZIP; do not confuse it with a source-code ZIP.
4. In Ghidra, use **File → Install Extensions → add (+)** and select the XEXLoaderWV release ZIP. Enable it if needed, apply the change, then restart Ghidra.
5. Create a new **Non-Shared Project**, stored **outside the Git repository** (for example `Documents\L4D2-Ghidra`).

A newer Ghidra version may be available, but the XEXLoaderWV **12.1.3** ZIP is explicitly built for Ghidra 12.1.3. **Do not mix Ghidra 12.2 with an extension built for 12.1.3** unless upstream documents compatibility.

## 3. Import an original XEX2 module, not its exported basefile (recommended)

In the Ghidra project, choose **File → Import File** and select the original Xbox 360 XEX2 container:

`C:\Users\FrontDesk\LFD2\game-extracted\left4dead2\bin\server_360.dll`

The previous `default.xex` can also serve as a small first loader-validation target.

The Xbox 360 loader should recognize the `XEX2` signature even though the filename ends in `.dll`. It should select an appropriate PowerPC big-endian language. If Ghidra only offers raw binary or a Windows PE loader, stop and verify XEXLoaderWV installation and check its load options.

Confirm **server** load address `0x89780000`, entry `0x89DED900`, and imported libraries `xam.xex`, `xboxkrnl.exe`, `tier0_360.dll`, and `vstdlib_360.dll`, if displayed. In the import options, allow `.pdata` function discovery if the option is present. If loading succeeds, accept default analysis options as a starting point and navigate to the entry address.

Do not invent a fake `.pdb` or `.xdb`; none was provided, so leave symbol-loading options disabled.

**Fallback for server analysis:** use `research/local/server_360.basefile` if an appropriate PowerPC PE loader is available and the image base is set to `0x89780000`. Prefer the original XEX2 module because its loader may preserve Xbox-specific imports, metadata, and memory mapping.

## 4. What to record first

Record only non-proprietary facts in the repo (not Ghidra project files or copied game code):

- Ghidra version and extension version, loader name, architecture
- import success or exact error
- memory base and entry point
- section names/sizes and function count reported by Ghidra
- whether the entry point decompiles into sensible control flow
- compiler/loader assumptions and unresolved warnings

The recommended first investigation is the loader startup and import thunks; identify which other game modules, if any, are invoked. The larger server code section makes function-level analysis practical as the next milestone. Do not expect the original Source engine C++ project, assets, or a buildable game to appear automatically.

## Confirmed metadata from xex2ool

- File: `game-extracted/default.xex` (757,760 bytes)
- Basefile: `research/local/default.basefile` (786,432 bytes; MZ signature)
- Title ID: `454108D4`; Media ID: `0E79403B`
- Encryption: normal; compression: basic
- Load address: `0x82000000`; entry point: `0x82010CB8`
- Image size: `0x000C0000`
- One resource: name `454108D4`, address `0x82021080`, size `0x9A6F0`
- Imported libraries: `xam.xex` v2.0.9328.0 (7), `xboxkrnl.exe` v2.0.9328.0 (43)

**Earlier launcher PE verification:** PE32, PowerPC FP (0x01F2), six sections, entry RVA 0x10CB8, image base 0x82000000, PE SizeOfImage 0x40200, text section 32,872 bytes. **Latest server verification:** 13 tests passed and both server address comparisons matched. No functions have yet been decompiled.

**First-function checklist:** After analysis completes, use Ghidra's Go To address action (usually **G**) and enter `89DED900`; inspect whether the disassembly there is recognized as a function, and open the Decompiler pane. Note function count and any warnings. If the expected entry is not mapped, capture the loader error rather than forcing the wrong language.

**Keep all original and decrypted game files on your computer, not GitHub.**
