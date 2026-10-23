# Left 4 Dead 2 — Xbox 360 reverse-engineering workspace

**Status: archive extracted locally; XEX inspection is next. This is not a source decompilation or playable game build.**

This project documents independent research into the Xbox 360 edition of Left 4 Dead 2. No proprietary executable, assets, keys, or recovered source code are published here.

## Current findings — October 23, 2026

- Locally extracted **96 files** from a **3.81 GB ZArchive** (reported by the project owner).
- xVerter reported **100% extraction** and identified **one XEX**: \`game-extracted/default.xex\`.
- The executable's **XEX2 header has not yet been read**, and its code has **not been decompiled**.

## Next step on Windows

Open PowerShell in \`C:\Users\FrontDesk\LFD2\` and run:

\`\`\`powershell
git pull
py tools\inspect_xex.py
\`\`\`

The new script reads only executable metadata locally (format signature, flags, offsets, optional headers, Title ID/Media ID if present). It does not decrypt or decompile executable code.

See [full XEX analysis guide](docs/XEX_ANALYSIS.md), [project roadmap](docs/ROADMAP.md), [Windows extraction guide](docs/EXTRACTION.md), and [research note template](docs/RESEARCH_TEMPLATE.md).

## Local tools

- \`tools/extract_local.py\`: identifies and extracts a locally held archive using xVerter.
- \`tools/inspect_xex.py\`: reads Xbox 360 XEX2 header metadata without external libraries.
- \`tools/inventory.py\`: inventories local extracted files, sizes, and SHA-256 hashes (optional).

Unit tests for the XEX2 inspector use synthetic data:

\`\`\`powershell
py -m unittest discover -s tests -v
\`\`\`

Keep game data in \`game-extracted/\`; the directory is excluded by \`.gitignore\`. **Never upload copyrighted game assets, executable binaries, decompiler dumps, or secrets to this public repository.** 
