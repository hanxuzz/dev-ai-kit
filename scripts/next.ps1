# Tell the user the single next sentence. Prints Chinese. Exit 0 always when it can read the workspace.
param(
  [Parameter(Mandatory = $true)][string]$Workspace
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib.ps1')

$script:captured = New-Object System.Collections.Generic.List[string]
function Emit([string]$Text) {
  $script:captured.Add($Text)
  Write-Output $Text
}
function Say([string]$Text) {
  Emit "下一步就做这一句：$Text"
}
function Save-Next {
  try {
    if (-not $Workspace -or -not (Test-Path -LiteralPath $Workspace)) { return }
    $cursor = Join-Path $Workspace '.cursor'
    if (-not (Test-Path -LiteralPath $cursor)) {
      New-Item -ItemType Directory -Force -Path $cursor | Out-Null
    }
    $enc = New-Object System.Text.UTF8Encoding $true
    [System.IO.File]::WriteAllLines((Join-Path $cursor 'next-step.txt'), [string[]]$script:captured, $enc)
  } catch { }
}
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch { }
$OutputEncoding = New-Object System.Text.UTF8Encoding $false

try {
if (-not (Test-Path -LiteralPath $Workspace)) {
  Say '先告诉我业务项目文件夹在哪。Cursor 要打开包着前端和后端的那一层，不是套件仓库。'
  exit 0
}
$Workspace = (Resolve-Path -LiteralPath $Workspace).Path
$projectFile = Join-Path $Workspace 'project.yaml'
$localFile = Join-Path $Workspace 'project.local.yaml'

Emit "工作区：$Workspace"

if (-not (Test-Path -LiteralPath $projectFile)) {
  Emit '还差：还没安装。不需要复制 skill.md。'
  Say '请用 https://github.com/hanxuzz/dev-ai-kit 安装到当前项目。克隆到当前文件夹外面，阅读 bootstrap/SKILL.md 并按它执行。不要改业务代码。'
  exit 0
}

$project = Read-SimpleYaml $projectFile
$confirmed = ''
if ($project.conventions) { $confirmed = [string]$project.conventions.confirmed }
if ($confirmed -ne 'true') {
  Emit '还差：分支和提交规范还没按这个项目确认。默认建议在 docs/conventions.md，现在不会自动建分支。'
  Say '对照各代码仓现在的分支，告诉我哪些规范打开、哪些关掉。确认前不要新建需求，也不要改代码。'
  exit 0
}

$local = $null
if (Test-Path -LiteralPath $localFile) { $local = Read-SimpleYaml $localFile }
else {
  Emit '还差：没有 project.local.yaml。'
  Say '请再用 https://github.com/hanxuzz/dev-ai-kit 安装一次，补上 project.local.yaml。不要改业务代码。'
  exit 0
}

$docsRoot = Resolve-DocsRoot $Workspace $project $local
if (-not $docsRoot -or -not (Test-Path -LiteralPath $docsRoot)) {
  Emit '还差：文档目录不存在，或共享目录路径是空的。'
  Say '文档准备放哪：文档库、OneDrive 共享目录，还是项目里的 docs 并且不提交？'
  exit 0
}
$docsRoot = (Resolve-Path -LiteralPath $docsRoot).Path

$later = New-Object System.Collections.Generic.List[string]
$bg = Join-Path $docsRoot 'team\background.md'
if (-not (Test-Path -LiteralPath $bg)) {
  Emit '还差：还没有项目背景。'
  Say '根据当前前后端，起草项目背景。看不懂的地方留空，文首保持未确认。'
  exit 0
}
$bgText = [System.IO.File]::ReadAllText($bg)
if ($bgText -match '未确认') {
  $later.Add('项目背景文首仍是未确认。你看过 docs/team/background.md 后可以说：背景已确认。')
}

$runtimeTest = ''
$runtimeStart = ''
if ($project.runtime) {
  if ($project.runtime.test) { $runtimeTest = [string]$project.runtime.test }
  if ($project.runtime.backend -and $project.runtime.backend.start) { $runtimeStart = [string]$project.runtime.backend.start }
  if (-not $runtimeStart -and $project.runtime.frontend -and $project.runtime.frontend.start) {
    $runtimeStart = [string]$project.runtime.frontend.start
  }
}
if (-not $runtimeTest -or -not $runtimeStart) {
  $later.Add('启动命令或测试命令还是空的。要自测时再填 project.yaml 的 runtime，不要现在连数据库。')
}

$reqRoot = Resolve-RequirementsRoot $docsRoot $project
if (-not $reqRoot) {
  Emit '还差：requirements_dir 不是一个目录名。'
  Say '把 project.yaml 里的 docs.requirements_dir 改成 requirement 或 requirements，不要写路径。'
  exit 0
}
$dirs = @()
if (Test-Path -LiteralPath $reqRoot) {
  $dirs = @(Get-ChildItem -LiteralPath $reqRoot -Directory)
}
$current = ''
if ($local.current) { $current = [string]$local.current }

if (-not $current -and $dirs.Count -gt 0) {
  Emit '已经有需求目录，不要另起一套空目录。'
  $dirs | ForEach-Object { Emit "- $($_.Name)" }
  Say '接上已有需求，告诉我需求号。不要新建目录，也不要覆盖里面的文件。'
  exit 0
}
if ($dirs.Count -eq 0 -or -not $current) {
  Emit '已经有：安装配置和项目背景。'
  Emit '还差：还没有一条正在做的需求。'
  if ($later.Count -gt 0) { Emit '还可以稍后做：'; $later | ForEach-Object { Emit "- $_" } }
  Say '新建需求。没有工单号就用 REQ-今天日期-英文短名，并告诉我标题。'
  exit 0
}

$dir = Join-Path $reqRoot $current
if (-not (Test-Path -LiteralPath $dir)) {
  Emit "还差：当前需求号 $current 没有对应文件夹。"
  Say "新建需求 $current。"
  exit 0
}

$statusPath = Join-Path $dir 'status.yaml'
if (-not (Test-Path -LiteralPath $statusPath)) {
  Emit "还差：$current 没有 status.yaml。"
  Say "按 flow-intake 只补 $current 的 status.yaml，不要创建后面的空文件。"
  exit 0
}
$status = Read-SimpleYaml $statusPath
$blocker = [string]$status.blocker
$questions = [string]$status.questions
Emit "当前需求：$current"
Emit "阶段：$($status.stage)    问题：$questions"

if ($blocker) {
  Emit "还差：被挡住了。$blocker"
  Say "先处理这件事：$blocker 处理完再告诉我继续。"
  exit 0
}

if ($questions -eq 'open') {
  Emit '还差：问题清单还没经需求方确认。现在不能写开发顺序，也不能改代码。'
  Emit "请把 $dir\03-questions.md 给需求方看。有共享目录时，同一份应在共享目录里。"
  Say '需求方已确认。按确认结果更新需求和影响点。'
  exit 0
}

$kitNames = @(
  'status.yaml', '01-meeting.md', '02-sources.md', '03-questions.md',
  '04-requirement.md', '05-impact.md', '06-plan.md', '07-testcases.md'
)
$existingFiles = @(Get-ChildItem -LiteralPath $dir -File | Where-Object { $kitNames -notcontains $_.Name })
if ($existingFiles.Count -gt 0 -and -not (Test-Path -LiteralPath (Join-Path $dir '02-sources.md'))) {
  Emit '还差：这个需求目录里已有材料，还没有收进 02-sources.md。'
  $existingFiles | Select-Object -First 8 | ForEach-Object { Emit "- $($_.Name)" }
  Say '把这些已有文件收成 02-sources.md。只追加摘录，不要改名，不要覆盖原文件。没有录屏就不要写 01-meeting.md。'
  exit 0
}

$steps = @(
  @{ File = '01-meeting.md'; Say = '解析这个需求的录屏。没有录像就改说：先收资料，把链接发给我。' }
  @{ File = '02-sources.md'; Say = '把需求方给的链接、Figma、Confluence 或 PDF 收进这个需求。没有材料就直接说：没有外部资料，对照代码整理需求。' }
  @{ File = '04-requirement.md'; Say = '对照现在的代码整理这个需求。有对不上的地方先写成问题，不要写开发顺序。' }
  @{ File = '05-impact.md'; Say = '对照现在的代码整理这个需求。有对不上的地方先写成问题，不要写开发顺序。' }
  @{ File = '06-plan.md'; Say = '写出开发顺序。' }
  @{ File = '07-testcases.md'; Say = '整理测试用例。能自动跑的标 auto，不能跑的标 manual。每条需求都要有用例，或写明为什么不测。' }
)

foreach ($step in $steps) {
  if (-not (Test-Path -LiteralPath (Join-Path $dir $step.File))) {
    Emit "还差：还没有 $($step.File)。"
    if ($later.Count -gt 0) { Emit '还可以稍后做：'; $later | ForEach-Object { Emit "- $_" } }
    Say $step.Say
    exit 0
  }
}

$planPath = Join-Path $dir '06-plan.md'
$planText = [System.IO.File]::ReadAllText($planPath)
if ($planText -match '(?m)^- \[ \]') {
  $branchOn = ''
  if ($project.conventions -and $project.conventions.branch) {
    $branchOn = [string]$project.conventions.branch.enabled
  }
  Emit '还差：开发顺序里还有没勾上的步骤。'
  if ($branchOn -eq 'true') {
    $pattern = 'feature/{id}'
    if ($project.conventions.branch.pattern) { $pattern = [string]$project.conventions.branch.pattern }
    $branch = $pattern.Replace('{id}', $current)
    Emit "改代码前要先在对应仓库使用分支 $branch 。"
    Say "做计划里第一个还没勾上的任务。开始前先建好或切到分支 $branch ，只做这一步。"
  }
  else {
    Emit '这个项目已关掉自动建分支，停在当前分支上改。'
    Say '做计划里第一个还没勾上的任务。只做这一步。做完告诉我验证命令的结果。'
  }
  exit 0
}

$casePath = Join-Path $dir '07-testcases.md'
$caseText = [System.IO.File]::ReadAllText($casePath)
if ($caseText -match '未执行') {
  if (-not $runtimeTest) {
    Emit '还差：用例还没跑，而且 project.yaml 里没有测试命令。'
    Say '先别跑。告诉我后端和前端怎么在本地启动，测试命令是哪一条。口令不要发在对话里，只给 Bitwarden 条目名。'
    exit 0
  }
  Emit '还差：用例写了，但还有未执行的自动项。'
  Say '执行这个需求里标了 auto 的用例。没有命令输出就不要写成通过。'
  exit 0
}

Emit '这条需求的文件已经齐，用例也没有挂着未执行。'
if ($later.Count -gt 0) {
  Emit '还可以优化：'
  $later | ForEach-Object { Emit "- $_" }
  Say '看上面还可以优化的第一条，做完再叫我。'
  exit 0
}
Say '这条需求可以收工。下一个需求对我说：新建需求，并告诉我标题。'
exit 0
} finally {
  Save-Next
}
