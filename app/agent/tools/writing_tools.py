# app/agent/tools/writing_tools.py
import os
import time
import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger("J.A.R.V.I.S")

# Try to import pyautogui for text typing
try:
    import pyautogui
    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    _PYAUTOGUI_AVAILABLE = False
    logger.warning("pyautogui not available — editor typing will be limited")


# ==================================================
# TEXT EDITOR TOOLS (used by register_tools.py)
# ==================================================

def open_text_editor(editor: str = "notepad") -> dict:
    """
    Open Notepad or WordPad text editor.
    """
    try:
        editor = (editor or "notepad").lower().strip()

        if editor == "wordpad":
            try:
                subprocess.Popen(["write.exe"])
                time.sleep(1.5)
                return {"status": "success", "message": "Opened WordPad"}
            except Exception:
                subprocess.Popen(["notepad.exe"])
                time.sleep(1.5)
                return {"status": "success", "message": "WordPad not found — opened Notepad"}
        else:
            subprocess.Popen(["notepad.exe"])
            time.sleep(1.5)
            return {"status": "success", "message": "Opened Notepad"}

    except Exception as e:
        logger.error(f"open_text_editor failed: {e}")
        return {"status": "error", "message": str(e)}


def write_text(text: str, clear_existing: bool = False) -> dict:
    """
    Type text into the currently focused window using PyAutoGUI.
    """
    if not _PYAUTOGUI_AVAILABLE:
        return {"status": "error", "message": "pyautogui not installed."}

    try:
        if clear_existing:
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.2)
            pyautogui.press("delete")
            time.sleep(0.2)

        pyautogui.write(text, interval=0.01)
        return {"status": "success", "message": f"Typed {len(text)} characters"}

    except Exception as e:
        logger.error(f"write_text failed: {e}")
        return {"status": "error", "message": str(e)}


def open_editor_and_write(
    text: str,
    editor: str = "notepad",
    clear_existing: bool = False
) -> dict:
    """
    Open Notepad/WordPad, wait for it to focus, and type the text.
    """
    try:
        result = open_text_editor(editor)
        if result.get("status") == "error":
            return result

        time.sleep(2.0)
        return write_text(text, clear_existing=clear_existing)

    except Exception as e:
        logger.error(f"open_editor_and_write failed: {e}")
        return {"status": "error", "message": str(e)}


# ==================================================
# GLOBAL WRITING SERVICE REFERENCE
# ==================================================

_writing_service_ref = None


# ==================================================
# REGISTER FUNCTION (called from main.py)
# ==================================================

def register_writing_tools(registry, writing_service):
    """Register all writing tools with the agent tool registry"""
    global _writing_service_ref
    _writing_service_ref = writing_service

    # ------------------------------------------------
    # write_email
    # ------------------------------------------------
    def _write_email(purpose: str, recipient: str = "Sir", tone: str = "professional"):
        result = writing_service.write_email(purpose, recipient, tone)
        return {
            "status": "success",
            "type": "email",
            "content": result["content"],
            "saved_to": result["path"]
        }

    registry.register(
        name="write_email",
        description="Write a professional email. Use when user asks to write/compose an email.",
        function=_write_email,
        parameters={
            "purpose": {"type": "string", "description": "What the email is about", "required": True},
            "recipient": {"type": "string", "description": "Who the email is for", "default": "Sir"},
            "tone": {"type": "string", "description": "professional/casual/formal", "default": "professional"}
        },
        requires_confirmation=False,
    )

    # ------------------------------------------------
    # write_report
    # ------------------------------------------------
    def _write_report(topic: str, details: str = "", length: str = "medium"):
        result = writing_service.write_report(topic, details, length)
        return {
            "status": "success",
            "type": "report",
            "content": result["content"],
            "saved_to": result["path"]
        }

    registry.register(
        name="write_report",
        description="Write a structured report on any topic.",
        function=_write_report,
        parameters={
            "topic": {"type": "string", "description": "Report topic", "required": True},
            "details": {"type": "string", "description": "Extra details", "default": ""},
            "length": {"type": "string", "description": "short/medium/long", "default": "medium"}
        },
        requires_confirmation=False,
    )

    # ------------------------------------------------
    # write_blog
    # ------------------------------------------------
    def _write_blog(topic: str, tone: str = "casual", word_count: int = 500):
        result = writing_service.write_blog(topic, tone, word_count)
        return {
            "status": "success",
            "type": "blog",
            "content": result["content"],
            "saved_to": result["path"]
        }

    registry.register(
        name="write_blog",
        description="Write a blog post on any topic.",
        function=_write_blog,
        parameters={
            "topic": {"type": "string", "description": "Blog topic", "required": True},
            "tone": {"type": "string", "description": "casual/professional", "default": "casual"},
            "word_count": {"type": "integer", "description": "Approximate words", "default": 500}
        },
        requires_confirmation=False,
    )

    # ------------------------------------------------
    # write_letter
    # ------------------------------------------------
    def _write_letter(purpose: str, recipient: str = "Sir", tone: str = "formal"):
        result = writing_service.write_letter(purpose, recipient, tone)
        return {
            "status": "success",
            "type": "letter",
            "content": result["content"],
            "saved_to": result["path"]
        }

    registry.register(
        name="write_letter",
        description="Write a formal or informal letter.",
        function=_write_letter,
        parameters={
            "purpose": {"type": "string", "description": "Letter purpose", "required": True},
            "recipient": {"type": "string", "description": "Recipient", "default": "Sir"},
            "tone": {"type": "string", "description": "formal/informal", "default": "formal"}
        },
        requires_confirmation=False,
    )

    # ------------------------------------------------
    # write_summary
    # ------------------------------------------------
    def _write_summary(text: str, length: str = "short"):
        result = writing_service.write_summary(text, length)
        return {
            "status": "success",
            "type": "summary",
            "content": result["content"],
            "saved_to": result["path"]
        }

    registry.register(
        name="write_summary",
        description="Summarize any given text.",
        function=_write_summary,
        parameters={
            "text": {"type": "string", "description": "Text to summarize", "required": True},
            "length": {"type": "string", "description": "short/medium/long", "default": "short"}
        },
        requires_confirmation=False,
    )

    # ------------------------------------------------
    # improve_text
    # ------------------------------------------------
    def _improve_text(text: str, style: str = "professional"):
        result = writing_service.improve_text(text, style)
        return {
            "status": "success",
            "type": "improved_text",
            "content": result["content"],
            "saved_to": result["path"]
        }

    registry.register(
        name="improve_text",
        description="Improve existing text in a given style.",
        function=_improve_text,
        parameters={
            "text": {"type": "string", "description": "Text to improve", "required": True},
            "style": {"type": "string", "description": "professional/casual/formal", "default": "professional"}
        },
        requires_confirmation=False,
    )

    # ------------------------------------------------
    # list_writing_outputs
    # ------------------------------------------------
    def _list_writing_outputs():
        return {"status": "success", "files": writing_service.list_outputs()}

    registry.register(
        name="list_writing_outputs",
        description="List all saved writing files.",
        function=_list_writing_outputs,
        parameters={},
        requires_confirmation=False,
    )

    logger.info("✅ 6 Writing tools registered")