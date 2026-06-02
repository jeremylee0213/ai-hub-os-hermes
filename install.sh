#!/usr/bin/env bash
set -euo pipefail

REPO_RAW_BASE="${HERMES_WEBUI_RAW_BASE:-https://raw.githubusercontent.com/aihubos/ai-hub-os-hermes/main}"
SOURCE_PATH="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SOURCE_PATH")" 2>/dev/null && pwd || pwd)"
INSTALLER="${SCRIPT_DIR}/install.py"
TMP_INSTALLER=""

info() { printf '[--] %s\n' "$*"; }
ok() { printf '[ok] %s\n' "$*"; }
warn() { printf '[!!] %s\n' "$*"; }

find_python() {
  if command -v python3 >/dev/null 2>&1; then command -v python3; return 0; fi
  if command -v python >/dev/null 2>&1; then command -v python; return 0; fi
  return 1
}

ensure_python_macos() {
  if find_python >/dev/null; then return 0; fi
  warn "Python 3 not found. Trying Hermes Agent official installer first..."
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash || true
  fi
  export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
  if find_python >/dev/null; then return 0; fi

  if command -v brew >/dev/null 2>&1; then
    warn "Installing Python with Homebrew..."
    brew install python
    if find_python >/dev/null; then return 0; fi
  fi

  warn "Requesting Xcode Command Line Tools. A macOS popup may appear."
  xcode-select --install 2>/dev/null || true
  cat >&2 <<'EOF'
Python 3 is still missing.
Please finish the macOS Command Line Tools popup, then run the same command again.
EOF
  exit 1
}

ensure_python_windows_or_linux() {
  if find_python >/dev/null; then return 0; fi
  if command -v curl >/dev/null 2>&1; then
    warn "Python 3 not found. Trying Hermes Agent official installer first..."
    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash || true
    export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
  fi
  if find_python >/dev/null; then return 0; fi
  echo "Python 3 is required. Please install Python 3.8+ and rerun." >&2
  exit 1
}

case "$(uname -s 2>/dev/null || echo unknown)" in
  Darwin) ensure_python_macos ;;
  *) ensure_python_windows_or_linux ;;
esac

PYTHON="$(find_python)"
ok "Python: $($PYTHON --version 2>&1)"

if [[ ! -f "$INSTALLER" ]]; then
  info "install.py not found locally; downloading latest installer..."
  TMP_INSTALLER="$(mktemp -t hermes-webui-install.XXXXXX.py)"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${REPO_RAW_BASE}/install.py" -o "$TMP_INSTALLER"
  elif command -v python3 >/dev/null 2>&1; then
    python3 - <<PY
import urllib.request
urllib.request.urlretrieve('${REPO_RAW_BASE}/install.py', '${TMP_INSTALLER}')
PY
  else
    echo "Could not download install.py; curl is required." >&2
    exit 1
  fi
  INSTALLER="$TMP_INSTALLER"
fi

exec "$PYTHON" "$INSTALLER" "$@"
