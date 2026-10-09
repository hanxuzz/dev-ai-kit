param([Parameter(Mandatory=$true)][string]$Workspace, [switch]$Ready, [switch]$All, [switch]$ConfigOnly)
$argsList = @('validate', '--workspace', $Workspace)
if ($Ready) { $argsList += '--ready' }
if ($All) { $argsList += '--all' }
if ($ConfigOnly) { $argsList += '--config-only' }
& (Join-Path $PSScriptRoot 'kit.ps1') @argsList
exit $LASTEXITCODE
