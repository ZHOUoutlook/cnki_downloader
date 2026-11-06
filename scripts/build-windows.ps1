param(
    [string]$Python = "$PSScriptRoot\..\.venv\Scripts\python.exe",
    [string]$ISCC = ""
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path "$PSScriptRoot\..").Path
Push-Location $projectRoot
try {
    if (-not (Test-Path -LiteralPath $Python)) { throw 'Python not found. Pass -Python with your build environment path.' }
    $version = & $Python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read application version.' }
    & $Python -m PyInstaller --noconfirm --windowed --onedir --name CNKI-Paper-Assistant --paths src --collect-submodules cnki_downloader.gui --hidden-import PyQt6.QtSvg --icon "$projectRoot/packaging/windows/app.ico" --specpath build/windows --workpath build/windows/work --distpath dist packaging/windows/launcher.py
    if ($LASTEXITCODE -ne 0) { throw 'Application build failed.' }
    if ($ISCC) {
        & $ISCC "/DAppVersion=$version" packaging/windows/installer.iss
        if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
        Write-Host "Installer ready: $projectRoot\dist\CNKI-Paper-Assistant-$version-Setup-x64.exe"
    } else {
        & $Python scripts/build-msi.py
        if ($LASTEXITCODE -ne 0) { throw 'MSI build failed. Use Python 3.12 on Windows.' }
    }
} finally {
    Pop-Location
}
