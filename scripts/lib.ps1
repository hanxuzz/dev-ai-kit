# Shared helpers for install.ps1 and validate.ps1. ASCII only.

function Read-SimpleYaml {
  param([Parameter(Mandatory = $true)][string]$Path)
  $root = @{}
  $stack = New-Object System.Collections.Generic.List[object]
  $stack.Add([pscustomobject]@{ Indent = -1; Node = $root })
  foreach ($raw in [System.IO.File]::ReadAllLines($Path)) {
    $line = $raw -replace '\t', '  '
    if ($line -match '^\s*$' -or $line -match '^\s*#') { continue }
    if ($line -notmatch '^(\s*)([A-Za-z0-9_.-]+):\s*(.*)$') { continue }
    $indent = $Matches[1].Length
    $key = $Matches[2]
    $rawValue = $Matches[3].Trim()
    $nested = $false
    $value = ''
    if ($rawValue -eq '' -or $rawValue.StartsWith('#')) { $nested = $true }
    else {
      $value = ($rawValue -replace '\s+#.*$', '').Trim()
      if ($value -eq '""' -or $value -eq "''") { $value = '' }
      else { $value = $value.Trim('"').Trim("'") }
    }
    while ($stack.Count -gt 1 -and $indent -le $stack[$stack.Count - 1].Indent) {
      $stack.RemoveAt($stack.Count - 1)
    }
    $parent = $stack[$stack.Count - 1].Node
    if ($nested) {
      $child = @{}
      $parent[$key] = $child
      $stack.Add([pscustomobject]@{ Indent = $indent; Node = $child })
    }
    else {
      $parent[$key] = $value
    }
  }
  return $root
}

function Resolve-RequirementsRoot {
  param($DocsRoot, $Project)
  $name = 'requirements'
  if ($Project.docs -and $Project.docs.requirements_dir) {
    $name = [string]$Project.docs.requirements_dir
  }
  if (-not $name) { $name = 'requirements' }
  if ($name -match '[\\/]' -or $name -eq '.' -or $name -eq '..') { return $null }
  return (Join-Path $DocsRoot $name)
}

function Resolve-DocsRoot {
  param($Workspace, $Project, $Local)
  $mode = [string]$Project.docs.mode
  $path = [string]$Project.docs.path
  if (-not $mode -or -not $path) { return $null }
  if ($mode -eq 'share') {
    $share = ''
    if ($Local.share) { $share = [string]$Local.share.path }
    if (-not $share) { return $null }
    if ([System.IO.Path]::IsPathRooted($path)) { return $path }
    return (Join-Path $share $path)
  }
  if ([System.IO.Path]::IsPathRooted($path)) { return $path }
  return (Join-Path $Workspace $path)
}

function Get-GitRoot {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return $null }
  $git = Get-Command git -ErrorAction SilentlyContinue
  if (-not $git) { return $null }
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $git.Source
  $psi.Arguments = "-C `"$Path`" rev-parse --show-toplevel"
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true
  $proc = [System.Diagnostics.Process]::Start($psi)
  $stdout = $proc.StandardOutput.ReadToEnd()
  $null = $proc.StandardError.ReadToEnd()
  $proc.WaitForExit()
  if ($proc.ExitCode -ne 0) { return $null }
  return $stdout.Trim()
}

function Write-Utf8 {
  param([string]$Path, [string]$Content)
  $dir = Split-Path -Parent $Path
  if ($dir -and -not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
  }
  $utf8 = New-Object System.Text.UTF8Encoding $false
  [System.IO.File]::WriteAllText($Path, $Content.Replace("`n", "`r`n"), $utf8)
}

function Test-CodeRoot {
  param([string]$Dir)
  $markers = @(
    '.git', 'package.json', 'pom.xml', 'build.gradle', 'build.gradle.kts',
    'go.mod', 'Cargo.toml', 'pyproject.toml', 'composer.json'
  )
  foreach ($name in $markers) {
    if (Test-Path -LiteralPath (Join-Path $Dir $name)) { return $true }
  }
  $csproj = Get-ChildItem -LiteralPath $Dir -Filter '*.csproj' -File -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($csproj) { return $true }
  $sln = Get-ChildItem -LiteralPath $Dir -Filter '*.sln' -File -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($sln) { return $true }
  return $false
}
