# Cross-platform adapter; all decisions live in kitcore.
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$CliArgs)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = $env:DEV_AI_KIT_PYTHON
if (-not $python) {
  $candidate = Join-Path $root '.venv/Scripts/python.exe'
  if (Test-Path -LiteralPath $candidate) { $python = $candidate }
  else {
    $candidate = Join-Path $root '.venv/bin/python'
    if (Test-Path -LiteralPath $candidate) { $python = $candidate }
  }
}
if ($python) {
  & $python (Join-Path $PSScriptRoot 'kit.py') @CliArgs
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
  & python3 (Join-Path $PSScriptRoot 'kit.py') @CliArgs
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
  & py -3 (Join-Path $PSScriptRoot 'kit.py') @CliArgs
} else {
  Write-Error 'FAIL no-python: Python 3.10+ required; see docs/runtime.md'
  exit 1
}
exit $LASTEXITCODE
