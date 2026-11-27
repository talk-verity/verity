#!/usr/bin/env python3
"""Launch all local services. Ctrl+C stops app processes; database data is retained."""
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PYTHON = BACKEND / ".venv/bin/python"
children = []

def stop(*_):
    for child in reversed(children):
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
    for child in children:
        try:
            child.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
    sys.exit(0)

def main():
    occupied = []
    for port in (3000, 8000):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                occupied.append(str(port))
    if occupied:
        sys.exit(
            f"Cannot start another instance: port(s) {', '.join(occupied)} are already in use.\n"
            "If Delphi is already running, open http://127.0.0.1:3000.\n"
            "To restart it, press Ctrl+C in its original terminal first.\n"
            "Inspect listeners with: lsof -nP -iTCP:3000 -iTCP:8000 -sTCP:LISTEN\n"
            "No services were started or stopped."
        )
    if not PYTHON.exists() or not (ROOT / "frontend/node_modules").exists():
        sys.exit("Install dependencies first; see README.md.")
    if subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        sys.exit("Start Docker Desktop, wait for it to be ready, then run this command again.")
    subprocess.run(["docker", "compose", "up", "-d"], cwd=ROOT, check=True)
    for _ in range(60):
        ready = subprocess.run(["docker", "compose", "exec", "-T", "postgres", "pg_isready", "-U", "delphi"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ready.returncode == 0:
            break
        time.sleep(1)
    else:
        sys.exit("PostgreSQL did not become ready.")
    subprocess.run([str(PYTHON), "-m", "alembic", "upgrade", "head"], cwd=BACKEND, check=True)
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    for command, cwd in [
        ([str(PYTHON), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"], BACKEND),
        ([str(PYTHON), "-m", "app.feedback.worker"], BACKEND),
        (["node", "node_modules/next/dist/bin/next", "dev", "--webpack", "--port", "3000"], ROOT / "frontend"),
    ]:
        children.append(subprocess.Popen(command, cwd=cwd, start_new_session=True))
    print("Delphi: http://localhost:3000 — Ctrl+C stops the app processes.", flush=True)
    while all(child.poll() is None for child in children):
        time.sleep(1)
    print("A service exited. Stopping the remaining app processes.", flush=True)
    stop()

if __name__ == "__main__":
    main()
