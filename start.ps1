$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Launcher = Join-Path $ScriptDir "start.py"

if (Get-Command py -ErrorAction SilentlyContinue) {
  & py -3 $Launcher @args
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  & python $Launcher @args
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
  & python3 $Launcher @args
} else {
  Write-Error "Python 3 is required. Please install Python 3.8+ and rerun."
}
