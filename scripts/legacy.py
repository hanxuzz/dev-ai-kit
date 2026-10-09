"""Translate legacy option names without invoking a shell."""
import subprocess
import sys
from pathlib import Path
options = {'-Workspace': '--workspace', '-DocsMode': '--mode', '-DocsRepo': '--docs-repo', '-SharePath': '--share', '-Apply': '--apply', '-Full': '--full', '-Ready': '--ready', '-All': '--all', '-ConfigOnly': '--config-only', '-Capability': '--capability'}
args = sys.argv[1:]
translated = []
i = 0
while i < len(args):
    if args[i] == '-Kit':
        if i + 1 >= len(args) or Path(args[i + 1]).resolve() != Path(__file__).resolve().parent.parent:
            raise SystemExit('FAIL kit-path: run the installer from the selected kit directory')
        i += 2
        continue
    translated.append(options.get(args[i], args[i]))
    i += 1
raise SystemExit(subprocess.call([sys.executable, str(Path(__file__).with_name('kit.py')), *translated]))
