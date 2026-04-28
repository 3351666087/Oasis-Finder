from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import sys
import webbrowser

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget


HOST = "127.0.0.1"
PORT = 8000
DISPLAY_URL = f"http://{HOST}:{PORT}/?lang=zh"


def app_root() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]


ROOT = app_root()


def resource_path(relative: str) -> Path:
    candidates = [
        ROOT / relative,
        Path(getattr(sys, "_MEIPASS", ROOT)) / relative,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def port_open(host: str = HOST, port: int = PORT) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.6):
            return True
    except OSError:
        return False


def ensure_mysql_started() -> None:
    if port_open(HOST, 3307):
        return
    script = resource_path("scripts/setup_local_mysql.ps1")
    if not script.exists():
        return
    subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-ProjectRoot",
            str(ROOT),
        ],
        cwd=str(ROOT),
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


class WebServerThread(QThread):
    ready = Signal()
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.server = None

    def run(self) -> None:
        try:
            ensure_mysql_started()
            import uvicorn

            from .web_api import app

            config = uvicorn.Config(
                app,
                host=HOST,
                port=PORT,
                log_level="warning",
                access_log=False,
                log_config=None,
            )
            self.server = uvicorn.Server(config)
            self.ready.emit()
            self.server.run()
        except Exception as exc:  # pragma: no cover - surfaced in launcher UI
            self.failed.emit(str(exc))

    def stop(self) -> None:
        if self.server is not None:
            self.server.should_exit = True


class Launcher(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.server_thread: WebServerThread | None = None
        self.setWindowTitle("Oasis Finder Launcher")
        self.setFixedSize(520, 300)

        self.title = QLabel("Oasis Finder")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))

        self.subtitle = QLabel("Browser showcase launcher")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle.setFont(QFont("Segoe UI", 10))

        self.status = QLabel("Red: not running")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))

        self.switch = QPushButton("OFF")
        self.switch.setCheckable(True)
        self.switch.setMinimumHeight(78)
        self.switch.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.switch.clicked.connect(self.toggle_server)

        layout = QVBoxLayout()
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.switch)
        layout.addWidget(self.status)
        self.setLayout(layout)
        self.paint_off()

    def paint_off(self) -> None:
        self.switch.setText("OFF")
        self.switch.setChecked(False)
        self.status.setText("Red: not running")
        self.setStyleSheet(
            """
            QWidget { background: #101820; color: #f8fafc; }
            QPushButton {
                border: 0;
                border-radius: 16px;
                background: #dc2626;
                color: white;
            }
            QPushButton:hover { background: #ef4444; }
            QLabel { color: #f8fafc; }
            """
        )

    def paint_on(self) -> None:
        self.switch.setText("ON")
        self.switch.setChecked(True)
        self.status.setText("Green: running, browser page opened")
        self.setStyleSheet(
            """
            QWidget { background: #071014; color: #f8fafc; }
            QPushButton {
                border: 0;
                border-radius: 16px;
                background: #22c55e;
                color: #05231a;
            }
            QPushButton:hover { background: #86efac; }
            QLabel { color: #f8fafc; }
            """
        )

    def toggle_server(self) -> None:
        if self.switch.isChecked():
            self.start_server()
        else:
            self.stop_server()

    def start_server(self) -> None:
        if port_open():
            self.paint_on()
            webbrowser.open(DISPLAY_URL)
            return
        self.status.setText("Starting local showcase service...")
        self.switch.setEnabled(False)
        self.server_thread = WebServerThread()
        self.server_thread.ready.connect(self.on_ready)
        self.server_thread.failed.connect(self.on_failed)
        self.server_thread.start()

    def on_ready(self) -> None:
        self.paint_on()
        self.switch.setEnabled(True)
        webbrowser.open(DISPLAY_URL)

    def on_failed(self, message: str) -> None:
        self.switch.setEnabled(True)
        self.paint_off()
        self.status.setText(f"Startup failed: {message[:80]}")

    def stop_server(self) -> None:
        if self.server_thread and self.server_thread.isRunning():
            self.server_thread.stop()
            self.server_thread.wait(1800)
        self.paint_off()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        self.stop_server()
        super().closeEvent(event)


def run_app() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = Launcher()
    window.show()
    app.exec()
