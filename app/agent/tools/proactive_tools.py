from datetime import datetime
from typing import Any, Dict, Optional, Optional

from ..proactive_manager import ProactiveManager


class ProactiveTools:

    def __init__(self, manager: ProactiveManager):
        self.manager = manager

    def create_reminder(
        self,
        name: str,
        run_at: str,
        message: str,
        repeat_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:

        try:
            scheduled_time = datetime.fromisoformat(run_at)

        except ValueError:
            return {
                "success": False,
                "error": "Invalid run_at datetime format.",
            }

        def reminder_action():
            print(
                f"🔔 LEO REMINDER: {message}"
            )

        try:
            self.manager.add_task(
    name=name,
    run_at=scheduled_time,
    action=reminder_action,
    repeat_seconds=repeat_seconds,
    message=message,
)

            return {
                "success": True,
                "name": name,
                "run_at": scheduled_time.isoformat(),
                "message": message,
                "repeat_seconds": repeat_seconds,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def remove_reminder(
        self,
        name: str,
    ) -> Dict[str, Any]:

        removed = self.manager.remove_task(name)

        return {
            "success": removed,
            "name": name,
            "message": (
                "Reminder removed."
                if removed
                else "Reminder not found."
            ),
        }

    def list_reminders(self):
        return {
            "success": True,
            "tasks": self.manager.get_tasks(),
        }
    def create_activity_rule(
        self,
        name: str,
        app_name: str,
        message: str,
    ) -> Dict[str, Any]:
        try:
            def activity_action(event):
                print(
                    f"🔔 LEO PROACTIVE: {message}"
                )

            self.manager.add_activity_rule(
                name=name,
                app_name=app_name,
                action=activity_action,
            )

            return {
                "success": True,
                "name": name,
                "app_name": app_name,
                "message": message,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }