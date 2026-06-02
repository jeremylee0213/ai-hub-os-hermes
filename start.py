#!/usr/bin/env python3
"""Cross-platform launcher for Hermes Web UI.

Thin shell/PowerShell wrappers call this file so startup works on macOS, Linux,
WSL2, and native Windows without lsof/pkill/nohup assumptions.
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

DEFAULT_PORT = 8788


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def find_python(repo: Path, agent_dir: Path | None, env: dict[str, str]) -> str:
    if env.get("HERMES_WEBUI_PYTHON"):
        return env["HERMES_WEBUI_PYTHON"]
    for p in [
        agent_dir / "venv" / "bin" / "python" if agent_dir else None,
        agent_dir / "venv" / "Scripts" / "python.exe" if agent_dir else None,
        repo / ".venv" / "bin" / "python",
        repo / ".venv" / "Scripts" / "python.exe",
    ]:
        if p and p.exists():
            return str(p)
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            return found
    raise SystemExit("Python 3 not found. Install Python 3.8+ or run install.py first.")


def discover_agent_dir(repo: Path, env: dict[str, str]) -> Path | None:
    home = Path.home()
    hermes_home = Path(env.get("HERMES_HOME", str(home / ".hermes"))).expanduser()
    candidates = [
        Path(env["HERMES_WEBUI_AGENT_DIR"]).expanduser() if env.get("HERMES_WEBUI_AGENT_DIR") else None,
        hermes_home / "hermes-agent",
        repo.parent / "hermes-agent",
        home / ".hermes" / "hermes-agent",
        home / "hermes-agent",
    ]
    for c in candidates:
        if c and (c / "run_agent.py").exists():
            return c.resolve()
    return None


def venv_python(repo: Path) -> Path:
    return repo / ".venv" / ("Scripts/python.exe" if platform.system().lower() == "windows" else "bin/python")


def ensure_deps(repo: Path, py: str) -> str:
    test = subprocess.run([py, "-c", "import yaml"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if test.returncode == 0:
        return py
    venv = repo / ".venv"
    if not venv.exists():
        subprocess.check_call([py, "-m", "venv", str(venv)])
    vpy = venv_python(repo)
    subprocess.check_call([str(vpy), "-m", "pip", "install", "--upgrade", "pip"])
    req = repo / "requirements.txt"
    if req.exists():
        subprocess.check_call([str(vpy), "-m", "pip", "install", "-r", str(req)])
    else:
        subprocess.check_call([str(vpy), "-m", "pip", "install", "pyyaml"])
    return str(vpy)


def port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


def wait_health(host: str, port: int, timeout: int = 20) -> bool:
    deadline = time.time() + timeout
    url = f"http://{host}:{port}/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                body = r.read().decode("utf-8", "ignore")
                if '"status"' in body:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Start Hermes Web UI.")
    p.add_argument("port", nargs="?", type=int, help=f"Port. Default: env HERMES_WEBUI_PORT or {DEFAULT_PORT}")
    p.add_argument("--host", help="Bind host. Default: env HERMES_WEBUI_HOST or 127.0.0.1")
    p.add_argument("--foreground", action="store_true", help="Run server in foreground instead of background.")
    p.add_argument("--no-deps", action="store_true", help="Do not auto-install Python dependencies.")
    return p.parse_args()


def main() -> int:
    repo = Path(__file__).resolve().parent
    env = os.environ.copy()
    env.update(load_dotenv(repo / ".env"))

    port = int(args.port or env.get("HERMES_WEBUI_PORT") or DEFAULT_PORT)
    host = args.host or env.get("HERMES_WEBUI_HOST") or "127.0.0.1"
    env["HERMES_WEBUI_PORT"] = str(port)
    env["HERMES_WEBUI_HOST"] = host
    env.setdefault("HERMES_HOME", str(Path.home() / ".hermes"))
    env.setdefault("HERMES_WEBUI_STATE_DIR", str(Path(env["HERMES_HOME"]).expanduser() / "webui"))

    agent_dir = discover_agent_dir(repo, env)
    if agent_dir:
        env["HERMES_WEBUI_AGENT_DIR"] = str(agent_dir)
        print(f"[ok] Hermes agent: {agent_dir}")
    else:
        print("[!!] Hermes agent not found. Agent features may not work.")

    py = find_python(repo, agent_dir, env)
    if not args.no_deps:
        py = ensure_deps(repo, py)
    print(f"[ok] Python: {py}")

    if port_open(host, port):
        raise SystemExit(f"Port already in use: {host}:{port}. Stop that process or choose another port.")

    cmd = [py, str(repo / "server.py")]
    print(f"[--] Starting Hermes Web UI on http://{host}:{port}")

    if args.foreground:
        os.execve(py, cmd, env)

    log_dir = Path(env.get("HERMES_WEBUI_STATE_DIR", str(Path.home() / ".hermes" / "webui"))).expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / f"hermes-webui-{port}.log"
    out = log.open("a", encoding="utf-8")
    proc = subprocess.Popen(cmd, cwd=str(repo), env=env, stdout=out, stderr=subprocess.STDOUT)

    if wait_health(host, port):
        print(f"[ok] Server is healthy: http://{host}:{port}")
    else:
        print(f"[!!] Health check did not pass yet. Log: {log}")
    print(f"PID: {proc.pid}")
    print(f"Log: {log}")
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(main())
