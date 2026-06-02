#!/usr/bin/env python3
"""Cross-platform launcher for Hermes Web UI.

This is the Windows/macOS/Linux equivalent of start.sh. It loads `.env`, prepares
minimal dependencies, starts server.py, and optionally runs a no-server check for
installers.
"""
from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

DEFAULT_PORT = 8788


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def venv_python(root: Path) -> Path:
    if os.name == "nt":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def ensure_deps(root: Path) -> Path:
    py = venv_python(root)
    if not py.exists():
        subprocess.run([sys.executable, "-m", "venv", str(root / ".venv")], check=True)
    subprocess.run([str(py), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    req = root / "requirements.txt"
    if req.exists():
        subprocess.run([str(py), "-m", "pip", "install", "-r", str(req)], check=True)
    return py


def find_agent_dir(root: Path) -> Path | None:
    candidates = [
        os.environ.get("HERMES_WEBUI_AGENT_DIR"),
        str(Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "hermes-agent"),
        str(root.parent / "hermes-agent"),
        str(Path.home() / ".hermes" / "hermes-agent"),
        str(Path.home() / "hermes-agent"),
    ]
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        candidates.append(str(Path(os.environ["LOCALAPPDATA"]) / "hermes" / "hermes-agent"))
    for item in candidates:
        if not item:
            continue
        p = Path(item).expanduser()
        if (p / "run_agent.py").exists():
            return p.resolve()
    return None


def port_is_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def wait_health(host: str, port: int, timeout: float = 15) -> bool:
    url = f"http://{host}:{port}/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                body = resp.read().decode("utf-8", "replace")
                if resp.status == 200 and '"status"' in body:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Start Hermes Web UI")
    parser.add_argument("port", nargs="?", type=int, default=None)
    parser.add_argument("--check", action="store_true", help="prepare/import check only; do not start server")
    args = parser.parse_args()

    root = repo_root()
    load_env(root / ".env")
    port = args.port or int(os.environ.get("HERMES_WEBUI_PORT", DEFAULT_PORT))
    host = os.environ.get("HERMES_WEBUI_HOST", "127.0.0.1")
    os.environ["HERMES_WEBUI_PORT"] = str(port)
    os.environ["HERMES_WEBUI_HOST"] = host

    agent_dir = find_agent_dir(root)
    if agent_dir:
        os.environ.setdefault("HERMES_WEBUI_AGENT_DIR", str(agent_dir))
        sys.path.insert(0, str(agent_dir))

    py = ensure_deps(root)
    if args.check:
        subprocess.run([str(py), "-c", "import yaml; print('check: pyyaml ok')"], check=True)
        if agent_dir:
            print(f"check: Hermes agent found at {agent_dir}")
        else:
            print("check: Hermes agent not found yet; Web UI can start but agent features may be limited")
        return

    if port_is_open(host, port):
        print(f"Port already in use: {host}:{port}", file=sys.stderr)
        print("Stop the existing server or choose another port.", file=sys.stderr)
        raise SystemExit(2)

    log_dir = Path(os.environ.get("TMPDIR") or os.environ.get("TEMP") or "/tmp")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"hermes-webui-{port}.log"
    print(f"Starting Hermes Web UI on http://{host}:{port}")
    print(f"Log: {log_path}")
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen([str(py), str(root / "server.py")], cwd=str(root), stdout=log, stderr=subprocess.STDOUT)
    if wait_health(host, port):
        print(f"Hermes Web UI is healthy: http://localhost:{port}")
        print(f"PID: {proc.pid}")
    else:
        print("Health check did not pass yet. Recent log:")
        try:
            print(log_path.read_text(encoding="utf-8")[-4000:])
        except Exception:
            pass
        raise SystemExit(1)


if __name__ == "__main__":
    main()
