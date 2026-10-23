# Left 4 Dead 2 — Xbox 360 reverse-engineering workspace

**Status: research scaffolding. This is not a game decompilation or playable build.**

This repository documents independent research into the Xbox 360 edition of Left 4 Dead 2. It contains no proprietary executable, extracted game assets, code, encryption keys, or disassembly. Use only game files you are permitted to analyze locally.

## Working from your own `.zar` archive

First confirm the archive format with an appropriate local inspection/conversion tool. The format has **not yet been verified by examination of file bytes**. Do not treat the extension alone as proof of the contained format.

After you have extracted it locally, inventory the output:

```powershell
py tools/inventory.py "game-extracted" --out "research/inventory.json"
```

The script creates a local listing containing file paths, sizes, and SHA-256 hashes. The output is ignored by Git.

## Next targets

1. Identify archive/container type and extraction method.
2. Extract your own files locally; locate `default.xex` if present.
3. Determine executable metadata and PowerPC architecture.
4. Load executable in an appropriate reverse-engineering environment (such as Ghidra with a validated XEX loader).
5. Record module imports, function boundaries, and original research notes.
6. Work toward independently written code/tests if feasible.

See [docs/ROADMAP.md](docs/ROADMAP.md). Never commit game assets, decompiler output copied from proprietary binaries, executable dumps, or secrets.

## Reality check

A source-compatible, buildable Left 4 Dead 2 decompilation cannot be generated simply by converting a compressed game archive. The research and tooling must be developed incrementally. This repository is currently only an organizational starting point.
