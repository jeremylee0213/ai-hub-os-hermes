$ErrorActionPreference = "Stop"
$RawBase = if ($env:HERMES_WEBUI_RAW_BASE) { $env:HERMES_WEBUI_RAW_BASE } else { "https://raw.githubusercontent.com/aihubos/ai-hub-os-hermes/main" }
$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$Installer = Join-Path $ScriptDir "install.py"

function Find-Python {
  if (Get-Command py -ErrorAction SilentlyContinue) { return @("py", "-3") }
  if (Get-Command python -ErrorAction SilentlyContinue) { return @("python") }
  if (Get-Command python3 -ErrorAction SilentlyContinue) { return @("python3") }
  return $null
}

function Ensure-Python {
  $py = Find-Python
  if ($py) { return $py }

  Write-Host "[!!] Python not found. Trying official Hermes Agent Windows installer first..."
  try {
    iex (irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1)
  } catch {
    Write-Host "[!!] Hermes official installer attempt failed; trying winget Python fallback..."
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

if (!(Test-Path $Installer)) {
  Write-Host "[--] install.py not found locally; downloading latest installer..."
  $Installer = Join-Path $env:TEMP ("hermes-webui-install-{0}.py" -f ([guid]::NewGuid().ToString("N")))
  Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/install.py" -OutFile $Installer
}

$PythonArgs = @()
if ($PythonCmd.Length -gt 1) { $PythonArgs = $PythonCmd[1..($PythonCmd.Length-1)] }
& $PythonCmd[0] @PythonArgs $Installer @args
