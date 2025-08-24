from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
from PyQt6.QtCore import QThread, pyqtSignal
import subprocess, sys, time, re

@dataclass
class DeviceJob:
    row: int
    ip: str
    interval: int = 30

_ANY_MS = re.compile(r'([<]?\d+(?:[.,]\d+)?)\s*(?:ms|мс)', re.IGNORECASE)

def ping_once(ip: str, timeout_ms: int = 1000) -> Tuple[bool, int]:
    is_windows = sys.platform.startswith("win")
    if is_windows:
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), ip]
        encoding = "mbcs"
        creationflags = 0x08000000  # CREATE_NO_WINDOW
    else:
        wait_s = max(1, int(timeout_ms/1000))
        cmd = ["ping", "-c", "1", "-W", str(wait_s), ip]
        encoding = "utf-8"
        creationflags = 0

    t0 = time.perf_counter()
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, encoding=encoding, errors="ignore",
                             timeout=timeout_ms/1000.0 + 1.0, creationflags=creationflags)
    except Exception:
        return False, 0
    elapsed_ms = int((time.perf_counter() - t0)*1000)
    txt = (out.stdout or "") + "\n" + (out.stderr or "")
    low = txt.lower()
    ok = (out.returncode == 0) or ("ttl=" in low) or ("bytes=" in low) or ("time=" in low) or ("время=" in low)
    ms = 0
    m = _ANY_MS.search(txt)
    if m:
        try:
            v = m.group(1).replace(",", ".").lstrip("<")
            ms = int(float(v))
        except Exception:
            ms = 0
    if ok and ms == 0:
        ms = elapsed_ms if elapsed_ms > 0 else 1
    return ok, (ms if ok else 0)

class PingWorker(QThread):
    ping_result = pyqtSignal(int, bool, int)  # row, online, ms
    started_monitoring = pyqtSignal()
    stopped_monitoring = pyqtSignal()

    def __init__(self, jobs: List[DeviceJob] | None = None, parent=None):
        super().__init__(parent)
        self._jobs: List[DeviceJob] = list(jobs) if jobs else []
        self._running = False

    def set_jobs(self, jobs: List[DeviceJob]):
        self._jobs = list(jobs)

    def stop(self):
        self._running = False

    def run(self):
        if not self._jobs:
            return
        self._running = True
        self.started_monitoring.emit()
        last_tick = {j.row: 0.0 for j in self._jobs}
        while self._running:
            now = time.time()
            for j in list(self._jobs):
                if not self._running:
                    break
                if now - last_tick.get(j.row, 0.0) >= max(1, j.interval):
                    online, ms = ping_once(j.ip, timeout_ms=1000)
                    self.ping_result.emit(j.row, online, ms)
                    last_tick[j.row] = now
            self.msleep(100)
        self.stopped_monitoring.emit()
