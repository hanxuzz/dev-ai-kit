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
    "docs\secrets.md",
    "docs\conventions.md",
    "skills\flow-conventions\SKILL.md",
    "skills\flow-bitwarden\SKILL.md",
    "skills\flow-implement\SKILL.md",
    "skills\flow-next\SKILL.md",
    "scripts\next.ps1",
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

$skills = Join-Path $kitRoot "skills"
if (Test-Path -LiteralPath $skills) {
    Get-ChildItem -LiteralPath $skills -Directory | ForEach-Object {
        $skillFile = Join-Path $_.FullName "SKILL.md"
        $name = $_.Name
        if (Test-Path -LiteralPath $skillFile) {
            Write-Host "ok   skill $name"
        } else {
            Write-Host "miss skill $name"
            $missing += "skill $name"
        }
    }
} else {
    Write-Host "miss skills directory"
    $missing += "skills"
}
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

$mcp = Join-Path $env:USERPROFILE ".cursor\mcp.json"
$hasBw = $false
if (Test-Path -LiteralPath $mcp) {
    $hasBw = Select-String -LiteralPath $mcp -Pattern "bitwarden" -Quiet -SimpleMatch
}
if ($hasBw) {
    Write-Host "ok   bitwarden mcp"
} else {
    Write-Host "warn bitwarden mcp is not in user mcp.json; see docs/secrets.md"
}

Write-Host ""
if ($missing.Count -eq 0) {
    Write-Host "技能安装：通过。套件内技能和本机依赖都在。"
    Write-Host "请你确认：无"
    Write-Host "请你做：无"
    exit 0
}

Write-Host ("技能安装：未通过。缺 " + ($missing -join ", "))
Write-Host "请你确认：无"
Write-Host "请你做：按 docs/dependencies.md 补上缺的本机依赖。套件仓库里的 skill 文件缺失时，重新克隆套件，不要手抄。"
Write-Host "see docs/dependencies.md"
exit 1
