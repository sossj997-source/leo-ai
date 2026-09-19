import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

from .proactive_manager import ProactiveManager


class ProactiveCommandParser:
    def __init__(self, manager: ProactiveManager):
        self.manager = manager

    def parse_time(self, text: str) -> Optional[datetime]:
        text = text.lower().strip()
        now = datetime.now()

        # "10 seconds/minutes/hours baad"
        match = re.search(
            r"(\d+)\s*(second|seconds|sec|secs|minute|minutes|min|mins|hour|hours|hr|hrs)\s*(baad|later)",
            text,
        )

        if match:
            amount = int(match.group(1))
            unit = match.group(2)

            if unit.startswith("second") or unit in {"sec", "secs"}:
                return now + timedelta(seconds=amount)

            if unit.startswith("minute") or unit in {"min", "mins"}:
                return now + timedelta(minutes=amount)

            if unit.startswith("hour") or unit in {"hr", "hrs"}:
                return now + timedelta(hours=amount)

        # "kal 7 baje"
        match = re.search(
            r"kal\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
            text,
        )

        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            meridiem = match.group(3)

            if meridiem == "pm" and hour < 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0

            tomorrow = now + timedelta(days=1)

            return tomorrow.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
            )

        # "roz/daily/har din 8 baje"
        match = re.search(
            r"(?:roz|daily|har\s+din)\s+"
            r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
            text,
        )

        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            meridiem = match.group(3)

            if meridiem == "pm" and hour < 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0

            run_at = now.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
            )

            # Agar aaj ka time nikal chuka hai,
            # first reminder kal hoga.
            if run_at <= now:
                run_at += timedelta(days=1)

            return run_at

        return None

    def is_daily(self, text: str) -> bool:
        text = text.lower().strip()

        return bool(
            re.search(
                r"\b(?:roz|daily|har\s+din)\b",
                text,
            )
        )

    def extract_message(self, text: str) -> str:
        patterns = [
            r"\d+\s*(?:second|seconds|sec|secs|minute|minutes|min|mins|hour|hours|hr|hrs)\s*(?:baad|later)\s*(.*)",

            r"kal\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*(.*)",

            r"(?:roz|daily|har\s+din)\s+"
            r"\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*(.*)",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                text.lower().strip(),
            )

            if match:
                message = match.group(1).strip()

                if message:
                    return message

        return text.strip()

    def create_reminder(
        self,
        text: str,
    ) -> Tuple[bool, str]:

        run_at = self.parse_time(text)

        if run_at is None:
            return False, "I couldn't understand the reminder time."

        message = self.extract_message(text)

        if not message:
            message = "Reminder"

        daily = self.is_daily(text)

        task_name = f"reminder_{int(run_at.timestamp())}"

        def reminder_action():
            print(
                f"🔔 LEO REMINDER: {message}"
            )

        self.manager.scheduler.add_task(
            name=task_name,
            run_at=run_at,
            action=reminder_action,
            repeat_seconds=86400 if daily else None,
        )

        self.manager._save_tasks()

        repeat_text = " daily" if daily else ""

        return True, (
            f"Reminder set for "
            f"{run_at.strftime('%Y-%m-%d %H:%M:%S')}"
            f"{repeat_text}: "
            f"{message}"
        )