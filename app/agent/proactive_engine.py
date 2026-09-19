from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import threading
import time


@dataclass
class ProactiveEvent:
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ProactiveRule:
    name: str
    condition: Callable[[ProactiveEvent], bool]
    action: Callable[[ProactiveEvent], Any]
    enabled: bool = True
    priority: int = 0


class ProactiveEngine:
    # Event -> Condition -> Action engine.
    # Rules are evaluated by priority (highest first).

    def __init__(self):
        self.rules: List[ProactiveRule] = []
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._events: List[ProactiveEvent] = []
        self._lock = threading.RLock()

    def add_rule(self, rule: ProactiveRule):
        with self._lock:
            self.rules = [
                existing for existing in self.rules
                if existing.name != rule.name
            ]
            self.rules.append(rule)
            self.rules.sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, name: str) -> bool:
        with self._lock:
            before = len(self.rules)
            self.rules = [r for r in self.rules if r.name != name]
            return len(self.rules) < before

    def enable_rule(self, name: str) -> bool:
        with self._lock:
            for rule in self.rules:
                if rule.name == name:
                    rule.enabled = True
                    return True
        return False

    def disable_rule(self, name: str) -> bool:
        with self._lock:
            for rule in self.rules:
                if rule.name == name:
                    rule.enabled = False
                    return True
        return False

    def emit(self, event: ProactiveEvent):
        with self._lock:
            self._events.append(event)
        self._process_event(event)

    def _process_event(self, event: ProactiveEvent):
        with self._lock:
            rules = list(self.rules)

        for rule in rules:
            if not rule.enabled:
                continue
            try:
                if rule.condition(event):
                    rule.action(event)
            except Exception as e:
                print(f"[ProactiveEngine] Rule '{rule.name}' failed: {e}")

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(
            target=self._loop,
            name="LEO-ProactiveEngine",
            daemon=True,
        )
        self._thread.start()
        print("[ProactiveEngine] Started")

    def stop(self):
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        print("[ProactiveEngine] Stopped")

    def _loop(self):
        while self.running:
            time.sleep(1)

    def get_events(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "event_type": e.event_type,
                    "data": e.data,
                    "created_at": e.created_at.isoformat(),
                }
                for e in self._events
            ]

    def get_rules(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "name": r.name,
                    "enabled": r.enabled,
                    "priority": r.priority,
                }
                for r in self.rules
            ]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self.running,
                "rules": len(self.rules),
                "enabled_rules": sum(
                    1 for r in self.rules if r.enabled
                ),
                "events": len(self._events),
            }
