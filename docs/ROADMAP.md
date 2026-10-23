# Xbox 360 Left 4 Dead 2 reverse-engineering roadmap

## Confirmed local research (October 23, 2026)

The project owner's PowerShell reports establish the following facts:

- ZArchive: **3,809,468,161 bytes**, footer valid, **96 files** / **4,657,721,169 aggregate bytes**
- xVerter completed local extraction successfully (**100%**)
- One Xbox 360 executable: `game-extracted/default.xex`
- Executable: **XEX2**, **757,760 bytes**
- PE data offset: `0x1000`, security info: `0x98`, module flags: `0x00000001`
- Optional header count: **16**
- Title ID: **`454108D4`**, Media ID: **`0E79403B`**
- Base-file format descriptor: present, size **24 bytes**
- Encryption type: **1 — normal (encrypted)**
- Compression type: **1 — basic** (not LZX)
- All **five synthetic inspector tests passed**
- The executable has **NOT** been decrypted, unpacked into a basefile, disassembled, or decompiled.

## Milestones

- [x] Identify and extract ZArchive
- [x] Locate XEX2 executable
- [x] Confirm execution ID and base-file security/compression metadata
- [x] Add local workflow for `xex2ool`
- [ ] Run `xex2ool info` and `xex2ool imports` on the local XEX and capture non-secret metadata
- [ ] Extract a local basefile, confirm whether it contains a PE image or flat data
- [ ] Configure a compatible PowerPC/XEX reverse engineering loader in Ghidra
- [ ] Identify entry point, sections, imports, and function boundaries
- [ ] Write independent function and subsystem research notes
- [ ] Assess the scope and practicality of a reproducible replacement build

See [XEX workflow](XEX_ANALYSIS.md). Keep any decrypted/recovered executable material local.

**This repository is research scaffolding, not a complete game decompilation or playable build.**
