#!/bin/sh
set -e
dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
if command -v powershell.exe >/dev/null 2>&1; then
  exec powershell.exe -NoProfile -File "$dir/next.ps1" "$@"
fi
if command -v pwsh >/dev/null 2>&1; then
  exec pwsh -NoProfile -File "$dir/next.ps1" "$@"
fi
echo "FAIL no-powershell"
exit 1
