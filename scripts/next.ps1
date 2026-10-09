param([Parameter(Mandatory=$true)][string]$Workspace, [switch]$Full)
$argsList = @('next', '--workspace', $Workspace)
if ($Full) { $argsList += '--full' }
& (Join-Path $PSScriptRoot 'kit.ps1') @argsList
exit $LASTEXITCODE
