"""Local Chrome-extension bridge for Leo.

This is the preferred browser transport because it works with a normal,
already-running Chrome profile without CDP or a second browser process.
The Chrome extension polls this localhost bridge and performs tab/DOM actions.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlparse

HOST = "127.0.0.1"
PORT = 8765

_lock = threading.Lock()
_commands: Dict[str, Dict[str, Any]] = {}


def _new_command(action: str, params: Dict[str, Any]) -> str:
    cid = uuid.uuid4().hex
    with _lock:
        _commands[cid] = {
            "id": cid,
            "action": action,
            "params": params or {},
            "status": "pending",
            "result": None,
            "error": None,
            "created": time.time(),
        }
    return cid


def _cleanup():
    cutoff = time.time() - 120
    with _lock:
        for cid in list(_commands):
            if _commands[cid]["created"] < cutoff:
                _commands.pop(cid, None)


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _send(self, code: int, payload: Dict[str, Any]):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        _cleanup()
        path = urlparse(self.path).path
        if path == "/browser/health":
            self._send(200, {"ok": True, "transport": "chrome-extension"})
            return
        if path == "/browser/poll":
            # Long-poll so an MV3 service worker does not depend on a fragile
            # setInterval timer. The request itself keeps the worker active.
            deadline = time.time() + 15
            while time.time() < deadline:
                with _lock:
                    for cmd in _commands.values():
                        if cmd["status"] == "pending":
                            cmd["status"] = "claimed"
                            self._send(200, {"command": {"id": cmd["id"], "action": cmd["action"], "params": cmd["params"]}})
                            return
                time.sleep(0.15)
            self._send(200, {"command": None})
            return
        if path.startswith("/browser/command/"):
            cid = path.rsplit("/", 1)[-1]
            with _lock:
                cmd = _commands.get(cid)
            if not cmd:
                self._send(404, {"error": "Unknown command"})
            else:
                self._send(200, {"status": cmd["status"], "result": cmd["result"], "error": cmd["error"]})
            return
        self._send(404, {"error": "Not found"})

    def do_POST(self):
        _cleanup()
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send(400, {"error": "Invalid JSON"})
            return

        if path == "/browser/command":
            action = str(data.get("action", "")).strip()
            if not action:
                self._send(400, {"error": "Missing action"})
                return
            cid = _new_command(action, data.get("params") or {})
            self._send(200, {"id": cid})
            return

        if path == "/browser/result":
            cid = str(data.get("id", ""))
            with _lock:
                cmd = _commands.get(cid)
                if not cmd:
                    self._send(404, {"error": "Unknown command"})
                    return
                cmd["status"] = "done" if data.get("success", False) else "failed"
                cmd["result"] = data.get("result")
                cmd["error"] = data.get("error")
            self._send(200, {"ok": True})
            return

        self._send(404, {"error": "Not found"})


def _start_server():
    try:
        server = ThreadingHTTPServer((HOST, PORT), _Handler)
        server.daemon_threads = True
        server.serve_forever()
    except Exception:
        pass


_thread = threading.Thread(target=_start_server, daemon=True, name="leo-browser-bridge")
_thread.start()


def execute(action: str, params: Optional[Dict[str, Any]] = None, timeout: float = 25.0) -> str:
    """Queue a command for the extension and wait for its result."""
    import urllib.request

    payload = json.dumps({"action": action, "params": params or {}}).encode("utf-8")
    req = urllib.request.Request(
        f"http://{HOST}:{PORT}/browser/command",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            cid = json.loads(response.read().decode("utf-8"))["id"]
    except Exception as exc:
        raise RuntimeError(
            "Leo's Chrome extension is not connected. Install/enable the bundled "
            "Leo Browser extension in Chrome once; no CDP code is required."
        ) from exc

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://{HOST}:{PORT}/browser/command/{cid}", timeout=2
            ) as response:
                state = json.loads(response.read().decode("utf-8"))
            if state["status"] == "done":
                return str(state.get("result") or "Done")
            if state["status"] == "failed":
                raise RuntimeError(str(state.get("error") or "Browser extension action failed."))
        except RuntimeError:
            raise
        except Exception:
            pass
        time.sleep(0.15)

    raise RuntimeError(
        "Leo timed out waiting for the Chrome extension. Make sure the bundled "
        "Leo Browser extension is enabled and Chrome is open."
    )
