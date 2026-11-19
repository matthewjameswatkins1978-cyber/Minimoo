#Requires -Version 7.0
$ErrorActionPreference = 'Stop'
Start-Job -Name minimoo-dashboard -ScriptBlock {
  Set-Location 'F:/Projects/Minimoo'
  $env:MINIMOO_DATA = if ($env:MINIMOO_DATA) { $env:MINIMOO_DATA } else { "$env:USERPROFILE\.minimoo" }
  python -m minimoo dashboard
} | Out-Null
Write-Host 'dashboard starting on http://127.0.0.1:3737 (127.0.0.1 only)'
