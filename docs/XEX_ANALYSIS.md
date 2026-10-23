# L4D2 Xbox 360 XEX2 analysis history

## Confirmed data from the owner's October 23, 2026 local runs

The archive was unpacked on Windows and the main executable at `game-extracted/default.xex` identified and inspected.

- XEX2 executable size: **757,760 bytes**
- Title ID: `454108D4`; Media ID: `0E79403B`
- XEX version/base version: **0.0.0.3**
- 16 optional XEX headers; module flags `0x00000001`
- Encryption: **Normal**; compression: **Basic**
- xex2ool v0.4.0 was successfully installed and executed
- Image base `0x82000000`, entry `0x82010CB8`, image size `0x000C0000`
- Imports: `xam.xex` (7), `xboxkrnl.exe` (43)
- Resources: 1 (address `0x82021080`, size `0x9A6F0`)
- The xex2ool `basefile` command created `research/local/default.basefile`, **786,432 bytes**, with initial bytes `4D 5A` (**MZ**).
- The basefile size matches the reported XEX image size. Complete PE validity and executable code structure remain **unverified**.

The original XEX and local basefile must **not** be uploaded to this public repository.

## Commands already completed

```powershell
py tools\extract_local.py "$archive"
py tools\inspect_xex.py
py tools\prepare_xex.py
py tools\prepare_xex.py --extract
```

## Next commands

```powershell
git pull
py -m unittest discover -s tests -v
py tools\inspect_pe.py
```

Then follow [GHIDRA_SETUP.md](GHIDRA_SETUP.md) for the version-matched Ghidra and Xbox XEX loader workflow.

**Important:** xex2ool extraction recovers a decoded executable image; it is not itself a C/C++ decompilation or playable reconstruction.
