from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

class AutomationController:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.main_file = self.base_dir / "main.py"
        self.stop_file = self.base_dir / "STOP_REQUESTED"
        self.process: Optional[subprocess.Popen] = None

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self) -> tuple[bool, str]:
        if self.is_running():
            return False, "Automation is already running."
        if not self.main_file.exists():
            return False, f"Cannot find {self.main_file.name}."
        try:
            self.stop_file.unlink(missing_ok=True)
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            self.process = subprocess.Popen(
                [sys.executable, str(self.main_file)],
                cwd=str(self.base_dir),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            return True, "Automation process started."
        except Exception as exc:
            return False, f"Could not start automation: {exc}"

    def stop(self) -> tuple[bool, str]:
        if not self.is_running():
            return False, "Automation is not running."
        try:
            self.stop_file.write_text("stop", encoding="utf-8")
            return True, "Stop requested. The current send will finish before the next queued video starts."
        except Exception as exc:
            return False, f"Could not request stop: {exc}"

    def read_status(self) -> dict:
        path = self.base_dir / "status.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"status": "Stopped", "current_file": "", "stage": "Not started"}
