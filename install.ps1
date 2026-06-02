$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Installer = Join-Path $ScriptDir "install.py"

if (Get-Command py -ErrorAction SilentlyContinue) {
  & py -3 $Installer @args
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  & python $Installer @args
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
  & python3 $Installer @args
} else {
  Write-Error "Python 3 is required. Please install Python 3.8+ and rerun."
}
