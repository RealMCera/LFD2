# Ghidra setup for the Left 4 Dead 2 Xbox 360 executable

## Status and scope

The owner extracted a **786,432-byte** basefile from `default.xex` with xex2ool. The local inspector verified a **PE32, PowerPC FP (0x01F2)** executable with six sections. The PE's entry address **0x82010CB8** matches the original XEX. XEX encryption is normal, with basic compression.

**This is not yet a decompilation.** The following steps verify the PE structure, install matching Ghidra components, and open the executable for analysis.

## 1. Validate the local basefile

In PowerShell, in `C:\Users\FrontDesk\LFD2`:

```powershell
git pull
py -m unittest discover -s tests -v
py tools\inspect_pe.py
```

The inspector prints only PE header fields and section metadata, not code. Compare the reported image base and entry address with the XEX metadata:

- XEX load address: `0x82000000`
- XEX image size: `0x000C0000`
- XEX entry point: `0x82010CB8`

If the PE and XEX entry addresses disagree, record that fact rather than assuming the PE is corrupted.

## 1b. Confirm where the rest of the game code lives

The recovered PE has a `.text` virtual size of only **32,872 bytes**. That is unexpectedly small for a whole modern game engine. We must not imply the file contains all the game's functions. Run:

```powershell
py tools\summarize_extract.py
```

Review other extracted files and possible code-bearing containers before assuming whole-game decompilation is possible from this XEX alone.

The PE reports `SizeOfImage = 0x40200` versus XEX image size `0xC0000`. These are **different fields** and may include Xbox-specific packaging or mapped resources; record the mismatch but do not treat it alone as a parsing failure.

## 1c. Game modules discovered

The inventory confirms that **21 DLL-named files are also XEX2 executable modules**. In addition to the launcher, priority targets include server_360.dll, client_360.dll, and engine_360.dll. See [MODULE_MAP.md](MODULE_MAP.md) for the exact local extraction and inspection commands. Their code and architecture have not been examined yet.

## 2. Install a **matching** Ghidra and Xbox 360 loader pair

Choose these versions specifically for compatibility:

1. Install **64-bit JDK 21** (Temurin/Adoptium is a suitable provider). In PowerShell, run `java -version` and check that Java 21 is available.
2. Download **Ghidra 12.1.3** from its [official release](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.3_build). Download the compiled Ghidra ZIP under Assets, **not** the automatically generated GitHub source code archives. Extract to a convenient local folder. Launch `ghidraRun.bat` inside that folder.
3. Download the **XEXLoaderWV 12.1.3** extension ZIP from its [matching upstream release](https://github.com/zeroKilo/XEXLoaderWV/releases/tag/12.1.3). Keep the extension as a ZIP; do not confuse it with a source-code ZIP.
4. In Ghidra, use **File → Install Extensions → add (+)** and select the XEXLoaderWV release ZIP. Enable it if needed, apply the change, then restart Ghidra.
5. Create a new **Non-Shared Project**, stored **outside the Git repository** (for example `Documents\L4D2-Ghidra`).

A newer Ghidra version may be available, but the XEXLoaderWV **12.1.3** ZIP is explicitly built for Ghidra 12.1.3. **Do not mix Ghidra 12.2 with an extension built for 12.1.3** unless upstream documents compatibility.

## 3. Import an original XEX2 module, not its exported basefile (recommended)

In the Ghidra project, choose **File → Import File**. After verifying that it can decode successfully, prioritize:

`C:\Users\FrontDesk\LFD2\game-extracted\left4dead2\bin\server_360.dll`

The previous `default.xex` can also serve as a small first loader-validation target.

The Xbox 360 loader should recognize the `XEX2` signature and propose a PowerPC big-endian language such as `PowerPC:BE:64:A2ALT-32addr`. If Ghidra only offers a raw-binary loader, stop and verify that XEXLoaderWV was installed and enabled.

Confirm base load `0x82000000`, entry `0x82010CB8`, and import libraries `xam.xex`, `xboxkrnl.exe`, if displayed. In the import options, allow `.pdata` function discovery if the option is present. If loading succeeds, accept default analysis options as a starting point and navigate to the entry address.

Do not invent a fake `.pdb` or `.xdb`; none was provided, so leave symbol-loading options disabled.

**Alternative:** use `research/local/default.basefile` if a PE loader is compatible and you have confirmed the correct image base and PowerPC architecture. The original XEX is preferable since the XEX-specific loader can use its metadata and imports.

## 4. What to record first

Record only non-proprietary facts in the repo (not Ghidra project files or copied game code):

- Ghidra version and extension version, loader name, architecture
- import success or exact error
- memory base and entry point
- section names/sizes and function count reported by Ghidra
- whether the entry point decompiles into sensible control flow
- compiler/loader assumptions and unresolved warnings

The recommended first investigation is the loader startup and import thunks; identify which other game modules, if any, are invoked. The small code section is a reason to check the scope. Do not expect the original Source engine C++ project, assets, or a buildable game to appear automatically.

## Confirmed metadata from xex2ool

- File: `game-extracted/default.xex` (757,760 bytes)
- Basefile: `research/local/default.basefile` (786,432 bytes; MZ signature)
- Title ID: `454108D4`; Media ID: `0E79403B`
- Encryption: normal; compression: basic
- Load address: `0x82000000`; entry point: `0x82010CB8`
- Image size: `0x000C0000`
- One resource: name `454108D4`, address `0x82021080`, size `0x9A6F0`
- Imported libraries: `xam.xex` v2.0.9328.0 (7), `xboxkrnl.exe` v2.0.9328.0 (43)

**Additional PE verification:** PE32, PowerPC FP (0x01F2), six sections, entry RVA 0x10CB8, image base 0x82000000, PE SizeOfImage 0x40200, text section 32,872 bytes. All nine synthetic tests passed. No functions have yet been decompiled.

**Keep all original and decrypted game files on your computer, not GitHub.**
