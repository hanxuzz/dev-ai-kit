#!/usr/bin/env python3
"""Cross-platform entrypoint; dependencies are explicitly installed, never downloaded here."""
import sys
# PowerShell redirected streams must keep the same UTF-8 protocol as POSIX.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")
if sys.version_info < (3, 10):
    raise SystemExit('FAIL python-version: Python 3.10+ required')
try:
    import yaml
except ImportError:
    raise SystemExit('FAIL no-pyyaml: install requirements.txt in the kit virtual environment; see docs/runtime.md')
from kitcore.cli import main
if __name__ == '__main__':
    raise SystemExit(main())
