# Left 4 Dead 2 Xbox 360 — XEX analysis

## Verified state (October 23, 2026)

The owner successfully extracted `game-extracted/default.xex`. Our Python header inspector reported:

- Format **XEX2**, size **757,760 bytes**, 16 optional headers
- Title ID `454108D4`, Media ID `0E79403B`
- Encryption **1: normal (encrypted)**
- Compression **1: basic**, NOT normal/LZX
- All five header-inspector unit tests passed

The original XEX is still encrypted. The header report alone does **not** mean machine code can yet be disassembled.

## Next workflow: use xex2ool locally

`xex2ool` is an independently maintained open-source XEX2 analysis CLI. It documents `info`, `imports`, and `basefile` commands:

- Project and usage: https://github.com/landaire/acceleration/blob/main/crates/xex2ool/README.md
- Official release builds: https://github.com/landaire/acceleration/releases

### 1. Get the Windows CLI

Download a Windows binary from an official release (not a random file mirror), unzip it and place `xex2ool.exe` in `LFD2\tools\bin\`. Create `tools\bin\` if necessary. That directory is ignored by Git. Alternatively add the executable to PATH, or supply `--tool` and its full local path.

### 2. Run metadata inspection first

In PowerShell, with your terminal in `C:\Users\FrontDesk\LFD2`:

```powershell
git pull
py tools\prepare_xex.py
```

This runs the external tool's `info` and `imports` commands on your original `game-extracted\default.xex`, without modifying it or writing a basefile.

If your `xex2ool.exe` is elsewhere:

```powershell
py tools\prepare_xex.py --tool "C:\Full\Path\To\xex2ool.exe"
```

Share the info/import summary as console text. Review it for private keys or similar secrets first; never share any keys or decrypted executable bytes.

### 3. Generate a local basefile after successful inspection

```powershell
py tools\prepare_xex.py --extract
```

This calls `xex2ool basefile` and writes the result under `research/local/default.basefile`. No files are sent over the network by our Python helper. The original XEX remains untouched. Output must not already exist; the script refuses to overwrite files.

The script prints the new file's **size** and **first 16 bytes**. If it begins with `MZ`, it may be a PE image; otherwise, identify the representation before importing it into a disassembler. Even a PE-like image can require Xbox-specific memory mapping and import handling.

## Later: Ghidra (PowerPC)

- Ghidra official releases: https://github.com/NationalSecurityAgency/ghidra/releases
- Xbox 360 XEX loader: https://github.com/zeroKilo/XEXLoaderWV
- Prefer a loader build confirmed compatible with the Ghidra version you install; check the loader's release notes.
- The reverse-engineering process involves mapping code and data sections, resolving imports, determining function boundaries, and independently documenting subsystems. Decompilation output is **not original C/C++ source** and will need extensive work to become buildable.

Keep the original XEX, any decrypted basefile, game assets, and disassembler project files local. Do not publish them to this public repo.
