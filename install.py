#!/usr/bin/env python3
"""Cross-platform one-shot installer for Hermes Web UI.

Designed for Codex-style usage: user pastes the GitHub URL and asks to install.
The installer bootstraps Hermes Agent, gets this Web UI via git or ZIP fallback,
prepares a Hermes profile, writes .env files, optionally installs Telegram
Desktop, and verifies the Web UI health endpoint.
"""
from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_REPO_URL = "https://github.com/aihubos/ai-hub-os-hermes.git"
DEFAULT_ZIP_URL = "https://github.com/aihubos/ai-hub-os-hermes/archive/refs/heads/main.zip"
DEFAULT_PORT = 8788
MIN_PYTHON = (3, 8)
PROFILE_RE = re.compile(r"[^a-z0-9_-]+")


class StepRunner:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def info(self, msg: str) -> None:
        print(f"[--] {msg}")

    def ok(self, msg: str) -> None:
        print(f"[ok] {msg}")

    def warn(self, msg: str) -> None:
        print(f"[!!] {msg}")

    def run(self, cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess:
        pretty = " ".join(quote(c) for c in cmd)
        if cwd:
            pretty = f"(cd {cwd} && {pretty})"
        self.info(pretty)
        if self.dry_run:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, text=True, check=check)


def quote(s: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:=@+-]+", s):
        return s
    return repr(s)


def is_windows() -> bool:
    return platform.system().lower() == "windows"


def is_macos() -> bool:
    return platform.system().lower() == "darwin"


def is_wsl() -> bool:
    return platform.system().lower() == "linux" and "microsoft" in platform.release().lower()


def refresh_path() -> None:
    extras: list[str] = []
    home = Path.home()
    if is_windows():
        local = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
        extras += [
            str(local / "Microsoft" / "WindowsApps"),
            str(local / "Programs" / "Python" / "Python312"),
            str(local / "Programs" / "Python" / "Python311"),
            str(local / "Programs" / "Git" / "cmd"),
            str(Path("C:/Program Files/Git/cmd")),
            str(Path("C:/Program Files/Git/bin")),
        ]
    else:
        extras += [str(home / ".local" / "bin"), "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
    old = os.environ.get("PATH", "")
    os.environ["PATH"] = os.pathsep.join([p for p in extras if p]) + os.pathsep + old


def default_install_path() -> Path:
    if is_windows():
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "HermesHub"
    return Path.home() / "HermesHub"


def default_hermes_base_home() -> Path:
    if is_windows():
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "hermes"
    return Path.home() / ".hermes"


def sanitize_agent_name(name: str) -> str:
    s = (name or "default").strip().lower()
    s = PROFILE_RE.sub("-", s).strip("-_")
    if not s:
        s = "default"
    if not re.match(r"^[a-z0-9]", s):
        s = f"h-{s}"
    return s[:64]


def ask(prompt: str, default: str) -> str:
    text = f"{prompt} [{default}]: "
    if sys.stdin.isatty():
        try:
            value = input(text).strip()
            return value or default
        except EOFError:
            return default
    if not is_windows():
        try:
            with open("/dev/tty", "r", encoding="utf-8", errors="ignore") as tty:
                print(text, end="", flush=True)
                value = tty.readline().strip()
                return value or default
        except OSError:
            pass
    print(f"[--] {prompt}: using default {default} (non-interactive)")
    return default


def ensure_dir(path: Path, runner: StepRunner) -> None:
    runner.info(f"mkdir -p {path}")
    if not runner.dry_run:
        path.mkdir(parents=True, exist_ok=True)


def python_command_is_usable(cmd: list[str]) -> bool:
    code = f"import sys; raise SystemExit(0 if sys.version_info >= ({MIN_PYTHON[0]}, {MIN_PYTHON[1]}) else 1)"
    try:
        result = subprocess.run(
            cmd + ["-c", code],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except OSError:
        return False


def which_python() -> str:
    refresh_path()
    if is_windows():
        for name in ("py", "python", "python3"):
            found = shutil.which(name)
            if found and python_command_is_usable([found] + (["-3"] if Path(found).name.lower() in {"py.exe", "py"} else [])):
                return found
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found and python_command_is_usable([found]):
            return found
    raise SystemExit("Python 3 not found. Rerun install.sh/install.ps1 so the bootstrapper can install it.")


def python_cmd() -> list[str]:
    exe = which_python()
    if Path(exe).name.lower() in {"py.exe", "py"}:
        return [exe, "-3"]
    return [exe]


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if is_windows() else "bin/python")


def command_exists(name: str) -> bool:
    refresh_path()
    return shutil.which(name) is not None


def usable_git_cmd() -> str | None:
    refresh_path()
    git = shutil.which("git")
    if not git:
        return None
    try:
        result = subprocess.run([git, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True, check=False)
        if result.returncode == 0:
            return git
    except OSError:
        return None
    return None


def install_homebrew_if_missing(runner: StepRunner) -> None:
    if not is_macos() or command_exists("brew"):
        return
    runner.warn("Homebrew not found. Installing Homebrew to improve one-shot setup...")
    runner.run(["/bin/bash", "-c", "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"], check=False)
    refresh_path()


def install_git_if_possible(runner: StepRunner) -> None:
    git = usable_git_cmd()
    if git:
        runner.ok(f"Git found: {git}")
        return
    if is_macos():
        install_homebrew_if_missing(runner)
        if command_exists("brew"):
            runner.run(["brew", "install", "git"], check=False)
            refresh_path()
        git = usable_git_cmd()
        if git:
            runner.ok(f"Git installed: {git}")
            return
        runner.warn("Git not available; using GitHub ZIP fallback.")
        return
    if is_windows() and command_exists("winget"):
        runner.run(["winget", "install", "--id", "Git.Git", "-e", "--accept-source-agreements", "--accept-package-agreements"], check=False)
        refresh_path()
        git = usable_git_cmd()
        if git:
            runner.ok(f"Git installed: {git}")
            return
    runner.warn("Git not available; using GitHub ZIP fallback.")


def git_cmd() -> str | None:
    return usable_git_cmd()


def install_or_update_hermes(runner: StepRunner, skip: bool = False) -> None:
    refresh_path()
    hermes = shutil.which("hermes")
    if skip:
        runner.warn("Skipping Hermes Agent install/update (--skip-hermes-install).")
        return
    if hermes:
        runner.ok(f"Hermes CLI found: {hermes}")
        runner.run([hermes, "--help"], check=False)
        return

    runner.warn("Hermes CLI not found. Running official Hermes Agent installer.")
    if is_windows():
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if not ps:
            raise SystemExit("PowerShell not found; cannot run Windows Hermes installer.")
        runner.run([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "iex (irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1)"], check=False)
    else:
        sh = shutil.which("bash") or "/bin/bash"
        runner.run([sh, "-c", "curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"], check=False)
    refresh_path()
    hermes = shutil.which("hermes")
    if hermes:
        runner.ok(f"Hermes CLI installed: {hermes}")
    else:
        runner.warn("Hermes CLI still not on PATH. Continuing; Web UI can still be prepared.")


def discover_agent_dir(install_path: Path, hermes_base: Path) -> Path | None:
    candidates = [
        Path(os.environ.get("HERMES_WEBUI_AGENT_DIR", "")) if os.environ.get("HERMES_WEBUI_AGENT_DIR") else None,
        hermes_base / "hermes-agent",
        install_path / "hermes-agent",
        Path.home() / ".hermes" / "hermes-agent",
        Path.home() / "hermes-agent",
    ]
    for c in candidates:
        if c and (c / "run_agent.py").exists():
            return c.resolve()
    return None


def download_zip_webui(webui_dir: Path, runner: StepRunner, zip_url: str = DEFAULT_ZIP_URL) -> Path:
    runner.info(f"Downloading Web UI ZIP fallback: {zip_url}")
    if runner.dry_run:
        return webui_dir.resolve()
    parent = webui_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    if webui_dir.exists() and any(webui_dir.iterdir()):
        backup = webui_dir.with_name(f"{webui_dir.name}.bak-{int(time.time())}")
        runner.warn(f"Existing non-git Web UI dir backed up: {backup}")
        shutil.move(str(webui_dir), str(backup))
    with tempfile.TemporaryDirectory() as td:
        zip_path = Path(td) / "webui.zip"
        curl = shutil.which("curl")
        if curl:
            try:
                runner.run([curl, "-fsSL", zip_url, "-o", str(zip_path)])
            except subprocess.CalledProcessError:
                runner.warn("curl ZIP download failed; retrying with Python urllib.")
                urllib.request.urlretrieve(zip_url, zip_path)
        else:
            urllib.request.urlretrieve(zip_url, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(td)
        extracted = next(p for p in Path(td).iterdir() if p.is_dir())
        shutil.move(str(extracted), str(webui_dir))
    return webui_dir.resolve()


def clone_or_update_webui(repo_url: str, install_path: Path, runner: StepRunner) -> Path:
    webui_dir = install_path / "hermes-for-web"
    current = Path(__file__).resolve().parent
    if (current / "server.py").exists() and (current / "install.py").exists() and not str(current).startswith(tempfile.gettempdir()):
        runner.ok(f"Running inside local Web UI repo: {current}")
        return current.resolve()

    ensure_dir(install_path, runner)
    install_git_if_possible(runner)
    git = git_cmd()
    if git and (webui_dir / ".git").exists():
        runner.ok(f"Web UI repo exists: {webui_dir}")
        result = runner.run([git, "-C", str(webui_dir), "pull", "--ff-only"], check=False)
        if result.returncode != 0:
            runner.warn("Git pull failed; using GitHub ZIP fallback.")
            download_zip_webui(webui_dir, runner)
    elif git:
        if webui_dir.exists() and any(webui_dir.iterdir()):
            runner.warn(f"Target exists but is not a git repo; using it as-is: {webui_dir}")
        else:
            try:
                runner.run([git, "clone", repo_url, str(webui_dir)])
            except subprocess.CalledProcessError:
                runner.warn("Git clone failed; using GitHub ZIP fallback.")
                download_zip_webui(webui_dir, runner)
    else:
        download_zip_webui(webui_dir, runner)
    return webui_dir.resolve()


def prepare_profile(agent_name: str, hermes_base: Path, runner: StepRunner) -> Path:
    if agent_name == "default":
        active_home = hermes_base
    else:
        active_home = hermes_base / "profiles" / agent_name
    for sub in ("memories", "sessions", "skills", "skins", "logs", "plans", "workspace", "cron", "webui"):
        ensure_dir(active_home / sub, runner)
    ensure_dir(hermes_base, runner)

    marker = hermes_base / "active_profile"
    if agent_name == "default":
        runner.info(f"default profile selected; leaving {marker} unchanged")
    else:
        runner.info(f"write {marker} = {agent_name}")
        if not runner.dry_run:
            marker.write_text(agent_name + "\n", encoding="utf-8")
    return active_home.resolve()


def write_if_missing(path: Path, text: str, runner: StepRunner, *, append: bool = False) -> None:
    runner.info(("append " if append else "write ") + str(path))
    if runner.dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if append and path.exists():
        existing = path.read_text(encoding="utf-8", errors="ignore")
        if "TELEGRAM_BOT_TOKEN" in existing:
            runner.ok(f"Telegram scaffold already present: {path}")
            return
        path.write_text(existing.rstrip() + "\n\n" + text, encoding="utf-8")
    else:
        if path.exists():
            backup = path.with_suffix(path.suffix + f".bak-{int(time.time())}")
            shutil.copy2(path, backup)
            runner.warn(f"Existing file backed up: {backup}")
        path.write_text(text, encoding="utf-8")


def write_env(webui_dir: Path, agent_dir: Path | None, hermes_base: Path, active_home: Path, port: int, runner: StepRunner) -> None:
    lines = [
        "# Generated by install.py. Edit as needed.",
        f"HERMES_BASE_HOME={hermes_base}",
        f"HERMES_HOME={active_home}",
        "HERMES_WEBUI_HOST=127.0.0.1",
        f"HERMES_WEBUI_PORT={port}",
        f"HERMES_WEBUI_STATE_DIR={active_home / 'webui'}",
        f"HERMES_WEBUI_DEFAULT_WORKSPACE={active_home / 'workspace'}",
    ]
    if agent_dir:
        lines.insert(1, f"HERMES_WEBUI_AGENT_DIR={agent_dir}")
    write_if_missing(webui_dir / ".env", "\n".join(lines) + "\n", runner)


def env_has_telegram_credentials(path: Path) -> bool:
    if not path.exists():
        return False
    vals: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
    return bool(vals.get("TELEGRAM_BOT_TOKEN")) and bool(vals.get("TELEGRAM_ALLOWED_USERS"))


def scaffold_telegram(active_home: Path, runner: StepRunner) -> bool:
    text = """# Telegram Gateway scaffold
# Create a bot with @BotFather, then fill these values.
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USERS=
# Optional:
# TELEGRAM_HOME_CHANNEL=
# TELEGRAM_PROXY=
"""
    env_path = active_home / ".env"
    configured = env_has_telegram_credentials(env_path)
    if configured:
        runner.ok("Telegram credentials already present; keeping existing values.")
        return True
    write_if_missing(env_path, text, runner, append=True)
    return False


def install_telegram_desktop(runner: StepRunner, skip: bool = False) -> None:
    if skip:
        runner.warn("Skipping Telegram Desktop install/check (--skip-telegram-desktop).")
        return
    if is_macos():
        if Path("/Applications/Telegram.app").exists() or Path.home().joinpath("Applications/Telegram.app").exists():
            runner.ok("Telegram Desktop already installed; skipping.")
            return
        install_homebrew_if_missing(runner)
        if command_exists("brew"):
            runner.run(["brew", "install", "--cask", "telegram"], check=False)
            return
        runner.warn("Telegram Desktop not installed and Homebrew unavailable; skipping app install.")
    elif is_windows():
        if command_exists("winget"):
            found = runner.run(["winget", "list", "--id", "Telegram.TelegramDesktop", "-e"], check=False)
            if found.returncode == 0:
                runner.ok("Telegram Desktop already installed; skipping.")
                return
            runner.run(["winget", "install", "--id", "Telegram.TelegramDesktop", "-e", "--accept-source-agreements", "--accept-package-agreements"], check=False)
        else:
            runner.warn("winget unavailable; skipping Telegram Desktop app install.")
    else:
        runner.info("Telegram Desktop app auto-install is only handled on macOS/Windows; skipping.")


def install_webui_deps(webui_dir: Path, runner: StepRunner) -> Path:
    venv = webui_dir / ".venv"
    py = venv_python(venv)
    if not py.exists():
        runner.run(python_cmd() + ["-m", "venv", str(venv)])
    runner.run([str(py), "-m", "pip", "install", "--upgrade", "pip"])
    req = webui_dir / "requirements.txt"
    if req.exists():
        runner.run([str(py), "-m", "pip", "install", "-r", str(req)])
    else:
        runner.run([str(py), "-m", "pip", "install", "pyyaml"])
    return py


def wait_health(port: int, timeout: int = 20) -> bool:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                body = r.read().decode("utf-8", "ignore")
                if '"status"' in body:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def verify_webui(webui_dir: Path, py: Path, env: dict[str, str], port: int, runner: StepRunner) -> None:
    if runner.dry_run:
        runner.info("dry-run: skip Web UI launch verification")
        return
    if port_open(port):
        runner.warn(f"Port {port} is already in use; skipping temporary health check.")
        return
    log = webui_dir / ".install-verify.log"
    runner.info(f"temporary launch for /health check on port {port}")
    with log.open("w", encoding="utf-8") as out:
        proc = subprocess.Popen([str(py), str(webui_dir / "server.py")], cwd=str(webui_dir), env=env, stdout=out, stderr=subprocess.STDOUT)
    try:
        if wait_health(port):
            runner.ok(f"Web UI health check passed: http://127.0.0.1:{port}/health")
        else:
            runner.warn(f"Web UI health check did not pass. See {log}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def maybe_start_gateway(active_home: Path, runner: StepRunner, auto_start: bool) -> None:
    if not auto_start:
        return
    if not env_has_telegram_credentials(active_home / ".env"):
        runner.warn("Telegram token/user ID missing; gateway auto-start skipped.")
        return
    refresh_path()
    hermes = shutil.which("hermes")
    if not hermes:
        runner.warn("Hermes CLI not found on PATH; gateway auto-start skipped.")
        return
    env = os.environ.copy()
    env["HERMES_HOME"] = str(active_home)
    runner.run([hermes, "gateway", "status"], env=env, check=False)
    runner.run([hermes, "gateway", "install"], env=env, check=False)
    runner.run([hermes, "gateway", "start"], env=env, check=False)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Install Hermes Agent + Hermes Web UI + Telegram Gateway scaffold.")
    p.add_argument("--install-path", help="Install path. Default: ~/HermesHub or Windows LOCALAPPDATA\\HermesHub")
    p.add_argument("--agent-name", help="Hermes profile/agent name. Default: default")
    p.add_argument("--repo-url", default=DEFAULT_REPO_URL, help=f"Web UI repo URL. Default: {DEFAULT_REPO_URL}")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Web UI port. Default: {DEFAULT_PORT}")
    p.add_argument("--yes", action="store_true", help="Use defaults for missing answers.")
    p.add_argument("--skip-hermes-install", action="store_true", help="Do not run official Hermes installer if hermes is missing.")
    p.add_argument("--skip-telegram-desktop", action="store_true", help="Do not check/install Telegram Desktop app.")
    p.add_argument("--auto-start-gateway", action="store_true", help="If Telegram env values exist, install/start Hermes gateway service.")
    p.add_argument("--no-verify", action="store_true", help="Skip temporary Web UI health check.")
    p.add_argument("--dry-run", action="store_true", help="Print actions without changing files.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    runner = StepRunner(args.dry_run)
    refresh_path()
    runner.info(f"Detected platform: {platform.system()}" + (" (WSL)" if is_wsl() else ""))

    default_path = str(default_install_path())
    install_path = Path(args.install_path or (default_path if args.yes else ask("Install path", default_path))).expanduser().resolve()
    agent_name_raw = args.agent_name or ("default" if args.yes else ask("Agent name", "default"))
    agent_name = sanitize_agent_name(agent_name_raw)
    if agent_name != agent_name_raw.strip().lower():
        runner.warn(f"Agent name sanitized: {agent_name_raw!r} -> {agent_name!r}")

    hermes_base = Path(os.environ.get("HERMES_BASE_HOME") or default_hermes_base_home()).expanduser().resolve()

    install_or_update_hermes(runner, skip=args.skip_hermes_install)
    webui_dir = clone_or_update_webui(args.repo_url, install_path, runner)
    active_home = prepare_profile(agent_name, hermes_base, runner)
    agent_dir = discover_agent_dir(install_path, hermes_base)
    if agent_dir:
        runner.ok(f"Hermes agent dir: {agent_dir}")
    else:
        runner.warn("Hermes agent checkout not found yet; Web UI .env will omit HERMES_WEBUI_AGENT_DIR.")

    write_env(webui_dir, agent_dir, hermes_base, active_home, args.port, runner)
    telegram_ready = scaffold_telegram(active_home, runner)
    install_telegram_desktop(runner, skip=args.skip_telegram_desktop)
    py = install_webui_deps(webui_dir, runner)

    env = os.environ.copy()
    env.update({
        "HERMES_BASE_HOME": str(hermes_base),
        "HERMES_HOME": str(active_home),
        "HERMES_WEBUI_HOST": "127.0.0.1",
        "HERMES_WEBUI_PORT": str(args.port),
        "HERMES_WEBUI_STATE_DIR": str(active_home / "webui"),
        "HERMES_WEBUI_DEFAULT_WORKSPACE": str(active_home / "workspace"),
    })
    if agent_dir:
        env["HERMES_WEBUI_AGENT_DIR"] = str(agent_dir)

    if not args.no_verify:
        verify_webui(webui_dir, py, env, args.port, runner)
    maybe_start_gateway(active_home, runner, args.auto_start_gateway)

    print("\nDone.")
    print(f"Web UI repo : {webui_dir}")
    print(f"Hermes home : {active_home}")
    print(f"Start Web UI: {webui_dir / ('start.ps1' if is_windows() else 'start.sh')} {args.port}")
    print(f"Open       : http://127.0.0.1:{args.port}")
    if telegram_ready:
        print("Telegram  : token/user ID already found. Use --auto-start-gateway to start gateway automatically.")
    else:
        print("Telegram  : BotFather token and Telegram user ID are still manual one-time secrets.")
        print(f"            Fill them in: {active_home / '.env'}")
        print("            then run: hermes gateway setup && hermes gateway")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
