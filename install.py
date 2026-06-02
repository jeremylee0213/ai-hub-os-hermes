#!/usr/bin/env python3
"""Cross-platform installer for Hermes Web UI.

Installs/updates Hermes Agent, clones or updates this Web UI, prepares a Hermes
profile, writes local .env files, scaffolds Telegram Gateway config, installs
Python dependencies, and optionally verifies the Web UI health endpoint.
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
import time
import urllib.request
from pathlib import Path

DEFAULT_REPO_URL = "https://github.com/aihubos/ai-hub-os-hermes.git"
DEFAULT_PORT = 8788
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


def is_wsl() -> bool:
    return platform.system().lower() == "linux" and "microsoft" in platform.release().lower()


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
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def ensure_dir(path: Path, runner: StepRunner) -> None:
    runner.info(f"mkdir -p {path}")
    if not runner.dry_run:
        path.mkdir(parents=True, exist_ok=True)


def which_python() -> str:
    if is_windows():
        for name in ("py", "python", "python3"):
            found = shutil.which(name)
            if found:
                return found
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            return found
    raise SystemExit("Python 3 not found. Install Python 3.8+ and rerun.")


def python_cmd() -> list[str]:
    exe = which_python()
    if Path(exe).name.lower() == "py.exe" or Path(exe).name.lower() == "py":
        return [exe, "-3"]
    return [exe]


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if is_windows() else "bin/python")


def git_cmd() -> str:
    git = shutil.which("git")
    if git:
        return git
    raise SystemExit("Git not found. Install Git, then rerun this installer.")


def install_or_update_hermes(runner: StepRunner, skip: bool = False) -> None:
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
        runner.run([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "iex (irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1)"])
    else:
        sh = shutil.which("bash") or "/bin/bash"
        runner.run([sh, "-c", "curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"])


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


def clone_or_update_webui(repo_url: str, install_path: Path, runner: StepRunner) -> Path:
    webui_dir = install_path / "hermes-for-web"
    current = Path(__file__).resolve().parent
    if webui_dir.exists() and current == webui_dir.resolve():
        runner.ok(f"Running inside target Web UI repo: {webui_dir}")
        return webui_dir

    ensure_dir(install_path, runner)
    git = git_cmd()
    if (webui_dir / ".git").exists():
        runner.ok(f"Web UI repo exists: {webui_dir}")
        runner.run([git, "-C", str(webui_dir), "pull", "--ff-only"])
    else:
        runner.run([git, "clone", repo_url, str(webui_dir)])
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
        f"HERMES_WEBUI_HOST=127.0.0.1",
        f"HERMES_WEBUI_PORT={port}",
        f"HERMES_WEBUI_STATE_DIR={active_home / 'webui'}",
        f"HERMES_WEBUI_DEFAULT_WORKSPACE={active_home / 'workspace'}",
    ]
    if agent_dir:
        lines.insert(1, f"HERMES_WEBUI_AGENT_DIR={agent_dir}")
    write_if_missing(webui_dir / ".env", "\n".join(lines) + "\n", runner)


def scaffold_telegram(active_home: Path, runner: StepRunner) -> None:
    text = """# Telegram Gateway scaffold
# Create a bot with @BotFather, then fill these values.
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USERS=
# Optional:
# TELEGRAM_HOME_CHANNEL=
# TELEGRAM_PROXY=
"""
    write_if_missing(active_home / ".env", text, runner, append=True)


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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Install Hermes Agent + Hermes Web UI + Telegram Gateway scaffold.")
    p.add_argument("--install-path", help="Install path. Default: ~/HermesHub or Windows LOCALAPPDATA\\HermesHub")
    p.add_argument("--agent-name", help="Hermes profile/agent name. Default: default")
    p.add_argument("--repo-url", default=DEFAULT_REPO_URL, help=f"Web UI repo URL. Default: {DEFAULT_REPO_URL}")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Web UI port. Default: {DEFAULT_PORT}")
    p.add_argument("--yes", action="store_true", help="Use defaults for missing answers.")
    p.add_argument("--skip-hermes-install", action="store_true", help="Do not run official Hermes installer if hermes is missing.")
    p.add_argument("--no-verify", action="store_true", help="Skip temporary Web UI health check.")
    p.add_argument("--dry-run", action="store_true", help="Print actions without changing files.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    runner = StepRunner(args.dry_run)
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
    scaffold_telegram(active_home, runner)
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

    print("\nDone.")
    print(f"Web UI repo : {webui_dir}")
    print(f"Hermes home : {active_home}")
    print(f"Start Web UI: {webui_dir / ('start.ps1' if is_windows() else 'start.sh')} {args.port}")
    print(f"Open       : http://127.0.0.1:{args.port}")
    print("Telegram  : fill TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USERS in")
    print(f"            {active_home / '.env'}")
    print("            then run: hermes gateway setup && hermes gateway")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
