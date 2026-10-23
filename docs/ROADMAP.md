# Xbox 360 L4D2 reverse-engineering roadmap

## Verified extraction report — 2026-10-23

User-reported Windows PowerShell outputs from xVerter:

- ZArchive file size: **3,809,468,161 bytes**
- Header start: `28 b5 2f fd` (Zstandard frame magic)
- Archive: recognized by xVerter as `format: zar`; footer verified
- Files indexed: **96**, aggregate content **4,657,721,169 bytes**
- `xverter convert`: **100% completed**, reported successful extraction
- Extracted directory: `game-extracted/` (local, Git-ignored)
- Xbox 360 executable discovered: `game-extracted/default.xex` (**one .xex**)
- XEX header: **XEX2**, size **757,760 bytes**, flags `0x00000001`, PE offset `0x1000`, security information offset `0x98`, **16 optional headers**
- Execution identity: Title ID **`454108D4`** and Media ID **`0E79403B`** (matches World release)
- Encryption and compression: **not yet reported**
- No decompilation or executable decryption has been completed

## Milestones

- [x] Identify original archive format and metadata.
- [x] Extract local archive contents successfully.
- [x] Locate an Xbox 360 executable file named `default.xex`.
- [x] Inspect XEX2 magic and execution ID metadata.
- [ ] Inspect base-file encryption and compression flags (inspector updated; awaiting output).
- [ ] Generate a private local extracted-file inventory (optional).
- [ ] Document import tables, executable architecture, and security/packing status.
- [ ] Configure and validate a suitable executable loader/reverse-engineering environment.
- [ ] Identify functions and relationships in original, independently written research notes.
- [ ] Independently implement and test narrow subsystems when feasible.
- [ ] Evaluate whether reproducible or matching builds are realistically achievable.

See [XEX analysis guide](XEX_ANALYSIS.md) and [extraction guide](EXTRACTION.md).

**Status:** archive extraction and initial XEX identity verified; encryption/compression flags are next. No playable build or recovered game source exists in this repository.
