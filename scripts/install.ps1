# Compatibility entrypoint. New installs require -Apply; default is a reviewable preview.
param([Parameter(Mandatory=$true)][string]$Workspace, [string]$Kit='', [string]$DocsMode='', [string]$DocsRepo='', [string]$SharePath='', [switch]$Apply)
$argsList = @('install', '--workspace', $Workspace)
if ($DocsMode) { $argsList += @('--mode', $DocsMode) }
if ($DocsRepo) { $argsList += @('--docs-repo', $DocsRepo) }
if ($SharePath) { $argsList += @('--share', $SharePath) }
if ($Kit -and (Resolve-Path $Kit).Path -ne (Resolve-Path (Join-Path $PSScriptRoot '..')).Path) { throw 'Run the installer from the selected kit directory.' }
if ($Apply) { $argsList += '--apply' }
& (Join-Path $PSScriptRoot 'kit.ps1') @argsList
exit $LASTEXITCODE
