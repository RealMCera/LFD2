# Executable analysis — starting from default.xex

**Status: archive extracted and one local XEX found; no executable metadata has been reported yet.**

The original Xbox 360 executable is stored locally at `game-extracted/default.xex`, relative to the repository root. Keep the file on your computer; do not upload it.

## Step 1 — update your local clone

From PowerShell in the LFD2 repository:

    git pull

## Step 2 — read the XEX header, no other software required

    py tools\inspect_xex.py

The script uses only Python's standard library and prints XEX2 magic, module flags, offsets, optional-header count, and the execution ID fields (Title ID, Media ID, version, disc number) if available. It does **not** decrypt, unpack, run, disassemble, or modify the file.

If the file isn't at the default location, provide an absolute path in double quotes:

    py tools\inspect_xex.py "D:\\somewhere\\default.xex"

If it reports a non-XEX2 magic, do not force it: inspect and verify the file separately.

## Step 3 — first source-like analysis (later)

- Download Ghidra from its official site: https://ghidra-sre.org/
- An Xbox 360 XEX-aware loader may be required, such as https://github.com/zeroKilo/XEXLoaderWV . Check extension compatibility with your installed Ghidra version.
- Retail XEX code may be encrypted/compressed. A XEX-aware toolchain is often needed before meaningful PowerPC code appears. No decrypted PE basefile is included in this repository.
- Work with original research notes rather than posting proprietary assembly, full decompiler listings, binaries, or extracted game assets.

Sources on XEX layout:
- https://free60.org/System-Software/Formats/XEX/
- https://github.com/xenia-manager/xenia-manager/blob/main/source/XeniaManager.Files/XexFile.cs

## Testing the inspector

    py -m unittest discover -s tests -v

These unit tests use synthetic XEX-like buffers, **not** copies of the game.
