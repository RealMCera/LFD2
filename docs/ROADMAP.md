# Xbox 360 L4D2 research roadmap

## Confirmed local archive findings — 2026-10-23

Reported by the project owner from Windows PowerShell using xVerter `info`:

- Filename: `Left 4 Dead 2 (World) (En,Ja,Fr,De,Es,It,Pt,Zh,Ko,Pl,Ru).zar`
- Archive size: **3,809,468,161 bytes**
- First four bytes: `28 b5 2f fd` (Zstandard frame magic)
- xVerter identification: `format : zar`
- xVerter validation: `footer : ZArchive magic OK`
- Files indexed by xVerter: **96**
- Reported aggregate file content: **4,657,721,169 bytes**
- Extraction: **not yet attempted or confirmed**
- XEX files: **not yet located**

## Milestones

- [x] Confirm format from local header and xVerter `info` metadata.
- [x] Document the extraction commands in [EXTRACTION.md](EXTRACTION.md) (not yet executed against this particular archive).
- [ ] Extract the 96 files locally and confirm completion.
- [ ] Inventory the local extracted files (keep copyrighted game files private).
- [ ] Locate and verify Xbox 360 executable modules (`*.xex`).
- [ ] Record XEX metadata, import tables, and architecture.
- [ ] Select and test an appropriate reverse-engineering loader/toolchain.
- [ ] Identify initial functions and relationships in original research notes.
- [ ] Establish independent code and tests for narrow subsystems.
- [ ] Evaluate whether a reproducible or matching build is achievable.

**Project status: archive format identification complete; decompilation has not begun.**
