#Requires -Version 7.0
Get-Job -Name minimoo-dashboard -ErrorAction SilentlyContinue | Stop-Job -PassThru | Remove-Job -Force
Write-Host 'dashboard stopped'
