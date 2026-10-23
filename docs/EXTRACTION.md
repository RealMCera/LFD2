# Windows ZArchive extraction

The game archive in Google Drive is approximately 3.81 GB. The connector refuses downloads over 256 MB, so inspect and extract a copy on your Windows PC. We have NOT examined its file header yet.

## 1. Install tools

Download this repository (Code > Download ZIP) or clone it:

    git clone https://github.com/RealMCera/LFD2.git
    cd LFD2

Install a current Python 3 for Windows, then xVerter:

    py -m pip install --upgrade xverter

If needed, download the official Windows standalone release from https://github.com/blank-query/xverter/releases and put xverter.exe on PATH.

Ensure you have substantial free disk space for extracted files; decompressed contents may be much larger than 3.81 GB.

## 2. Download the actual archive locally

Download the game archive from your Google Drive into your Downloads folder. Keep the original archive on your own PC, not in the GitHub repository.

## 3. Identify it before extracting

Open PowerShell in the repository folder:

    py tools\extract_local.py --info-only

Paste the full path when prompted, for example C:\Users\YOUR_USERNAME\Downloads\Left 4 Dead 2 (World) (En,Ja,Fr,De,Es,It,Pt,Zh,Ko,Pl,Ru).zar .

The script displays the first 32 bytes, then asks xVerter to identify the archive. Filename extensions are not proof of file format.

## 4. Extract

After successful identification run:

    py tools\extract_local.py

Paste the same local file path when prompted. xVerter will attempt conversion to a folder at game-extracted/ . The script reports any .xex filenames it finds.

Extra options:

    py tools\extract_local.py --verify
    py tools\extract_local.py --inventory

Verification reads the full archive. Inventory hashes extracted files and can be slow. The output stays local in research/inventory.json. Both game-extracted/ and this report are excluded from Git.

## 5. Next research phase

Share the text-only output of the --info-only command, and (after extraction) the XEX file paths. Do not share original game binaries, assets, keys, or copyrighted code in the public GitHub repository.

Extraction is not decompilation. We still need to identify the executable and begin original reverse-engineering research before there can be a source reconstruction.
