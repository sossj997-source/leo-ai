# leo_app.py
# LEO DESKTOP APP - pywebview wrapper for frontend
# Run: python leo_app.py
# Build: pyinstaller --onefile --windowed --add-data "frontend;frontend" --name LeoApp leo_app.py

import webview
import os
import sys
import threading
import http.server
import socketserver
import time


def resource_path(relative):
    """PyInstaller bundle ke andar aur bahar dono ke liye path."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.abspath("."), relative)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def start_local_server(directory, port=5501):
    os.chdir(directory)
    handler = QuietHandler
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def main():
    frontend_dir = resource_path("frontend")
    if not os.path.exists(frontend_dir):
        print(f"ERROR: frontend folder not found at {frontend_dir}")
        sys.exit(1)

    httpd = start_local_server(frontend_dir, port=5501)
    time.sleep(0.5)

    window = webview.create_window(
        "LEO",
        "http://127.0.0.1:5501/index.html",
        width=1100,
        height=750,
        min_size=(700, 500),
        background_color="#0a0a0f",
    )

    webview.start()


if __name__ == "__main__":
    main()