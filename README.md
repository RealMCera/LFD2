# Left 4 Dead 2 — Xbox 360 reverse-engineering workspace

**Status: research scaffolding, not a decompilation or playable build.**

This repository documents independent analysis of the Xbox 360 edition of Left 4 Dead 2. It contains no proprietary executable, game data, console keys, or recovered source code. Analyze only game files you are permitted to use locally.

## Windows quickstart

1. Download your own ZAR archive from Google Drive to your Windows PC.
2. Install Python 3 and xVerter (command: **py -m pip install --upgrade xverter**).
3. Open a terminal in this repository; run **py tools\extract_local.py --info-only**.
4. Paste the full local archive path when prompted.
5. Once identification succeeds, run **py tools\extract_local.py** to extract locally.

Full instructions: [Windows extraction guide](docs/EXTRACTION.md).

The archive is approximately 3.81 GB; the connected Drive service imposes a 256 MB file download limit, so we have **not** inspected its header or extracted its contents. xVerter supports ZArchive; the name alone does not establish that this specific file uses that format.

## Next milestones

- Inspect actual archive signature and metadata.
- Extract locally and find default.xex or other XEX executables, if present.
- Record architecture and executable metadata.
- Perform original function/subsystem research.
- Consider independently authored tests and implementations.

See [roadmap](docs/ROADMAP.md) and [research template](docs/RESEARCH_TEMPLATE.md).

The optional tool **tools/inventory.py** generates a local SHA-256 file manifest into research/inventory.json, which is ignored by Git.

**Do not commit game binaries or extracted assets.** Unpacking an archive does not reconstruct proprietary source code.
