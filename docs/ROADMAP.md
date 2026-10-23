# Xbox 360 Left 4 Dead 2 reverse-engineering roadmap

## Verified local results — 2026-10-23

Reported from the project's Windows PowerShell workflow:

- ZArchive: **3,809,468,161 bytes**, recognized, **96 files**, extraction completed at 100%.
- Local executable: `game-extracted/default.xex`, **757,760 bytes**, format **XEX2**.
- Title ID: `454108D4`; Media ID: `0E79403B`; version: **0.0.0.3**.
- Encryption: **Normal**. Compression: **Basic**.
- xex2ool binary was successfully installed and ran `info`, `imports`, and `basefile`.
- Load address: `0x82000000`; entry point: `0x82010CB8`; image size: `0xC0000`.
- Resource count **1**, named `454108D4`, address `0x82021080`, size `0x9A6F0`.
- Imports: `xam.xex` **7**, `xboxkrnl.exe` **43** (v2.0.9328.0, min v2.0.8507.0).
- Decoded local basefile: `research/local/default.basefile`, **786,432 bytes**, starts with **MZ**.
- The extracted basefile has **not** been fully verified as a valid PE, and no function decompilation has been performed.

## Milestones

- [x] Identify and extract source ZArchive.
- [x] Find XEX2 and verify game identity.
- [x] Identify encryption and compression.
- [x] Run xex2ool information and import analysis.
- [x] Produce a local MZ basefile without publishing it.
- [x] Add `tools/inspect_pe.py` to inspect PE/COFF header metadata.
- [ ] Verify PE signature, machine type, sections, image base, entry address.
- [ ] Install matching **Ghidra 12.1.3** and **XEXLoaderWV 12.1.3**.
- [ ] Import `default.xex` with the PowerPC-aware XEX loader.
- [ ] Validate mapped entry point, imports, functions, and analysis quality.
- [ ] Produce original research notes and independently written code/tests.
- [ ] Assess whether a complete buildable recreation is realistically feasible.

See [Ghidra setup](GHIDRA_SETUP.md) and [XEX analysis](XEX_ANALYSIS.md).

**Status: executable decoding completed; PE validation and Ghidra function analysis still pending.**
