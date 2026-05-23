# build.ps1 — Genera el paquete de distribución BandeJA Downloader
# Uso: .\build.ps1 [-Version "1.0.0"]
param(
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"
$root   = $PSScriptRoot
$dist   = "$root\dist"
$output = "$root\release"

Write-Host "=== BandeJA Downloader — Build v$Version ===" -ForegroundColor Cyan

# 1. Compilar servidor con PyInstaller
Write-Host "`n[1/3] Compilando bandeja-server.exe..." -ForegroundColor Yellow
pyinstaller --clean --noconfirm "$root\bandeja-server.spec"
if (-not (Test-Path "$dist\bandeja-server.exe")) {
    Write-Error "PyInstaller no generó el ejecutable. Revisa la salida anterior."
}
Write-Host "    OK: $dist\bandeja-server.exe" -ForegroundColor Green

# 2. Ensamblar el ZIP de release
Write-Host "`n[2/3] Ensamblando release ZIP..." -ForegroundColor Yellow
$releaseDir  = "$output\BandeJA-Downloader-v$Version"
$releaseZip  = "$output\BandeJA-Downloader-v$Version.zip"

if (Test-Path $releaseDir) { Remove-Item $releaseDir -Recurse -Force }
New-Item -ItemType Directory -Path "$releaseDir\servidor"      | Out-Null
New-Item -ItemType Directory -Path "$releaseDir\instrucciones" | Out-Null

Copy-Item "$dist\bandeja-server.exe" "$releaseDir\servidor\"
# La extensión va como carpeta directa — el usuario apunta "Cargar descomprimida" a ella
Copy-Item "$root\extension" "$releaseDir\extension" -Recurse

$pdf = "$root\instrucciones\BandeJA-Downloader-Instrucciones.pdf"
if (Test-Path $pdf) {
    Copy-Item $pdf "$releaseDir\instrucciones\"
} else {
    Write-Host "    AVISO: PDF de instrucciones no encontrado, carpeta vacía." -ForegroundColor DarkYellow
}

if (Test-Path $releaseZip) { Remove-Item $releaseZip }
Compress-Archive -Path "$releaseDir\*" -DestinationPath $releaseZip
Write-Host "    OK: $releaseZip" -ForegroundColor Green

Write-Host "`n=== Build completado ===" -ForegroundColor Cyan
Write-Host "Extensión: extraer el ZIP y cargar la carpeta 'extension' en chrome://extensions"
Write-Host "Release: $releaseZip"
