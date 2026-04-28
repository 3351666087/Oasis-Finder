from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import webbrowser


ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web"
PYTHON = sys.executable


def _start_hidden(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.Popen:
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env or os.environ.copy(),
        startupinfo=startupinfo,
        creationflags=creationflags,
    )


def run_app() -> None:
    """Launch the browser-based Oasis Finder backend and frontend together."""
    if not WEB_DIR.exists():
        raise SystemExit("Missing web/ frontend folder. Run from the repository root after installing frontend files.")
    if not (WEB_DIR / "node_modules").exists():
        print("Installing frontend dependencies in web/ ...")
        subprocess.check_call(["npm", "install"], cwd=str(WEB_DIR))

    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = str(ROOT / "src")

    backend = _start_hidden(
        [PYTHON, "-m", "uvicorn", "mesh_supply_chain.web_api:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
        ROOT,
        backend_env,
    )
    frontend = _start_hidden(["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"], WEB_DIR)

    print("Oasis Finder web stack is starting...")
    print("Consumer frontend: http://127.0.0.1:5173/")
    print("Merchant backend console: http://127.0.0.1:5173/admin")
    print("API docs: http://127.0.0.1:8000/docs")
    print("Press Ctrl+C to stop both processes.")

    time.sleep(2.2)
    webbrowser.open("http://127.0.0.1:5173/")

    try:
        while backend.poll() is None and frontend.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for process in [frontend, backend]:
            if process.poll() is None:
                if os.name == "nt":
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    process.terminate()
        time.sleep(0.8)
        for process in [frontend, backend]:
            if process.poll() is None:
                process.kill()
