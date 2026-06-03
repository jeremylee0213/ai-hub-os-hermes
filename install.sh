#!/usr/bin/env bash
set -euo pipefail

REPO_RAW_BASE="${HERMES_WEBUI_RAW_BASE:-https://raw.githubusercontent.com/aihubos/ai-hub-os-hermes/main}"
SOURCE_PATH="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR=""
INSTALLER=""
TMP_INSTALLER=""
BOOTSTRAP_DRY_RUN=false
BOOTSTRAP_HELP=false
BOOTSTRAP_SKIP_HERMES=false
BOOTSTRAP_SKIP_PREFLIGHT=false
BOOTSTRAP_YES=false

info() { printf '[--] %s\n' "$*"; }
ok() { printf '[ok] %s\n' "$*"; }
warn() { printf '[!!] %s\n' "$*"; }

for arg in "$@"; do
  case "$arg" in
    --dry-run) BOOTSTRAP_DRY_RUN=true ;;
    --help|-h) BOOTSTRAP_HELP=true ;;
    --yes) BOOTSTRAP_YES=true ;;
    --skip-preflight) BOOTSTRAP_SKIP_PREFLIGHT=true ;;
    --skip-hermes-install) BOOTSTRAP_SKIP_HERMES=true ;;
  esac
done

print_bootstrap_help() {
  cat <<'EOF'
Hermes Web UI installer bootstrap

Usage:
  curl -fsSL https://raw.githubusercontent.com/aihubos/ai-hub-os-hermes/main/install.sh | bash
  curl -fsSL https://raw.githubusercontent.com/aihubos/ai-hub-os-hermes/main/install.sh | bash -s -- --yes

Common options:
  --yes
  --dry-run
  --skip-preflight
  --skip-hermes-install
  --skip-gpt-oauth
  --skip-telegram-desktop
  --skip-obsidian
  --skip-llm-wiki
  --ai-hub-root PATH
  --no-verify
  --install-path PATH
  --obsidian-path PATH
  --llm-wiki-path PATH
  --agent-name NAME
  --bot-name NAME
  --bot-id ID
EOF
}

confirm_preflight() {
  if [[ "${HERMES_WEBUI_PREFLIGHT_DONE:-}" == "1" ]]; then return 0; fi
  if [[ "$BOOTSTRAP_HELP" == true ]]; then return 0; fi
  cat <<'EOF'

Preflight checklist
 - 인터넷 연결이 되어 있음
 - macOS 터미널 또는 Windows PowerShell을 열 수 있음
 - Codex를 사용할 수 있는 GPT/ChatGPT 계정으로 로그인되어 있음
 - GPT/ChatGPT 웹 설정에서 Codex 기능을 켰음
 - Codex Computer Use 옵션을 켰음
 - 설치 중 관리자 권한/브라우저 로그인 요청을 승인할 수 있음
 - Telegram을 쓸 경우 BotFather 봇과 내 Telegram ID를 준비했음

EOF
  if [[ "$BOOTSTRAP_SKIP_PREFLIGHT" == true || "$BOOTSTRAP_YES" == true || "$BOOTSTRAP_DRY_RUN" == true ]]; then
    export HERMES_WEBUI_PREFLIGHT_DONE=1
    return 0
  fi
  if [[ ! -r /dev/tty ]]; then
    warn "No interactive terminal found; continuing without preflight confirmation."
    export HERMES_WEBUI_PREFLIGHT_DONE=1
    return 0
  fi
  printf '위 항목을 모두 완료했나요? 계속하려면 yes 입력 [no]: ' > /dev/tty
  IFS= read -r answer < /dev/tty || answer=""
  case "$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')" in
    y|yes|ok|done|ready|네|예|응|완료|준비됨)
      export HERMES_WEBUI_PREFLIGHT_DONE=1
      ;;
    *)
      echo "사전 준비가 끝난 뒤 같은 설치 명령을 다시 실행해 주세요." >&2
      exit 1
      ;;
  esac
}

is_usable_python() {
  "$1" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 8) else 1)
PY
}

find_python() {
  local candidate
  for name in python3 python; do
    if command -v "$name" >/dev/null 2>&1; then
      candidate="$(command -v "$name")"
      if is_usable_python "$candidate"; then
        printf '%s\n' "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

ensure_python_macos() {
  if find_python >/dev/null; then return 0; fi
  if [[ "$BOOTSTRAP_HELP" == true ]]; then
    print_bootstrap_help
    exit 0
  fi
  if [[ "$BOOTSTRAP_DRY_RUN" == true ]]; then
    warn "dry-run: Python 3.8+ is missing; would try Hermes installer, Homebrew Python, then Xcode Command Line Tools."
    exit 0
  fi
  warn "Python 3 not found. Trying Hermes Agent official installer first..."
  if [[ "$BOOTSTRAP_SKIP_HERMES" == false ]] && command -v curl >/dev/null 2>&1; then
    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash -s -- --non-interactive || true
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
  if [[ "$BOOTSTRAP_HELP" == true ]]; then
    print_bootstrap_help
    exit 0
  fi
  if [[ "$BOOTSTRAP_DRY_RUN" == true ]]; then
    warn "dry-run: Python 3.8+ is missing; would try the official Hermes installer first."
    exit 0
  fi
  if [[ "$BOOTSTRAP_SKIP_HERMES" == false ]] && command -v curl >/dev/null 2>&1; then
    warn "Python 3 not found. Trying Hermes Agent official installer first..."
    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash -s -- --non-interactive || true
    export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
  fi
  if find_python >/dev/null; then return 0; fi
  echo "Python 3 is required. Please install Python 3.8+ and rerun." >&2
  exit 1
}

case "$(uname -s 2>/dev/null || echo unknown)" in
  *) confirm_preflight ;;
esac

case "$(uname -s 2>/dev/null || echo unknown)" in
  Darwin) ensure_python_macos ;;
  *) ensure_python_windows_or_linux ;;
esac

PYTHON="$(find_python)"
ok "Python: $($PYTHON --version 2>&1)"

if [[ -f "$SOURCE_PATH" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "$SOURCE_PATH")" 2>/dev/null && pwd || pwd)"
  if [[ -f "${SCRIPT_DIR}/install.py" && -f "${SCRIPT_DIR}/server.py" ]]; then
    INSTALLER="${SCRIPT_DIR}/install.py"
  fi
fi

if [[ -z "$INSTALLER" ]]; then
  info "install.py not found locally; downloading latest installer..."
  TMP_INSTALLER="$(mktemp -t hermes-webui-install.XXXXXX.py)"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${REPO_RAW_BASE}/install.py" -o "$TMP_INSTALLER"
  else
    "$PYTHON" - <<PY
import urllib.request
urllib.request.urlretrieve('${REPO_RAW_BASE}/install.py', '${TMP_INSTALLER}')
PY
  fi
  INSTALLER="$TMP_INSTALLER"
fi

exec "$PYTHON" "$INSTALLER" "$@"
