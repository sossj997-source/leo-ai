from datetime import datetime, timedelta
from typing import Callable, List, Optional
import threading
import time


class ScheduledTask:
    def __init__(
        self,
        name: str,
        run_at: datetime,
        action: Callable,
        repeat_seconds: Optional[int] = None,
        message: Optional[str] = None,
    ):
        self.name = name
        self.run_at = run_at
        self.action = action
        self.executed = False
        self.repeat_seconds = repeat_seconds
        self.message = message


class ProactiveScheduler:
    def __init__(self):
        self.tasks: List[ScheduledTask] = []
        self.running = False
        self._thread = None

    def add_task(
        self,
        name: str,
        run_at: datetime,
        action: Callable,
        repeat_seconds: Optional[int] = None,
        message: Optional[str] = None,
    ):
        task = ScheduledTask(
            name=name,
            run_at=run_at,
            action=action,
            repeat_seconds=repeat_seconds,
            message=message,
        )

        self.tasks.append(task)

    def remove_task(self, name: str) -> bool:
        before = len(self.tasks)

        self.tasks = [
            task
            for task in self.tasks
            if task.name != name
        ]

        return len(self.tasks) < before

    def start(self):
        if self.running:
            return

        self.running = True

        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
        )

        self._thread.start()

        print("[ProactiveScheduler] Started")

    def stop(self):
        self.running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

        print("[ProactiveScheduler] Stopped")

    def _loop(self):
        while self.running:
            now = datetime.now()

            for task in self.tasks:
                if task.executed and task.repeat_seconds is None:
                    continue

                if now >= task.run_at:
                    try:
                        print(
                            f"[ProactiveScheduler] Running: {task.name}"
                        )

                        task.action()

                        if task.repeat_seconds:
                            task.run_at = (
                                task.run_at
                                + timedelta(
                                    seconds=task.repeat_seconds
                                )
                            )

                            task.executed = False

                        else:
                            task.executed = True

                    except Exception as e:
                        print(
                            f"[ProactiveScheduler] "
                            f"Task '{task.name}' failed: {e}"
                        )

            time.sleep(1)

    def get_tasks(self):
        return [
            {
                "name": task.name,
                "run_at": task.run_at.isoformat(),
                "executed": task.executed,
                "repeat_seconds": task.repeat_seconds,
                "message": task.message,
            }
            for task in self.tasks
        ]