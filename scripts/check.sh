#!/usr/bin/env bash
# 只报告依赖在不在。不安装、不下载、不连库。
set -u
kit_root="$(cd "$(dirname "$0")/.." && pwd)"
missing=0

check_file() {
  if [ -f "$kit_root/$1" ]; then
    echo "ok   $1"
  else
    echo "miss $1"
    missing=1
  fi
}

echo "kit: $kit_root"
check_file "kit.yaml"
check_file "AGENTS.md"
check_file "README.md"
check_file "MANUAL.md"
check_file "开始.md"
check_file "PLAN.md"
check_file "bootstrap/SKILL.md"
check_file "rules/dev-ai-kit.mdc"
check_file "docs/layout.md"
check_file "docs/runtime.md"
check_file "docs/dependencies.md"
check_file "docs/trust.md"
check_file "docs/practices.md"
check_file "docs/fit.md"
check_file "docs/code-style.md"
check_file "docs/secrets.md"
check_file "docs/conventions.md"
check_file "skills/flow-conventions/SKILL.md"
check_file "skills/flow-bitwarden/SKILL.md"
check_file "skills/flow-implement/SKILL.md"
check_file "skills/flow-next/SKILL.md"
check_file "scripts/next.ps1"
check_file "scripts/validate.ps1"
check_file "templates/requirements/status.yaml"

if [ -f "$HOME/.cursor/skills/asr-watch/SKILL.md" ] || command -v asr-watch >/dev/null 2>&1; then
  echo "ok   asr-watch"
else
  echo "miss asr-watch"
  missing=1
fi

if command -v ffmpeg >/dev/null 2>&1; then
  echo "ok   ffmpeg"
else
  echo "miss ffmpeg"
  missing=1
fi

if [ -f "$HOME/.cursor/skills/agent-browser/SKILL.md" ]; then
  echo "ok   agent-browser skill"
else
  echo "miss agent-browser skill"
  missing=1
fi

if [ -d "$HOME/.cursor/aifred-agent-browser" ]; then
  echo "ok   agent-browser source"
else
  echo "miss agent-browser source"
  missing=1
fi

if [ -f "$HOME/.cursor/mcp.json" ] && grep -q bitwarden "$HOME/.cursor/mcp.json"; then
  echo "ok   bitwarden mcp"
else
  echo "warn bitwarden mcp is not in user mcp.json; see docs/secrets.md"
fi

echo
if [ "$missing" -eq 0 ]; then
  echo "check passed"
  exit 0
fi
echo "see docs/dependencies.md"
exit 1
