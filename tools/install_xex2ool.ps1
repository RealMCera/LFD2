# Install xex2ool from the upstream GitHub release into tools/bin/.
# Run from the LFD2 checkout: powershell -NoProfile -ExecutionPolicy Bypass -File tools\install_xex2ool.ps1
# This downloads a public tool, not any game data.
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$releaseApi = "https://api.github.com/repos/landaire/acceleration/releases/tags/v0.4.0"
$destDir = Join-Path $PSScriptRoot "bin"
$dest = Join-Path $destDir "xex2ool.exe"

if (Test-Path -LiteralPath $dest) {
    Write-Host "Already installed: $dest"
    & $dest --help
    exit $LASTEXITCODE
}

try {
    $headers = @{ "User-Agent" = "LFD2-xex2ool-installer"; "Accept" = "application/vnd.github+json" }
    $release = Invoke-RestMethod -Uri $releaseApi -Headers $headers
    $assets = @($release.assets)

    # Filter by the GitHub release filenames rather than guessing a download URL.
    $windows = @($assets | Where-Object {
        $_.name -match '(?i)(windows|win64|win-x64|win_amd64|pc-windows)'
    })
    $preferred = @($windows | Where-Object { $_.name -match '(?i)(x64|amd64|x86_64)' })
    if ($preferred.Count -ge 1) { $windows = $preferred }
    $preferred = @($windows | Where-Object { $_.name -match '(?i)xex2ool' })
    if ($preferred.Count -ge 1) { $windows = $preferred }
    $supported = @($windows | Where-Object { $_.name -match '(?i)(\.zip|\.exe|\.tar\.gz)$' })
    if ($supported.Count -ne 1) {
        Write-Host "Cannot safely choose a Windows asset automatically."
        Write-Host "Assets published in $($release.tag_name):"
        $assets | ForEach-Object { Write-Host "  $($_.name)" }
        Write-Host "Download the Windows x64 build manually from:"
        Write-Host "  https://github.com/landaire/acceleration/releases/tag/v0.4.0"
        exit 2
    }
    $asset = $supported[0]
    Write-Host "Downloading official release asset: $($asset.name)"
    $temp = Join-Path ([System.IO.Path]::GetTempPath()) ("lfd2-xex2ool-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $temp -Force | Out-Null
    try {
        $downloaded = Join-Path $temp $asset.name
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $downloaded
        $extractDir = Join-Path $temp "extracted"
        New-Item -ItemType Directory -Path $extractDir -Force | Out-Null
        if ($asset.name -match '(?i)\.zip$') {
            Expand-Archive -LiteralPath $downloaded -DestinationPath $extractDir -Force
            $executables = @(Get-ChildItem -LiteralPath $extractDir -Recurse -File -Filter "xex2ool.exe")
            if ($executables.Count -ne 1) {
                throw "Expected one xex2ool.exe inside the release ZIP, found $($executables.Count)"
            }
            $source = $executables[0].FullName
        } elseif ($asset.name -match '(?i)\.tar\.gz$') {
            & tar -xf $downloaded -C $extractDir
            if ($LASTEXITCODE -ne 0) { throw "tar extraction failed" }
            $executables = @(Get-ChildItem -LiteralPath $extractDir -Recurse -File -Filter "xex2ool.exe")
            if ($executables.Count -ne 1) { throw "Expected one xex2ool.exe inside the archive" }
            $source = $executables[0].FullName
        } else {
            $source = $downloaded
        }
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $dest
        Write-Host "Installed: $dest"
        & $dest --help | Select-Object -First 12
        if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
            throw "The downloaded executable did not pass the --help check."
        }
        Write-Host "Done. Next command: py tools\prepare_xex.py"
    } finally {
        Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
    }
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
