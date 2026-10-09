#!/bin/sh
# Translate the previous PowerShell-style options; execute the same Python engine.
set -eu
command_name=$1
shift
root=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
# Argument translation uses Python rather than eval to preserve spaces and quoting.
if [ -n "${DEV_AI_KIT_PYTHON:-}" ]; then interpreter=$DEV_AI_KIT_PYTHON
elif [ -x "$root/../.venv/bin/python" ]; then interpreter="$root/../.venv/bin/python"
else interpreter=python3
fi
exec "$interpreter" "$root/legacy.py" "$command_name" "$@"
