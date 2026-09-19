# app/agent/tools/browser_automation.py
"""
Leo browser automation using normal Chrome + PyAutoGUI + OCR.
No CDP, no port 9222, no Chrome extension, no separate profile.
"""

from __future__ import annotations
import os
import re
import subprocess
import time
import logging
from urllib.parse import quote_plus

logger = logging.getLogger("J.A.R.V.I.S")

# pyautogui and pytesseract require a display — not available on Linux servers
try:
    import pyautogui
    _PYAUTOGUI_AVAILABLE = True
except (ImportError, KeyError, Exception) as e:
    pyautogui = None
    _PYAUTOGUI_AVAILABLE = False
    logger.warning(f"pyautogui not available: {e}")

try:
    import pytesseract
    _PYTESSERACT_AVAILABLE = True
except (ImportError, KeyError, Exception) as e:
    pytesseract = None
    _PYTESSERACT_AVAILABLE = False
    logger.warning(f"pytesseract not available: {e}")

# Tesseract setup — only if available
if _PYTESSERACT_AVAILABLE:
    for candidate in (
        os.environ.get("TESSERACT_CMD", ""),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ):
        if candidate and os.path.isfile(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            break


class BrowserController:

    def __init__(self):
        self._last_url = ""
        self._last_search_query = ""

    @staticmethod
    def _ensure_chrome():
        """Focus or start Chrome on Windows (skipped on Linux)."""
        if os.name == "nt":  # Windows only
            subprocess.Popen("start chrome", shell=True)
            time.sleep(3)

    def open_browser(self, browser_name: str = "chrome"):
        if browser_name.lower() not in {"chrome", "google chrome"}:
            raise ValueError("Only Chrome is supported.")

        if not _PYAUTOGUI_AVAILABLE:
            return "Browser automation not available on server."

        self._ensure_chrome()
        return "Chrome opened and is ready."

    def navigate_to_url(self, url: str, browser_name: str = "chrome"):
        if not _PYAUTOGUI_AVAILABLE:
            return "Browser automation not available on server."

        self._ensure_chrome()
        if not url.startswith("http"):
            url = "https://" + url
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.3)
        pyautogui.typewrite(url, interval=0.01)
        pyautogui.press("enter")
        time.sleep(2)
        self._last_url = url
        return f"Navigated to {url}"

    def search_page(self, query: str):
        if not _PYAUTOGUI_AVAILABLE:
            return "Browser automation not available on server."

        self._ensure_chrome()
        # Assume search box is focused or use Ctrl+K / Ctrl+L
        pyautogui.hotkey("ctrl", "k")
        time.sleep(0.3)
        pyautogui.typewrite(query, interval=0.01)
        pyautogui.press("enter")
        time.sleep(2)
        self._last_search_query = query
        return f"Searched for: {query}"

    @staticmethod
    def _ocr_words(img):
        if not _PYTESSERACT_AVAILABLE:
            return []
        try:
            text = pytesseract.image_to_string(img)
            return text.split()
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return []

    def click_first_result(self):
        if not _PYAUTOGUI_AVAILABLE:
            return "Browser automation not available on server."

        # Take screenshot of top area and OCR for first clickable result
        try:
            screenshot = pyautogui.screenshot(region=(0, 100, 1920, 400))
            words = self._ocr_words(screenshot)
            if words:
                # Click on first text region
                pyautogui.click(200, 200)
                time.sleep(2)
                return "Clicked on first search result."
        except Exception as e:
            logger.error(f"Click first result failed: {e}")
        return "Could not find search result to click."

    def type_text(self, text: str):
        if not _PYAUTOGUI_AVAILABLE:
            return "Browser automation not available on server."

        try:
            pyautogui.typewrite(text, interval=0.01)
            return f"Typed {len(text)} characters."
        except Exception as e:
            logger.error(f"Type text failed: {e}")
            return f"Type failed: {e}"


# ==================================================
# MODULE-LEVEL HELPERS (used by browser_tools.py)
# ==================================================

_controller = BrowserController()


def open_browser(browser_name: str = "chrome"):
    return _controller.open_browser(browser_name)


def navigate_to_url(url: str, browser_name: str = "chrome"):
    return _controller.navigate_to_url(url, browser_name)


def search_page(query: str):
    return _controller.search_page(query)


def click_first_result():
    return _controller.click_first_result()


def type_text(text: str):
    return _controller.type_text(text)