"""Leo browser automation using normal Chrome + PyAutoGUI + OCR.
No CDP, no port 9222, no Chrome extension, no separate profile.
"""
from __future__ import annotations
import os, re, subprocess, time
from urllib.parse import quote_plus
import pyautogui
import pytesseract

for candidate in (os.environ.get("TESSERACT_CMD", ""), r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
    if candidate and os.path.isfile(candidate):
        pytesseract.pytesseract.tesseract_cmd = candidate
        break

class BrowserController:
    def __init__(self):
        self._last_url = ""
        self._last_search_query = ""

    @staticmethod
    def _ensure_chrome():
        subprocess.Popen("start chrome", shell=True)
        time.sleep(3)

    def open_browser(self, browser_name="chrome"):
        if browser_name.lower() not in {"chrome", "google chrome"}:
            raise ValueError("Only Chrome is supported.")
        self._ensure_chrome()
        return "Chrome opened and is ready."

    def navigate_to_url(self, url, browser_name="chrome"):
        if browser_name.lower() not in {"chrome", "google chrome"}:
            raise ValueError("Only Chrome is supported.")
        url=(url or "").strip()
        if not url: raise ValueError("URL cannot be empty.")
        if not url.startswith(("http://","https://")): url="https://"+url
        self._ensure_chrome()
        pyautogui.hotkey("ctrl","l"); pyautogui.write(url, interval=0.005); pyautogui.press("enter")
        time.sleep(5); self._last_url=url
        return f"Opened {url} in Chrome."

    def search_page(self, query):
        query=(query or "").strip()
        if not query: raise ValueError("Search query cannot be empty.")
        current=self._last_url.lower()
        if "youtube.com" in current: url="https://www.youtube.com/results?search_query="+quote_plus(query)
        else: url="https://www.google.com/search?q="+quote_plus(query)
        pyautogui.hotkey("ctrl","l"); pyautogui.write(url, interval=0.005); pyautogui.press("enter")
        time.sleep(6); self._last_url=url; self._last_search_query=query
        return f"Searched for '{query}'."

    @staticmethod
    def _ocr_words(img):
        data=pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        words=[]
        for i, raw in enumerate(data["text"]):
            text=raw.strip()
            if not text: continue
            try: conf=float(data["conf"][i])
            except Exception: conf=0
            if conf < 35: continue
            words.append({"text":text,"conf":conf,"x":int(data["left"][i]),"y":int(data["top"][i]),"w":int(data["width"][i]),"h":int(data["height"][i])})
        return words

    def click_first_result(self):
        words=self._ocr_words(pyautogui.screenshot())
        query_words={w.lower() for w in re.findall(r"[A-Za-z0-9]+", self._last_search_query) if len(w)>=3}
        if not query_words: raise RuntimeError("No previous browser search query is available for OCR click.")
        hits=[w for w in words if w["text"].lower() in query_words and w["y"]>120]
        if not hits:
            hits=[w for w in words if any(q in w["text"].lower() or w["text"].lower() in q for q in query_words) and w["y"]>120]
        if not hits: raise RuntimeError("OCR could not find the searched result on screen.")
        first_y=min(w["y"] for w in hits)
        near=[w for w in words if abs(w["y"]-first_y)<120 and w["y"]>120]
        x1=min(w["x"] for w in near); x2=max(w["x"]+w["w"] for w in near)
        y1=min(w["y"] for w in near); y2=max(w["y"]+w["h"] for w in near)
        sw,sh=pyautogui.size(); cx=min(max((x1+x2)//2,250),sw-100); cy=min(max((y1+y2)//2,180),sh-100)
        pyautogui.moveTo(cx,cy,duration=.35); time.sleep(.8); pyautogui.click(cx,cy); time.sleep(4)
        return f"Clicked the first visible search result at ({cx}, {cy})."

    def type_text(self, text):
        if text is None: raise ValueError("Text cannot be None.")
        pyautogui.write(str(text), interval=.01)
        return "Typed the requested text in the active Chrome field."

_controller=BrowserController()
open_browser=lambda browser_name="chrome": _controller.open_browser(browser_name)
navigate_to_url=lambda url,browser_name="chrome": _controller.navigate_to_url(url,browser_name)
search_page=lambda query: _controller.search_page(query)
click_first_result=lambda: _controller.click_first_result()
type_text=lambda text: _controller.type_text(text)
