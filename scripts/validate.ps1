# Validate a project workspace. Exit 0 when usable, 1 when a gate is broken.
param(
  [Parameter(Mandatory = $true)][string]$Workspace
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib.ps1')

$fails = New-Object System.Collections.Generic.List[string]
$warns = New-Object System.Collections.Generic.List[string]

function Add-Fail([string]$Code, [string]$Detail) {
  $fails.Add("FAIL $Code $Detail")
}
function Add-Warn([string]$Code, [string]$Detail) {
  $warns.Add("WARN $Code $Detail")
}

$Workspace = (Resolve-Path -LiteralPath $Workspace).Path
$projectFile = Join-Path $Workspace 'project.yaml'
$localFile = Join-Path $Workspace 'project.local.yaml'

if (-not (Test-Path -LiteralPath $projectFile)) {
  Add-Fail 'no-project-yaml' $projectFile
}
if (-not (Test-Path -LiteralPath $localFile)) {
  Add-Fail 'no-project-local' $localFile
}
if ($fails.Count -gt 0) {
  $fails | ForEach-Object { Write-Output $_ }
  exit 1
}

$project = Read-SimpleYaml $projectFile
$local = Read-SimpleYaml $localFile
$rawProject = [System.IO.File]::ReadAllText($projectFile)
if ($rawProject -match '[A-Za-z]:[\\/]' -or $rawProject -match '\\\\') {
  Add-Fail 'absolute-path-in-project-yaml' 'Put machine paths in project.local.yaml'
}
foreach ($line in ($rawProject -split "`n")) {
  if ($line -match '^\s*(password|passwd|secret|token)\s*:\s*\S+') {
    Add-Fail 'secret-in-project-yaml' $line.Trim()
  }
}

$kit = ''
if ($local.kit) { $kit = [string]$local.kit.path }
if (-not $kit -or -not (Test-Path -LiteralPath (Join-Path $kit 'AGENTS.md'))) {
  Add-Fail 'kit-missing' $kit
}

$mode = ''
$path = ''
if ($project.docs) {
  $mode = [string]$project.docs.mode
  $path = [string]$project.docs.path
}
if ($mode -notin @('local', 'share', 'repo', 'tracked')) {
  Add-Fail 'docs-mode' "got '$mode'"
}
$docsRoot = Resolve-DocsRoot $Workspace $project $local
if (-not $docsRoot) {
  Add-Fail 'docs-root' 'docs.path or share.path is empty'
}
elseif (-not (Test-Path -LiteralPath $docsRoot)) {
  Add-Fail 'docs-root-missing' $docsRoot
}
else {
  $docsRoot = (Resolve-Path -LiteralPath $docsRoot).Path
  $gitRoot = Get-GitRoot $docsRoot
  if ($mode -eq 'local' -and $gitRoot) {
    Add-Fail 'docs-inside-git' "$docsRoot is inside $gitRoot. Use mode tracked when this git repo already commits docs."
  }
  if ($mode -eq 'tracked' -and -not $gitRoot) {
    Add-Fail 'docs-not-tracked' "$docsRoot is not inside a git repo. Use mode local, share, or repo."
  }
  if ($mode -eq 'repo' -and -not $gitRoot) {
    Add-Fail 'docs-repo-not-git' $docsRoot
  }
  $team = Join-Path $docsRoot 'team\background.md'
  if (-not (Test-Path -LiteralPath $team)) {
    Add-Warn 'no-background' $team
  }
}

$stages = @('intake', 'meeting', 'sources', 'questions', 'requirement', 'impact', 'plan', 'build', 'test', 'done')
$questionValues = @('none', 'open', 'confirmed')
$stageFile = @{
  meeting      = '01-meeting.md'
  sources      = '02-sources.md'
  questions    = '03-questions.md'
  requirement  = '04-requirement.md'
  impact       = '05-impact.md'
  plan         = '06-plan.md'
  build        = '06-plan.md'
  test         = '07-testcases.md'
  done         = '07-testcases.md'
}
$afterRequirement = @('requirement', 'impact', 'plan', 'build', 'test', 'done')

$current = ''
if ($local.current) { $current = [string]$local.current }

if ($docsRoot -and (Test-Path -LiteralPath $docsRoot)) {
  $reqRoot = Resolve-RequirementsRoot $docsRoot $project
  if ($reqRoot -and (Test-Path -LiteralPath $reqRoot)) {
    Get-ChildItem -LiteralPath $reqRoot -Directory | ForEach-Object {
      $dir = $_.FullName
      $id = $_.Name
      $statusPath = Join-Path $dir 'status.yaml'
      if (-not (Test-Path -LiteralPath $statusPath)) {
        if ($current -eq $id) { Add-Fail 'no-status' $id }
        else { Add-Warn 'no-status' "$id has files but no status.yaml yet" }
        return
      }
      $status = Read-SimpleYaml $statusPath
      $stage = [string]$status.stage
      $questions = [string]$status.questions
      if ($stages -notcontains $stage) { Add-Fail 'bad-stage' "$id stage=$stage" }
      if ($questionValues -notcontains $questions) { Add-Fail 'bad-questions' "$id questions=$questions" }
      if ($stageFile.ContainsKey($stage)) {
        $need = $stageFile[$stage]
        if (-not (Test-Path -LiteralPath (Join-Path $dir $need))) {
          Add-Fail 'missing-artifact' "$id stage=$stage missing $need"
        }
      }
      if ($questions -eq 'open') {
        if ($stage -ne 'questions') { Add-Fail 'questions-open' "$id stage=$stage; open questions require stage=questions" }
        if (-not (Test-Path -LiteralPath (Join-Path $dir '03-questions.md'))) {
          Add-Fail 'missing-artifact' "$id questions=open missing 03-questions.md"
        }
        foreach ($banned in @('04-requirement.md', '05-impact.md', '06-plan.md')) {
          if (Test-Path -LiteralPath (Join-Path $dir $banned)) {
            Add-Fail 'early-artifact' "$id has $banned while questions=open"
          }
        }
      }
      elseif ($afterRequirement -contains $stage) {
        if (-not (Test-Path -LiteralPath (Join-Path $dir '04-requirement.md'))) {
          Add-Fail 'missing-artifact' "$id missing 04-requirement.md"
        }
        if (@('impact', 'plan', 'build', 'test', 'done') -contains $stage -and -not (Test-Path -LiteralPath (Join-Path $dir '05-impact.md'))) {
          Add-Fail 'missing-artifact' "$id missing 05-impact.md"
        }
      }
      $blocker = [string]$status.blocker
      if ($blocker) { Add-Warn 'blocker' "$id $blocker" }
    }
  }
}

if ($current -and $docsRoot -and (Test-Path -LiteralPath $docsRoot)) {
  $reqRoot = Resolve-RequirementsRoot $docsRoot $project
  $currentDir = Join-Path $reqRoot $current
  if (-not $reqRoot -or -not (Test-Path -LiteralPath $currentDir)) {
    Add-Fail 'current-missing' $current
  }
}

$warns | ForEach-Object { Write-Output $_ }
$fails | ForEach-Object { Write-Output $_ }
if ($fails.Count -gt 0) { exit 1 }
Write-Output 'OK validate'
exit 0
