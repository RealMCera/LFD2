# Play the Chrome prototype

**This is an original browser FPS/zombie-survival prototype, not an emulated or ported copy of Left 4 Dead 2.** No Valve game files are bundled. Everything runs in your browser using Canvas and JavaScript.

## Play it locally now (Windows + Chrome)

Open PowerShell:

    cd C:\Users\FrontDesk\LFD2
    git pull
    & "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" (Resolve-Path ".\docs\index.html").Path

If Chrome is installed in another location, open C:\Users\FrontDesk\LFD2\docs\index.html with **Open with → Google Chrome**. No server, backend, or additional game archive is needed. Desktop mouse and keyboard are recommended.

Click **ENTER THE CITY** to begin. Chrome can lock your mouse for first-person aiming. Press Escape to release it. Arrow keys and Space provide a fallback.

## Controls

| Action | Controls |
|---|---|
| Move | W / A / S / D |
| Aim/turn | Mouse or left/right arrows |
| Shoot | Left mouse button or Space |
| Sprint | Shift |
| Reload | R |
| Use medkit | F |
| Minimap | M |
| Pause | Escape or P |
| Resume | Click RESUME |

## Features

- First-person pseudo-3D raycasting, rendered with Canvas
- Five infected waves with increasing difficulty
- Two AI teammates with basic follow/combat logic
- Zombie navigation, attacks and line-of-sight shooting
- 24-round pistol, reloads, supply/medkit pickups
- Health bars, ammo display, minimap and sound toggle
- Single self-contained offline HTML file, no third-party assets or libraries

## Publish to GitHub Pages for a shareable Chrome link

The browser game is already in docs/index.html. To publish it:

1. Visit https://github.com/RealMCera/LFD2
2. Select Settings → Pages.
3. Under Build and deployment, select Deploy from a branch.
4. Select branch main and folder /docs, then Save.
5. Open the website URL GitHub reports once Pages finishes deploying. The usual default project URL is https://realmcera.github.io/LFD2/ , but it has **not been verified live**.

Documentation: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site

## Scope

This prototype is **not Xbox 360 emulation, not Valve's Source engine, and not the original Left 4 Dead 2 ported to Chrome**. It cannot run the original XEX2 or DLL-named game modules. A real commercial-game port remains a separate, substantially larger project.
