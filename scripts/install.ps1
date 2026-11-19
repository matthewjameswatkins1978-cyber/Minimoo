#Requires -Version 7.0
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$env:MINIMOO_DATA = if ($env:MINIMOO_DATA) { $env:MINIMOO_DATA } else { "$env:USERPROFILE\.minimoo" }
New-Item -ItemType Directory -Force -Path $env:MINIMOO_DATA | Out-Null
python -m minimoo init
Write-Host "Minimoo installed. Data: $env:MINIMOO_DATA"
Write-Host "Start: python -m minimoo dashboard  (or scripts/start.ps1)"
