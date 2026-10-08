# Tell the user the single next sentence. Prints Chinese. Exit 0 always when it can read the workspace.
param(
  [Parameter(Mandatory = $true)][string]$Workspace
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib.ps1')

function Say([string]$Text) {
  Write-Output "下一步就做这一句：$Text"
}

if (-not (Test-Path -LiteralPath $Workspace)) {
  Say '先告诉我业务项目文件夹在哪。Cursor 要打开包着前端和后端的那一层，不是套件仓库。'
  exit 0
}
$Workspace = (Resolve-Path -LiteralPath $Workspace).Path
$projectFile = Join-Path $Workspace 'project.yaml'
$localFile = Join-Path $Workspace 'project.local.yaml'

Write-Output "工作区：$Workspace"

if (-not (Test-Path -LiteralPath $projectFile)) {
  Write-Output '还差：还没安装。根目录要有从套件复制来的 skill.md。'
  Say '请阅读项目根目录的 skill.md，并严格按它执行安装。不要跳步，不要改业务代码。做完告诉我生成了哪些文件。'
  exit 0
}

$project = Read-SimpleYaml $projectFile
$local = $null
if (Test-Path -LiteralPath $localFile) { $local = Read-SimpleYaml $localFile }
else {
  Write-Output '还差：没有 project.local.yaml。'
  Say '请再按 skill.md 安装一次，补上 project.local.yaml。'
  exit 0
}

$docsRoot = Resolve-DocsRoot $Workspace $project $local
if (-not $docsRoot -or -not (Test-Path -LiteralPath $docsRoot)) {
  Write-Output '还差：文档目录不存在，或共享目录路径是空的。'
  Say '文档准备放哪：文档库、OneDrive 共享目录，还是项目里的 docs 并且不提交？'
  exit 0
}
$docsRoot = (Resolve-Path -LiteralPath $docsRoot).Path

$later = New-Object System.Collections.Generic.List[string]
$bg = Join-Path $docsRoot 'team\background.md'
if (-not (Test-Path -LiteralPath $bg)) {
  Write-Output '还差：还没有项目背景。'
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

$reqRoot = Join-Path $docsRoot 'requirements'
$dirs = @()
if (Test-Path -LiteralPath $reqRoot) {
  $dirs = @(Get-ChildItem -LiteralPath $reqRoot -Directory)
}
$current = ''
if ($local.current) { $current = [string]$local.current }

if ($dirs.Count -eq 0 -or -not $current) {
  Write-Output '已经有：安装配置和项目背景。'
  Write-Output '还差：还没有一条正在做的需求。'
  if ($later.Count -gt 0) { Write-Output '还可以稍后做：'; $later | ForEach-Object { Write-Output "- $_" } }
  Say '新建需求。没有工单号就用 REQ-今天日期-英文短名，并告诉我标题。'
  exit 0
}

$dir = Join-Path $reqRoot $current
if (-not (Test-Path -LiteralPath $dir)) {
  Write-Output "还差：当前需求号 $current 没有对应文件夹。"
  Say "新建需求 $current。"
  exit 0
}

$statusPath = Join-Path $dir 'status.yaml'
if (-not (Test-Path -LiteralPath $statusPath)) {
  Write-Output "还差：$current 没有 status.yaml。"
  Say "按 flow-intake 只补 $current 的 status.yaml，不要创建后面的空文件。"
  exit 0
}
$status = Read-SimpleYaml $statusPath
$blocker = [string]$status.blocker
$questions = [string]$status.questions
Write-Output "当前需求：$current"
Write-Output "阶段：$($status.stage)    问题：$questions"

if ($blocker) {
  Write-Output "还差：被挡住了。$blocker"
  Say "先处理这件事：$blocker 处理完再告诉我继续。"
  exit 0
}

if ($questions -eq 'open') {
  Write-Output '还差：问题清单还没经需求方确认。现在不能写开发顺序，也不能改代码。'
  Write-Output "请把 $dir\03-questions.md 给需求方看。有共享目录时，同一份应在共享目录里。"
  Say '需求方已确认。按确认结果更新需求和影响点。'
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
    Write-Output "还差：还没有 $($step.File)。"
    if ($later.Count -gt 0) { Write-Output '还可以稍后做：'; $later | ForEach-Object { Write-Output "- $_" } }
    Say $step.Say
    exit 0
  }
}

$planPath = Join-Path $dir '06-plan.md'
$planText = [System.IO.File]::ReadAllText($planPath)
if ($planText -match '(?m)^- \[ \]') {
  Write-Output '还差：开发顺序里还有没勾上的步骤。'
  Say '做计划里第一个还没勾上的任务。只做这一步。做完告诉我验证命令的结果。'
  exit 0
}

$casePath = Join-Path $dir '07-testcases.md'
$caseText = [System.IO.File]::ReadAllText($casePath)
if ($caseText -match '未执行') {
  if (-not $runtimeTest) {
    Write-Output '还差：用例还没跑，而且 project.yaml 里没有测试命令。'
    Say '先别跑。告诉我后端和前端怎么在本地启动，测试命令是哪一条。口令不要发在对话里，只给 Bitwarden 条目名。'
    exit 0
  }
  Write-Output '还差：用例写了，但还有未执行的自动项。'
  Say '执行这个需求里标了 auto 的用例。没有命令输出就不要写成通过。'
  exit 0
}

Write-Output '这条需求的文件已经齐，用例也没有挂着未执行。'
if ($later.Count -gt 0) {
  Write-Output '还可以优化：'
  $later | ForEach-Object { Write-Output "- $_" }
  Say '看上面还可以优化的第一条，做完再叫我。'
  exit 0
}
Write-Output '套件还能加强的地方：用一场真实录屏走通解析；把 skills 接到用户技能目录，换一台电脑也能直接说。'
Say '这条需求可以收工。下一个需求对我说：新建需求，并告诉我标题。'
exit 0
