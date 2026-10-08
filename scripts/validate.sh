#!/bin/sh
# Runs scripts/validate.ps1. Gate logic is not duplicated here.
set -e
dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
if command -v powershell.exe >/dev/null 2>&1; then
  exec powershell.exe -NoProfile -File "$dir/validate.ps1" "$@"
fi
if command -v pwsh >/dev/null 2>&1; then
  exec pwsh -NoProfile -File "$dir/validate.ps1" "$@"
fi
echo "FAIL no-powershell Install PowerShell and run scripts/validate.ps1"
exit 1
