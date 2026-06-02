param(
    [string]$InstallPath,
    [string]$AgentName,
    [string]$RepoUrl,
    [switch]$SkipHermesInstall,
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = $null

foreach ($candidate in @("python", "python3", "py")) {
    try {
        if ($candidate -eq "py") {
            & py -3 --version *> $null
            if ($LASTEXITCODE -eq 0) { $Python = "py -3"; break }
        } else {
            & $candidate --version *> $null
            if ($LASTEXITCODE -eq 0) { $Python = $candidate; break }
        }
    } catch {}
}

if (-not $Python) {
    throw "Python 3 was not found. Install Python 3.11+ and re-run this script."
}

$argsList = @((Join-Path $ScriptDir "install.py"))
if ($InstallPath) { $argsList += @("--install-path", $InstallPath) }
if ($AgentName) { $argsList += @("--agent-name", $AgentName) }
if ($RepoUrl) { $argsList += @("--repo-url", $RepoUrl) }
if ($SkipHermesInstall) { $argsList += "--skip-hermes-install" }
if ($Yes) { $argsList += "--yes" }

if ($Python -eq "py -3") {
    py -3 @argsList
} else {
    & $Python @argsList
}
