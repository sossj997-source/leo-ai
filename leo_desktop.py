# leo_desktop.py
# LEO DESKTOP CLIENT
# Tkinter UI + Render API backend
# Run: python leo_desktop.py
# Build: pyinstaller --onefile --windowed --name Leo leo_desktop.py

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import json
import os
import threading
import sys
import uuid

# ==================================================
# CONFIG
# ==================================================
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".leo_config.json")
DEFAULT_URL = "https://leo-ai-fb31.onrender.com"
TIMEOUT = 120


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"api_url": DEFAULT_URL, "session_id": str(uuid.uuid4())}


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Config save failed: {e}")


# ==================================================
# MAIN APP
# ==================================================
class LeoApp:
    def __init__(self, root):
        self.root = root
        self.config = load_config()
        self.realtime_mode = False
        self.is_sending = False

        self.root.title("LEO")
        self.root.geometry("900x650")
        self.root.minsize(600, 400)

        # Colors
        self.bg = "#0d1117"
        self.fg = "#e6edf3"
        self.user_color = "#58a6ff"
        self.leo_color = "#7ee787"
        self.input_bg = "#161b22"
        self.button_bg = "#238636"
        self.button_fg = "#ffffff"

        self.root.configure(bg=self.bg)

        self._build_ui()
        self._check_backend()

    # ------------------------------------------------
    # UI BUILD
    # ------------------------------------------------
    def _build_ui(self):
        # Top bar
        top = tk.Frame(self.root, bg=self.bg, height=50)
        top.pack(fill=tk.X, padx=10, pady=(10, 0))

        title = tk.Label(top, text="LEO", font=("Segoe UI", 16, "bold"),
                         bg=self.bg, fg=self.fg)
        title.pack(side=tk.LEFT)

        self.status_label = tk.Label(top, text="● connecting...", font=("Segoe UI", 9),
                                     bg=self.bg, fg="#8b949e")
        self.status_label.pack(side=tk.LEFT, padx=(12, 0))

        # Realtime toggle
        self.realtime_var = tk.BooleanVar(value=False)
        rt_check = tk.Checkbutton(top, text="Realtime", variable=self.realtime_var,
                                  command=self._toggle_realtime,
                                  bg=self.bg, fg=self.fg, selectcolor=self.input_bg,
                                  activebackground=self.bg, activeforeground=self.fg,
                                  font=("Segoe UI", 9))
        rt_check.pack(side=tk.RIGHT, padx=(0, 6))

        # Clear button
        clear_btn = tk.Button(top, text="Clear", command=self._clear_chat,
                              bg=self.input_bg, fg=self.fg, relief=tk.FLAT,
                              font=("Segoe UI", 9), padx=10, pady=2,
                              activebackground="#30363d", activeforeground=self.fg)
        clear_btn.pack(side=tk.RIGHT, padx=(0, 6))

        # Settings button
        set_btn = tk.Button(top, text="⚙", command=self._open_settings,
                            bg=self.input_bg, fg=self.fg, relief=tk.FLAT,
                            font=("Segoe UI", 11), padx=8, pady=0,
                            activebackground="#30363d", activeforeground=self.fg)
        set_btn.pack(side=tk.RIGHT, padx=(0, 6))

        # Chat area
        self.chat_area = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD,
            bg=self.input_bg, fg=self.fg,
            font=("Segoe UI", 10),
            relief=tk.FLAT, borderwidth=0,
            padx=14, pady=12,
            insertbackground=self.fg,
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.chat_area.configure(state=tk.DISABLED)

        # Configure tags for colored text
        self.chat_area.tag_config("user", foreground=self.user_color, font=("Segoe UI", 10, "bold"))
        self.chat_area.tag_config("leo", foreground=self.leo_color, font=("Segoe UI", 10, "bold"))
        self.chat_area.tag_config("text", foreground=self.fg, font=("Segoe UI", 10))
        self.chat_area.tag_config("meta", foreground="#8b949e", font=("Segoe UI", 9, "italic"))

        # Input area
        bottom = tk.Frame(self.root, bg=self.bg)
        bottom.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.input_box = tk.Text(bottom, height=3, wrap=tk.WORD,
                                 bg=self.input_bg, fg=self.fg,
                                 font=("Segoe UI", 10),
                                 relief=tk.FLAT, borderwidth=0,
                                 padx=10, pady=8,
                                 insertbackground=self.fg)
        self.input_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.input_box.bind("<Return>", self._on_enter)
        self.input_box.bind("<Shift-Return>", lambda e: None)

        self.send_btn = tk.Button(bottom, text="Send", command=self._send_message,
                                  bg=self.button_bg, fg=self.button_fg,
                                  font=("Segoe UI", 10, "bold"),
                                  relief=tk.FLAT, padx=20, pady=10,
                                  activebackground="#2ea043", activeforeground=self.button_fg)
        self.send_btn.pack(side=tk.RIGHT, padx=(10, 0))

        self._append("leo", "LEO", "Ready. Message bhejo.\n")

    # ------------------------------------------------
    # CHAT HELPERS
    # ------------------------------------------------
    def _append(self, tag, prefix, text):
        self.chat_area.configure(state=tk.NORMAL)
        if prefix:
            self.chat_area.insert(tk.END, f"{prefix}: ", tag)
        self.chat_area.insert(tk.END, f"{text}\n\n", "text")
        self.chat_area.see(tk.END)
        self.chat_area.configure(state=tk.DISABLED)

    def _append_meta(self, text):
        self.chat_area.configure(state=tk.NORMAL)
        self.chat_area.insert(tk.END, f"{text}\n\n", "meta")
        self.chat_area.see(tk.END)
        self.chat_area.configure(state=tk.DISABLED)

    def _clear_chat(self):
        self.chat_area.configure(state=tk.NORMAL)
        self.chat_area.delete("1.0", tk.END)
        self.chat_area.configure(state=tk.DISABLED)
        self.config["session_id"] = str(uuid.uuid4())
        save_config(self.config)
        self._append_meta("Session cleared. Fresh start.")

    def _on_enter(self, event):
        if event.state & 0x0001:  # Shift held
            return
        self._send_message()
        return "break"

    def _toggle_realtime(self):
        self.realtime_mode = self.realtime_var.get()
        mode = "ON (web search)" if self.realtime_mode else "OFF"
        self._append_meta(f"Realtime mode: {mode}")

    # ------------------------------------------------
    # BACKEND
    # ------------------------------------------------
    def _check_backend(self):
        def check():
            try:
                r = requests.get(f"{self.config['api_url']}/health", timeout=60)
                if r.status_code == 200:
                    self.root.after(0, lambda: self.status_label.config(
                        text="● online", fg="#7ee787"))
                else:
                    self.root.after(0, lambda: self.status_label.config(
                        text=f"● error {r.status_code}", fg="#f85149"))
            except Exception as e:
                self.root.after(0, lambda: self.status_label.config(
                    text="● offline", fg="#f85149"))

        threading.Thread(target=check, daemon=True).start()

    def _send_message(self):
        if self.is_sending:
            return
        msg = self.input_box.get("1.0", tk.END).strip()
        if not msg:
            return
        self.input_box.delete("1.0", tk.END)
        self._append("user", "You", msg)

        self.is_sending = True
        self.send_btn.config(state=tk.DISABLED, text="...")

        def worker():
            endpoint = "/chat/realtime" if self.realtime_mode else "/chat"
            payload = {"message": msg, "session_id": self.config.get("session_id")}
            try:
                r = requests.post(
                    f"{self.config['api_url']}{endpoint}",
                    json=payload,
                    timeout=TIMEOUT,
                )
                if r.status_code == 200:
                    data = r.json()
                    self.config["session_id"] = data.get("session_id", self.config.get("session_id"))
                    save_config(self.config)
                    reply = data.get("response", "(no response)")
                    self.root.after(0, lambda: self._append("leo", "Leo", reply))
                else:
                    self.root.after(0, lambda: self._append_meta(f"Error {r.status_code}: {r.text[:200]}"))
            except requests.exceptions.Timeout:
                self.root.after(0, lambda: self._append_meta("Timeout. Render cold start ho sakta hai. Dobara try karo."))
            except Exception as e:
                self.root.after(0, lambda: self._append_meta(f"Error: {e}"))
            finally:
                self.root.after(0, self._reset_send)

        threading.Thread(target=worker, daemon=True).start()

    def _reset_send(self):
        self.is_sending = False
        self.send_btn.config(state=tk.NORMAL, text="Send")

    # ------------------------------------------------
    # SETTINGS
    # ------------------------------------------------
    def _open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("500x200")
        win.configure(bg=self.bg)

        tk.Label(win, text="API URL:", bg=self.bg, fg=self.fg,
                 font=("Segoe UI", 10)).pack(anchor=tk.W, padx=15, pady=(15, 4))

        url_var = tk.StringVar(value=self.config.get("api_url", DEFAULT_URL))
        entry = tk.Entry(win, textvariable=url_var, bg=self.input_bg, fg=self.fg,
                         insertbackground=self.fg, relief=tk.FLAT,
                         font=("Segoe UI", 10))
        entry.pack(fill=tk.X, padx=15, ipady=6)

        def save():
            self.config["api_url"] = url_var.get().strip().rstrip("/")
            save_config(self.config)
            self._append_meta(f"API URL updated: {self.config['api_url']}")
            self._check_backend()
            win.destroy()

        tk.Button(win, text="Save", command=save,
                  bg=self.button_bg, fg=self.button_fg,
                  font=("Segoe UI", 10, "bold"),
                  relief=tk.FLAT, padx=20, pady=8).pack(pady=20)


# ==================================================
# ENTRY
# ==================================================
def main():
    root = tk.Tk()
    app = LeoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()