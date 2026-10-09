#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
if [ -n "${DEV_AI_KIT_PYTHON:-}" ]; then
  exec "$DEV_AI_KIT_PYTHON" "$root/scripts/kit.py" "$@"
elif [ -x "$root/.venv/bin/python" ]; then
  exec "$root/.venv/bin/python" "$root/scripts/kit.py" "$@"
elif command -v python3 >/dev/null 2>&1; then
  exec python3 "$root/scripts/kit.py" "$@"
fi
echo 'FAIL no-python: install Python 3.10+ and requirements.txt; see docs/runtime.md' >&2
exit 1
