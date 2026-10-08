#!/bin/sh
# Runs the Windows/PowerShell installer. The behavior lives in install.ps1.
set -e
dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
if command -v powershell.exe >/dev/null 2>&1; then
  exec powershell.exe -NoProfile -File "$dir/install.ps1" "$@"
fi
if command -v pwsh >/dev/null 2>&1; then
  exec pwsh -NoProfile -File "$dir/install.ps1" "$@"
fi
echo "FAIL no-powershell Install PowerShell and run scripts/install.ps1"
exit 1
