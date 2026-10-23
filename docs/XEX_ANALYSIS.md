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

## Confirmed results from the owner's Windows inspection (2026-10-23)

- `default.xex` size: **757,760 bytes**.
- Format: **XEX2**, module flags: `0x00000001` (title module).
- PE payload offset: `0x00001000`; security information offset: `0x00000098`.
- Optional headers: **16**, Execution ID present.
- Title ID: `454108D4`, Media ID: `0E79403B` (verified World-release identifiers).
- Execution version/base version raw: `0x00000003` / `0x00000003`.
- No decryption, unpacked PE, disassembly, or code decompilation has happened.

## Next: identify encryption and compression

The inspector now also reads the XEX2 **Base File Format** optional-header descriptor (`0x000003FF`), when present. It prints the encryption type (none/encrypted) and compression type (none/basic/LZX/delta) without printing keys or extracting proprietary code.

From PowerShell in this repository, run:

    git pull
    py -m unittest discover -s tests -v
    py tools\inspect_xex.py

Share only the new metadata lines starting with `base_file_format_present`, `base_file_format_size`, `encryption_type`, and `compression_type` (or the full brief tool text output).

## Future: Ghidra

- Official releases: https://github.com/NationalSecurityAgency/ghidra/releases
- Xbox 360 XEX loader: https://github.com/zeroKilo/XEXLoaderWV
- Prefer a Ghidra/loader combination with explicitly documented compatibility; do not assume the newest loader ZIP works with every Ghidra version.
- If encrypted/packed, an appropriate XEX-aware loader/decompressor is needed before normal PowerPC disassembly. Do not publish binary dumps or proprietary code.
