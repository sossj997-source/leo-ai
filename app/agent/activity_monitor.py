import ctypes
import threading
import time
from typing import Optional

import psutil
import pygetwindow

from .proactive_engine import ProactiveEngine, ProactiveEvent


class ActivityMonitor:
    """
    Monitors the currently active Windows application/window.

    Emits an app_changed event only when the active app/window changes.
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
                ctypes.byref(pid),
            )

            process_name = "unknown.exe"

            try:
                process = psutil.Process(pid.value)
                process_name = process.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            return {
                "app": process_name,
                "title": title,
                "hwnd": hwnd,
            }

        except Exception as e:
            print(f"[ActivityMonitor] Window detection failed: {e}")
            return None

    def _check_activity(self):
        info = self._get_active_window_info()

        if info is None:
            return

        current_key = (
            info["app"],
            info["title"],
            info["hwnd"],
        )

        if current_key == self._last_key:
            return

        previous = self._last_key
        self._last_key = current_key

        event = ProactiveEvent(
            event_type="app_changed",
            data={
                "app": info["app"],
                "title": info["title"],
                "hwnd": info["hwnd"],
                "previous": previous,
            },
        )

        self.engine.emit(event)

    def _loop(self):
        while self.running:
            try:
                self._check_activity()
            except Exception as e:
                print(f"[ActivityMonitor] Check failed: {e}")

            time.sleep(self.poll_interval)

    def start(self):
        if self.running:
            return

        self.running = True

        self._thread = threading.Thread(
            target=self._loop,
            name="LEO-ActivityMonitor",
            daemon=True,
        )

        self._thread.start()

        print("[ActivityMonitor] Started")

    def stop(self):
        self.running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

        print("[ActivityMonitor] Stopped")

    def get_status(self):
        return {
            "running": self.running,
            "last_activity": self._last_key,
            "poll_interval": self.poll_interval,
        }


if __name__ == "__main__":

    engine = ProactiveEngine()

    def show_event(event):
        print("EVENT:", event.data)

    engine.add_rule(
        __import__(
            "app.agent.proactive_engine",
            fromlist=["ProactiveRule"],
        ).ProactiveRule(
            name="activity_test",
            condition=lambda event: event.event_type == "app_changed",
            action=show_event,
        )
    )

    monitor = ActivityMonitor(engine)

    monitor.start()

    try:
        time.sleep(15)
    finally:
        monitor.stop()