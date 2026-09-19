from datetime import datetime
from typing import Callable, Optional
import threading
import time


class TimeTrigger:
    def __init__(
        self,
        name: str,
        run_at: datetime,
        callback: Callable,
    ):
        self.name = name
        self.run_at = run_at
        self.callback = callback
        self.fired = False


class ProactiveTriggerManager:
    def __init__(self):
        self.time_triggers = []
        self.running = False
        self._thread: Optional[threading.Thread] = None

    def add_time_trigger(
        self,
        name: str,
        run_at: datetime,
        callback: Callable,
    ):
        self.time_triggers.append(
            TimeTrigger(
                name=name,
                run_at=run_at,
                callback=callback,
            )
        )

    def remove_time_trigger(self, name: str) -> bool:
        before = len(self.time_triggers)

        self.time_triggers = [
            trigger
            for trigger in self.time_triggers
            if trigger.name != name
        ]

        return len(self.time_triggers) < before

    def start(self):
        if self.running:
            return

        self.running = True

        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
        )

        self._thread.start()

        print("[ProactiveTriggers] Started")

    def stop(self):
        self.running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

        print("[ProactiveTriggers] Stopped")

    def _loop(self):
        while self.running:
            now = datetime.now()

            for trigger in self.time_triggers:
                if trigger.fired:
                    continue

                if now >= trigger.run_at:
                    try:
                        print(
                            f"[ProactiveTriggers] Fired: {trigger.name}"
                        )

                        trigger.callback()
                        trigger.fired = True

                    except Exception as e:
                        print(
                            f"[ProactiveTriggers] "
                            f"Trigger '{trigger.name}' failed: {e}"
                        )

            time.sleep(1)

    def get_status(self):
        return {
            "running": self.running,
            "triggers": len(self.time_triggers),
        }