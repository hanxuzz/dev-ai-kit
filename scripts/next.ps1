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
function AgentStep([string]$Text) {
  Emit "下一步由你来做：$Text"
}
function Progress([string]$Text) {
  Emit "套件进度：$Text"
}
function Ask([string]$Text) {
  Emit "下一步请用户定：$Text"
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
  Ask '业务项目文件夹在哪？要打开包着前端和后端的那一层，不是套件仓库。'
  exit 0
}
$Workspace = (Resolve-Path -LiteralPath $Workspace).Path
$projectFile = Join-Path $Workspace 'project.yaml'
$localFile = Join-Path $Workspace 'project.local.yaml'

Emit "工作区：$Workspace"

if (-not (Test-Path -LiteralPath $projectFile)) {
  Emit '还差：还没安装。不需要复制 skill.md。'
  AgentStep '用 https://github.com/hanxuzz/dev-ai-kit 安装到当前项目。克隆到当前文件夹外面，阅读 bootstrap/SKILL.md 并执行。不要改业务代码，也不要让用户把这句话发回来。'
  exit 0
}

$project = Read-SimpleYaml $projectFile
$confirmed = ''
if ($project.conventions) { $confirmed = [string]$project.conventions.confirmed }

$local = $null
if (Test-Path -LiteralPath $localFile) { $local = Read-SimpleYaml $localFile }
else {
  Emit '还差：没有 project.local.yaml。'
  AgentStep '再按 bootstrap/SKILL.md 安装一次，补上 project.local.yaml。不要改业务代码，不要让用户复述这句话。'
  exit 0
}

$docsRoot = Resolve-DocsRoot $Workspace $project $local
if (-not $docsRoot -or -not (Test-Path -LiteralPath $docsRoot)) {
  Emit '还差：文档目录不存在，或共享目录路径是空的。'
  Ask '文档准备放哪：已有的文档库、OneDrive 共享目录，还是项目里的 docs 并且不提交？'
  exit 0
}
$docsRoot = (Resolve-Path -LiteralPath $docsRoot).Path

$conv = Join-Path $docsRoot 'team\conventions.md'
$convText = ''
if (Test-Path -LiteralPath $conv) { $convText = [System.IO.File]::ReadAllText($conv) }
$convCollected = $convText -match '收集日期：\s*\S'
if ($confirmed -ne 'true') {
  if (-not $convCollected) {
    Emit '还差：还没有把项目已有规范收集并问过用户。'
    Progress '确认项目规范（安装后的第 1 步）'
    AgentStep '现在就按 skills/flow-conventions/SKILL.md 收集 AGENTS.md 和规则，写入 team/conventions.md。然后用确认清单逐项问用户，把读到的原文附在问题里。回复第一句用上面的套件进度。不要让用户复述这句话，也不要提后面的需求。'
  }
  else {
    Emit '还差：项目规范已经收集，还没有问过用户。'
    Progress '确认项目规范（收集已经写好，还差你点头）'
    AgentStep '打开 team/conventions.md，按 skills/flow-conventions/SKILL.md 的确认清单逐项问用户。回复第一句用上面的套件进度。不要让用户复述这句话，也不要提后面的需求。'
  }
  exit 0
}

$later = New-Object System.Collections.Generic.List[string]
$bg = Join-Path $docsRoot 'team\background.md'
if (-not (Test-Path -LiteralPath $bg)) {
  Emit '还差：还没有项目背景。'
  AgentStep '根据当前前后端起草 team/background.md 和 team/map.md。看不懂的留空，文首保持未确认。起草完只把留空的点问用户，不要让用户发口令句。'
  exit 0
}
$bgText = [System.IO.File]::ReadAllText($bg)
if ($bgText -match '未确认') {
  $later.Add('项目背景文首仍是未确认。这不挡住当前需求。起草时留空的点，用户看过可以说：背景已确认。')
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
  $later.Add('启动命令或测试命令还是空的。这不挡住改代码。要自动跑用例时再填 project.yaml 的 runtime，不要现在连数据库。')
}

$reqRoot = Resolve-RequirementsRoot $docsRoot $project
if (-not $reqRoot) {
  Emit '还差：requirements_dir 不是一个目录名。'
  AgentStep '看文档根下已经有的目录。只有 requirement 或只有 requirements 时，把 docs.requirements_dir 写成那个名字。两个都有再问用户留哪一个。不要写路径。'
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
  if ($dirs.Count -eq 1) {
    AgentStep "把 project.local.yaml 的 current 写成 $($dirs[0].Name)，不要新建目录，不要覆盖文件。写完再跑一次 next.ps1。"
  }
  else {
    Ask '上面有多条需求。当前做哪一条？告诉我需求号。'
  }
  exit 0
}
if ($dirs.Count -eq 0 -or -not $current) {
  Emit '已经有：安装配置和项目背景。'
  Emit '还差：还没有一条正在做的需求。'
  if ($later.Count -gt 0) { Emit '还可以稍后做：'; $later | ForEach-Object { Emit "- $_" } }
  Ask '还没有正在做的需求。标题是什么？有工单号用工单号，没有就用一句英文短名。'
  exit 0
}

$dir = Join-Path $reqRoot $current
if (-not (Test-Path -LiteralPath $dir)) {
  Emit "还差：当前需求号 $current 没有对应文件夹。"
  AgentStep "当前需求号 $current 没有文件夹。按 flow-intake 只建这个目录和 status.yaml，不要覆盖别的需求，也不要预告后面的步骤。"
  exit 0
}

$statusPath = Join-Path $dir 'status.yaml'
if (-not (Test-Path -LiteralPath $statusPath)) {
  Emit "还差：$current 没有 status.yaml。"
  AgentStep "按 flow-intake 只补 $current 的 status.yaml，不要创建后面的空文件。补完再跑 next.ps1。"
  exit 0
}
$status = Read-SimpleYaml $statusPath
$blocker = [string]$status.blocker
$questions = [string]$status.questions
Emit "当前需求：$current"
Emit "阶段：$($status.stage)    问题：$questions"

if ($blocker) {
  Emit "还差：被挡住了。$blocker"
  AgentStep "处理 blocker：$blocker 。缺的材料再问用户。不要让用户把这句话发回来。"
  exit 0
}

if ($questions -eq 'open') {
  Emit '还差：问题清单还没经需求方确认。现在不能写开发顺序，也不能改代码。'
  Emit "请把 $dir\03-questions.md 给需求方看。有共享目录时，同一份应在共享目录里。"
  Ask '问题清单里还有未确认项。需求方的结论是什么？确认后我再更新需求和影响点。'
  exit 0
}

$kitNames = @(
  'status.yaml', '01-meeting.md', '02-sources.md', '03-questions.md',
  '04-requirement.md', '05-impact.md', '06-plan.md', '07-testcases.md'
)
$existingFiles = @(Get-ChildItem -LiteralPath $dir -File | Where-Object { $kitNames -notcontains $_.Name })
if ($existingFiles.Count -gt 0 -and -not (Test-Path -LiteralPath (Join-Path $dir '02-sources.md'))) {
  $mapped = $false
  $pre = Read-SimpleYaml (Join-Path $dir 'status.yaml')
  foreach ($role in @('requirement', 'impact', 'plan')) {
    if (Get-RoleFileName $pre $role '') { $mapped = $true }
  }
  if (-not $mapped) {
    Emit '还差：这个需求目录里已有材料，还没对上套件要读的文件。'
    $existingFiles | Select-Object -First 8 | ForEach-Object { Emit "- $($_.Name)" }
    Progress '接上已有材料（还没写成套件要的 status.yaml）'
    AgentStep '本轮就写 status.yaml，不要先问用户怎么填。规格写入 files.requirement，名称里带计划或 Plan 的写入 files.plan，files.impact 留空。不要把规格填进 impact。写完再跑一次 next.ps1。回复第一句用上面的套件进度。'
    exit 0
  }
}

$steps = @(
  @{ Role = ''; File = '01-meeting.md'; Do = '按 flow-meeting 在共享目录索引里找这条需求的录像并解析。索引里没有录像时，问用户录像路径，或问是否改为只收资料。' }
  @{ Role = ''; File = '02-sources.md'; Do = '按 flow-sources 把已经给出的链接、Figma、Confluence 和 PDF 收成 02-sources.md。还没有任何材料时，问用户要链接或说明没有外部资料。' }
  @{ Role = 'requirement'; File = '04-requirement.md'; Do = '按 flow-impact 对照代码整理需求。已有 Spec 就指向 files.requirement，不要新建空文件。发现冲突就写成问题并停下问用户。' }
  @{ Role = 'impact'; File = '05-impact.md'; Do = '按 flow-impact 写影响点，或把已有影响点文件写入 files.impact。路径对不上就问用户，不要写开发顺序。' }
  @{ Role = 'plan'; File = '06-plan.md'; Do = '按 flow-plan 写开发顺序，或把已有计划写入 files.plan。不要新建一份空的 06 盖住已有文件。写完停下，不要改代码。' }
  @{ Role = 'testcases'; File = '07-testcases.md'; Do = '按 flow-test 整理用例。能对上已有测试命令的标 auto，其余标 manual。runtime 为空不要编造命令。' }
)

$reqStatus = Read-SimpleYaml (Join-Path $dir 'status.yaml')
$skipMeeting = $false
$skipSources = $false
if ($reqStatus.skip) {
  $skipMeeting = [string]$reqStatus.skip.meeting -eq 'skipped'
  $skipSources = [string]$reqStatus.skip.sources -eq 'skipped'
}
$requirementName = Get-RoleFileName $reqStatus 'requirement' '04-requirement.md'
$impactName = Get-RoleFileName $reqStatus 'impact' '05-impact.md'
$planName = Get-RoleFileName $reqStatus 'plan' '06-plan.md'
$requirementPath = Join-Path $dir $requirementName
$impactPath = Join-Path $dir $impactName
$planPath = Join-Path $dir $planName
$impactIsAlias = ($impactName -eq $requirementName) -or ($impactName -eq $planName)

if ((Test-Path -LiteralPath $requirementPath) -and -not $skipMeeting -and -not (Test-Path -LiteralPath (Join-Path $dir '01-meeting.md'))) {
  Progress '已有规格，跳过空的会议纪要和资料摘录'
  AgentStep '本轮就做：共享目录索引里没有这条需求的录像时，把 status.yaml 的 skip.meeting 和 skip.sources 写成 skipped。有录像或链接就先收那些。不要写空的 01、02。做完再跑 next.ps1。回复第一句用上面的套件进度。'
  exit 0
}

foreach ($step in $steps) {
  if ($step.File -eq '01-meeting.md' -and $skipMeeting) { continue }
  if ($step.File -eq '02-sources.md' -and $skipSources) { continue }
  $fileName = $step.File
  if ($step.Role) { $fileName = Get-RoleFileName $reqStatus $step.Role $step.File }
  if ($step.Role -eq 'impact' -and $impactIsAlias) {
    Emit '还差：files.impact 指向的是规格或计划，不是对照代码后的影响点。'
    Progress '对照代码整理影响点（规格还不能当成影响点）'
    AgentStep '本轮就按 flow-impact 对照代码写 05-impact.md。每个修改点写仓库里真实存在的路径，新增的路径标明新增。写完把 files.impact 改成 05-impact.md。不要改规格和计划的原文。回复先说套件进度，再列出改哪些路径，问用户有没有指错。'
    exit 0
  }
  if (-not (Test-Path -LiteralPath (Join-Path $dir $fileName))) {
    Emit "还差：还没有 $fileName。"
    if ($later.Count -gt 0) { Emit '不挡住当前需求，还可以稍后做：'; $later | ForEach-Object { Emit "- $_" } }
    AgentStep $step.Do
    exit 0
  }
}

if (-not (Test-Path -LiteralPath $planPath)) {
  Emit "还差：还没有 $planName。"
  AgentStep '按 flow-plan 写开发顺序。不要改代码。'
  exit 0
}
$planText = [System.IO.File]::ReadAllText($planPath)
if ($planText -notmatch '(?m)^- \[ \]') {
  Emit '还差：计划是叙述，没有未完成的 - [ ]，还不能据此改代码。'
  Progress '把现有计划整理成可执行任务（还不能改代码）'
  AgentStep '本轮就通读现有计划，抽出可执行步骤，追加到该文件末尾，标题用「套件任务」，每行一条 - [ ]。不要改原有叙述，不要改代码。回复先说套件进度，再把追加的任务列出来，问用户有没有漏。'
  exit 0
}
if ($confirmed -ne 'true') {
  Emit '还差：要改代码了，但分支和提交规范还没按这个仓库确认。'
  AgentStep '现在就按 skills/flow-conventions/SKILL.md 收集并逐项问用户。不要让用户复述这句话，也不要改代码。'
  exit 0
}
$branchOn = ''
if ($project.conventions -and $project.conventions.branch) {
  $branchOn = [string]$project.conventions.branch.enabled
}
Emit '套件进度：按任务改代码'
Emit '还差：开发顺序里还有没勾上的步骤。'
if ($branchOn -eq 'true') {
  $pattern = 'feature/{id}'
  if ($project.conventions.branch.pattern) { $pattern = [string]$project.conventions.branch.pattern }
  $branch = $pattern.Replace('{id}', $current)
  Emit "改代码前要先在对应仓库使用分支 $branch 。"
  AgentStep "按 flow-implement 做计划里第一个还没勾上的任务。开始前先建好或切到分支 $branch ，只做这一步。做完把验证结果告诉用户，不要接着做下一步。"
}
else {
  Emit '这个项目已关掉自动建分支，停在当前分支上改。'
  AgentStep '按 flow-implement 做计划里第一个还没勾上的任务。不要新建分支。只做这一步，做完把验证结果告诉用户。'
}
exit 0

$casePath = Join-Path $dir '07-testcases.md'
$caseText = [System.IO.File]::ReadAllText($casePath)
if ($caseText -match '未执行') {
  if (-not $runtimeTest) {
    Emit '还差：用例还没跑，而且 project.yaml 里没有测试命令。'
    Ask '用例还不能自动跑。后端和前端在本地怎么启动，测试命令是哪一条？口令不要发在对话里，只给 Bitwarden 条目名。'
    exit 0
  }
  Emit '还差：用例写了，但还有未执行的自动项。'
  AgentStep '按 flow-test 执行标了 auto 的用例。没有命令输出就不要写成通过。失败就停下来把现象告诉用户。'
  exit 0
}

Emit '这条需求的文件已经齐，用例也没有挂着未执行。'
if ($later.Count -gt 0) {
  Emit '还可以优化：'
  $later | ForEach-Object { Emit "- $_" }
  AgentStep '做上面还可以优化里的第一条里、不需要用户拍板的那一件。需要用户确认的，改成提问。做完再跑 next.ps1。'
  exit 0
}
Ask '这条需求可以收工。要开下一条时，告诉我标题或工单号。'
exit 0
} finally {
  Save-Next
}
