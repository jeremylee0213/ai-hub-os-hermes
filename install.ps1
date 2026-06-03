$ErrorActionPreference = "Stop"
$RawBase = if ($env:HERMES_WEBUI_RAW_BASE) { $env:HERMES_WEBUI_RAW_BASE } else { "https://raw.githubusercontent.com/aihubos/ai-hub-os-hermes/main" }
$BootstrapDryRun = $args -contains "--dry-run"
$BootstrapHelp = ($args -contains "--help") -or ($args -contains "-h")
$BootstrapYes = $args -contains "--yes"
$BootstrapSkipPreflight = $args -contains "--skip-preflight"
$BootstrapSkipHermes = $args -contains "--skip-hermes-install"
$Installer = $null

if ($PSScriptRoot) {
  $LocalInstaller = Join-Path $PSScriptRoot "install.py"
  $LocalServer = Join-Path $PSScriptRoot "server.py"
  if ((Test-Path $LocalInstaller) -and (Test-Path $LocalServer)) {
    $Installer = $LocalInstaller
  }
}

function Show-BootstrapHelp {
  Write-Host "Hermes Web UI installer bootstrap"
  Write-Host ""
  Write-Host "Usage:"
  Write-Host "  iex (irm https://raw.githubusercontent.com/aihubos/ai-hub-os-hermes/main/install.ps1)"
  Write-Host ""
  Write-Host "Common options:"
  Write-Host "  --yes"
  Write-Host "  --dry-run"
  Write-Host "  --skip-preflight"
  Write-Host "  --skip-hermes-install"
  Write-Host "  --skip-gpt-oauth"
  Write-Host "  --skip-telegram-desktop"
  Write-Host "  --skip-obsidian"
  Write-Host "  --skip-llm-wiki"
  Write-Host "  --ai-hub-root PATH"
  Write-Host "  --no-verify"
  Write-Host "  --install-path PATH"
  Write-Host "  --obsidian-path PATH"
  Write-Host "  --llm-wiki-path PATH"
  Write-Host "  --agent-name NAME"
  Write-Host "  --bot-name NAME"
  Write-Host "  --bot-id ID"
}

function Confirm-Preflight {
  if ($env:HERMES_WEBUI_PREFLIGHT_DONE -eq "1") { return }
  if ($BootstrapHelp) { return }

  Write-Host ""
  Write-Host "Preflight checklist"
  Write-Host " - 인터넷 연결이 되어 있음"
  Write-Host " - macOS 터미널 또는 Windows PowerShell을 열 수 있음"
  Write-Host " - Codex를 사용할 수 있는 GPT/ChatGPT 계정으로 로그인되어 있음"
  Write-Host " - GPT/ChatGPT 웹 설정에서 Codex 기능을 켰음"
  Write-Host " - Codex Computer Use 옵션을 켰음"
  Write-Host " - 설치 중 관리자 권한/브라우저 로그인 요청을 승인할 수 있음"
  Write-Host " - Telegram을 쓸 경우 BotFather 봇과 내 Telegram ID를 준비했음"
  Write-Host ""

  if ($BootstrapSkipPreflight -or $BootstrapYes -or $BootstrapDryRun) {
    $env:HERMES_WEBUI_PREFLIGHT_DONE = "1"
    return
  }
  if ([Console]::IsInputRedirected) {
    Write-Host "[!!] No interactive terminal found; continuing without preflight confirmation."
    $env:HERMES_WEBUI_PREFLIGHT_DONE = "1"
    return
  }

  $answer = (Read-Host "위 항목을 모두 완료했나요? 계속하려면 yes 입력 [no]").ToLowerInvariant()
  if (@("y", "yes", "ok", "done", "ready", "네", "예", "응", "완료", "준비됨") -notcontains $answer) {
    throw "사전 준비가 끝난 뒤 같은 설치 명령을 다시 실행해 주세요."
  }
  $env:HERMES_WEBUI_PREFLIGHT_DONE = "1"
}

Confirm-Preflight

function Test-PythonCommand {
  param([string[]]$Command)
  try {
    $exe = $Command[0]
    $cmdArgs = @()
    if ($Command.Length -gt 1) { $cmdArgs = $Command[1..($Command.Length - 1)] }
    & $exe @cmdArgs -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 8) else 1)" 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  }
}

function Find-Python {
  foreach ($cmd in @(@("py", "-3"), @("python"), @("python3"))) {
    $found = Get-Command $cmd[0] -ErrorAction SilentlyContinue
    if (-not $found) { continue }
    if ($found.Source -and $found.Source -like "*\WindowsApps\*" -and -not (Test-PythonCommand $cmd)) {
      continue
    }
    if (Test-PythonCommand $cmd) { return $cmd }
  }
  return $null
}

function Ensure-Python {
  $py = Find-Python
  if ($py) { return $py }

  if ($BootstrapHelp) {
    Show-BootstrapHelp
    exit 0
  }
  if ($BootstrapDryRun) {
    Write-Host "[!!] dry-run: Python 3.8+ is missing; would try Hermes installer, then winget Python."
    exit 0
  }

  if (-not $BootstrapSkipHermes) {
    Write-Host "[!!] Python not found. Trying official Hermes Agent Windows installer first..."
    try {
      iex (irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1)
    } catch {
      Write-Host "[!!] Hermes official installer attempt failed; trying winget Python fallback..."
    }
  }

  $env:Path = "$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Microsoft\WindowsApps;$env:Path"
  $py = Find-Python
  if ($py) { return $py }

  if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host "[--] Installing Python with winget..."
    winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
    $env:Path = "$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Microsoft\WindowsApps;$env:Path"
    $py = Find-Python
    if ($py) { return $py }
  }

  throw "Python 3 is required. Install Python 3.8+ and rerun."
}

$PythonCmd = Ensure-Python
Write-Host "[ok] Python command: $($PythonCmd -join ' ')"

if (-not $Installer) {
  Write-Host "[--] install.py not found locally; downloading latest installer..."
  $Installer = Join-Path $env:TEMP ("hermes-webui-install-{0}.py" -f ([guid]::NewGuid().ToString("N")))
  Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/install.py" -OutFile $Installer
}

$PythonArgs = @()
if ($PythonCmd.Length -gt 1) { $PythonArgs = $PythonCmd[1..($PythonCmd.Length-1)] }
& $PythonCmd[0] @PythonArgs $Installer @args
