from datetime import datetime
from typing import Any, Callable, Dict, Optional

from .proactive_scheduler import ProactiveScheduler
from .proactive_store import ProactiveStore
from .proactive_triggers import ProactiveTriggerManager
from .proactive_engine import (
    ProactiveEngine,
    ProactiveEvent,
    ProactiveRule,
)

class ProactiveManager:
    def __init__(self, store_path: str = "data/proactive_tasks.json"):
        self.scheduler = ProactiveScheduler()
        self.store = ProactiveStore(store_path)
        self.engine = ProactiveEngine()
        self.triggers = ProactiveTriggerManager()

        self._load_tasks()

    def _load_tasks(self):
        saved_tasks = self.store.load_tasks()

        for task in saved_tasks:
            # Skip completed one-time tasks.
            # Recurring tasks must always be restored.
            if task.get("executed") and not task.get("repeat_seconds"):
                continue

            try:
                run_at = datetime.fromisoformat(task["run_at"])
                repeat_seconds = task.get("repeat_seconds")
                message = task.get("message", "Reminder")

                def restored_action(
                    task_message=message,
                ):
                    print(f"🔔 LEO REMINDER: {task_message}")

                self.scheduler.add_task(
                    name=task["name"],
                    run_at=run_at,
                    action=restored_action,
                    repeat_seconds=repeat_seconds,
                    message=message,
                )

            except (KeyError, ValueError, TypeError):
                continue

    def emit_event(
        self,
        event_type: str,
        data=None,
    ):
        event = ProactiveEvent(
            event_type=event_type,
            data=data or {},
        )

        self.engine.emit(event)

    def add_activity_rule(
        self,
        name: str,
        app_name: str,
        action: Callable[[ProactiveEvent], Any],
        priority: int = 0,
    ):
        app_name = app_name.lower()

        def condition(event: ProactiveEvent) -> bool:
            if event.event_type != "app_changed":
                return False

            current_app = str(
                event.data.get("app", "")
            ).lower()

            return current_app == app_name

        self.engine.add_rule(
            ProactiveRule(
                name=name,
                condition=condition,
                action=action,
                priority=priority,
            )
        )
    def add_time_trigger(
        self,
        name: str,
        run_at: datetime,
        event_type: str,
        data=None,
    ):
        def fire_event():
            self.emit_event(
                event_type,
                data or {},
            )

        self.triggers.add_time_trigger(
            name=name,
            run_at=run_at,
            callback=fire_event,
        )

    def add_task(
        self,
        name: str,
        run_at: datetime,
        action: Callable,
        repeat_seconds: Optional[int] = None,
        message: Optional[str] = None,
    ):
        self.scheduler.add_task(
            name=name,
            run_at=run_at,
            action=action,
            repeat_seconds=repeat_seconds,
            message=message,
        )

        self._save_tasks()

    def remove_task(self, name: str) -> bool:
        removed = self.scheduler.remove_task(name)

        if removed:
            self._save_tasks()

        return removed

    def start(self):
        self.scheduler.start()
        self.triggers.start()

    def stop(self):
        self.scheduler.stop()
        self.triggers.stop()
        self._save_tasks()

    def get_tasks(self):
        return self.scheduler.get_tasks()

    def _save_tasks(self):
        self.store.save_tasks(
            self.scheduler.get_tasks()
        )

    def get_status(self) -> Dict[str, Any]:
        return {
            "scheduler": self.scheduler.running,
            "triggers": self.triggers.running,
            "tasks": len(self.scheduler.tasks),
            "time_triggers": len(self.triggers.time_triggers),
            "store_exists": self.store.exists(),
        }