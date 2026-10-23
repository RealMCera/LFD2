# Xbox 360 L4D2 reverse-engineering roadmap

## Verified extraction report — 2026-10-23

User-reported Windows PowerShell outputs from xVerter:

- ZArchive file size: **3,809,468,161 bytes**
- Header start: \`28 b5 2f fd\` (Zstandard frame magic)
- Archive: recognized by xVerter as \`format: zar\`; footer verified
- Files indexed: **96**, aggregate content **4,657,721,169 bytes**
- \`xverter convert\`: **100% completed**, reported successful extraction
- Extracted directory: \`game-extracted/\` (local, Git-ignored)
- Xbox 360 executable discovered: \`game-extracted/default.xex\` (**one .xex**)
- XEX header metadata / Title ID: **not yet inspected**
- No decompilation or executable decryption has been completed

## Milestones

- [x] Identify original archive format and metadata.
- [x] Extract local archive contents successfully.
- [x] Locate an Xbox 360 executable file named \`default.xex\`.
- [ ] Inspect XEX2 magic and execution metadata (script ready: \`tools/inspect_xex.py\`).
- [ ] Generate a private local extracted-file inventory (optional).
- [ ] Document import tables, executable architecture, and security/packing status.
- [ ] Configure and validate a suitable executable loader/reverse-engineering environment.
- [ ] Identify functions and relationships in original, independently written research notes.
- [ ] Independently implement and test narrow subsystems when feasible.
- [ ] Evaluate whether reproducible or matching builds are realistically achievable.

See [XEX analysis guide](XEX_ANALYSIS.md) and [extraction guide](EXTRACTION.md).

**Status:** archive extraction completed; XEX inspection is next. No playable build or recovered game source exists in this repository.
