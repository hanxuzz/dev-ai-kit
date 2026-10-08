# Report whether kit files and local dependencies exist.
# Does not install, download, or connect to anything.

$ErrorActionPreference = "Continue"
$kitRoot = Split-Path -Parent $PSScriptRoot
$missing = @()

function Test-CommandOnPath {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Host "kit: $kitRoot"
foreach ($rel in @(
    "kit.yaml",
    "AGENTS.md",
    "README.md",
    "MANUAL.md",
    "开始.md",
    "PLAN.md",
    "bootstrap\SKILL.md",
    "rules\dev-ai-kit.mdc",
    "docs\layout.md",
    "docs\runtime.md",
    "docs\dependencies.md",
    "docs\trust.md",
    "docs\practices.md",
    "docs\fit.md",
    "docs\code-style.md",
    "skills\flow-implement\SKILL.md",
    "scripts\validate.ps1",
    "templates\requirements\status.yaml"
)) {
    $full = Join-Path $kitRoot $rel
    if (Test-Path -LiteralPath $full) {
        Write-Host "ok   $rel"
    } else {
        Write-Host "miss $rel"
        $missing += $rel
    }
}

$docs = Join-Path $kitRoot "docs"
$docCount = 0
if (Test-Path -LiteralPath $docs) {
    $docCount = @(Get-ChildItem -LiteralPath $docs -Filter "*.md" -File).Count
}
if ($docCount -gt 0) {
    Write-Host "ok   docs ($docCount markdown)"
} else {
    Write-Host "miss docs markdown"
    $missing += "docs"
}

$asrSkill = Join-Path $env:USERPROFILE ".cursor\skills\asr-watch\SKILL.md"
$browserSkill = Join-Path $env:USERPROFILE ".cursor\skills\agent-browser\SKILL.md"
$browserSrc = Join-Path $env:USERPROFILE ".cursor\aifred-agent-browser"

if ((Test-Path -LiteralPath $asrSkill) -or (Test-CommandOnPath "asr-watch") -or (Test-CommandOnPath "asr-watch.cmd")) {
    Write-Host "ok   asr-watch"
} else {
    Write-Host "miss asr-watch"
    $missing += "asr-watch"
}

if (Test-CommandOnPath "ffmpeg") {
    Write-Host "ok   ffmpeg"
} else {
    Write-Host "miss ffmpeg"
    $missing += "ffmpeg"
}

if (Test-Path -LiteralPath $browserSkill) {
    Write-Host "ok   agent-browser skill"
} else {
    Write-Host "miss agent-browser skill"
    $missing += "agent-browser"
}

if (Test-Path -LiteralPath $browserSrc) {
    Write-Host "ok   agent-browser source"
} else {
    Write-Host "miss agent-browser source"
    $missing += "aifred-agent-browser"
}

Write-Host ""
if ($missing.Count -eq 0) {
    Write-Host "check passed"
    exit 0
}

Write-Host ("missing: " + ($missing -join ", "))
Write-Host "see docs/dependencies.md"
exit 1
