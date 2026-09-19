"""LEO Browser Tools - visible Chrome control via PyAutoGUI + OCR."""
from urllib.parse import urlparse
from app.agent.tools.browser_automation import open_browser as _open, navigate_to_url as _navigate, type_text as _type

def open_website(url: str) -> str:
    if not url or not url.strip(): raise ValueError("URL cannot be empty.")
    url=url.strip()
    if not url.startswith(("http://","https://")): url="https://"+url
    p=urlparse(url)
    if p.scheme not in {"http","https"} or not p.netloc: raise ValueError("Invalid HTTP/HTTPS website URL.")
    return _navigate(url,"chrome")

def open_browser(browser_name: str="chrome") -> str: return _open(browser_name or "chrome")
def navigate_to_url(url: str,browser_name: str="chrome") -> str: return _navigate(url,browser_name or "chrome")
def type_text(text: str) -> str: return _type(text)
