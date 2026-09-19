# app/agent/activity_monitor.py
import sys
import threading
import time
import logging
from typing import Optional

import psutil

from .proactive_engine import ProactiveEngine, ProactiveEvent

logger = logging.getLogger("J.A.R.V.I.S")

# Windows-specific imports — only available on Windows
_PYGETWINDOW_AVAILABLE = False
_CTYPES_AVAILABLE = False

if sys.platform == "win32":
    try:
        import ctypes
        _CTYPES_AVAILABLE = True
    except (ImportError, Exception) as e:
        ctypes = None
        logger.warning(f"ctypes not available: {e}")

    try:
        import pygetwindow
        _PYGETWINDOW_AVAILABLE = True
    except (ImportError, Exception) as e:
        pygetwindow = None
        logger.warning(f"pygetwindow not available: {e}")
else:
    ctypes = None
    pygetwindow = None
    logger.info("ActivityMonitor disabled — not supported on this platform")


class ActivityMonitor:
    """
    Monitors the currently active Windows application/window.

    Emits an app_changed event only when the active app/window changes.
    NOTE: This feature only works on Windows. On Linux servers, it is disabled.
    """

    def __init__(
        self,
        engine: ProactiveEngine,
        poll_interval: float = 1.0,
    ):
        self.engine = engine
        self.poll_interval = poll_interval

        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._last_key = None

    def _get_active_window_info(self):
        """Get info about the currently active window (Windows only)."""
        if not _PYGETWINDOW_AVAILABLE or not _CTYPES_AVAILABLE:
            return None

        try:
            window = pygetwindow.getActiveWindow()

            if window is None:
                return None

            title = window.title or ""

            if not title.strip():
                return None

            hwnd = int(window._hWnd)

            # Get process ID from window handle
            user32 = ctypes.windll.user32
            pid = ctypes.c_ulong()

            user32.GetWindowThreadProcessId(
                hwnd,
                ctypes.byref(pid)
            )

            process_name = "unknown"

            try:
                process = psutil.Process(pid.value)
                process_name = process.name()

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            return {
                "title": title,
                "process": process_name,
                "pid": pid.value,
            }

        except Exception as e:
            logger.debug(f"Could not get active window: {e}")
            return None

    def _check_activity(self):
        """Check for active window change and emit event."""
        if not _PYGETWINDOW_AVAILABLE:
            return

        info = self._get_active_window_info()

        if info is None:
            return

        current_key = f"{info['process']}::{info['title']}"

        if current_key != self._last_key:
            self._last_key = current_key

            event = ProactiveEvent(
                type="app_changed",
                data={
                    "app": info["process"],
                    "title": info["title"],
                    "pid": info["pid"],
                },
            )

            self.engine.emit(event)

    def _loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                self._check_activity()
            except Exception as e:
                logger.error(f"ActivityMonitor loop error: {e}")

            time.sleep(self.poll_interval)

    def start(self):
        """Start monitoring (only works on Windows)."""
        if not _PYGETWINDOW_AVAILABLE:
            logger.info("ActivityMonitor skipped — pygetwindow not available (non-Windows platform)")
            return

        if self.running:
            return

        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("[ActivityMonitor] Started")

    def stop(self):
        """Stop monitoring."""
        self.running = False

        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

        logger.info("[ActivityMonitor] Stopped")

    def get_status(self):
        """Return current status."""
        return {
            "running": self.running,
            "available": _PYGETWINDOW_AVAILABLE,
            "platform": sys.platform,
        }