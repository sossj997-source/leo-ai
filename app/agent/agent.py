import ast
import json
import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from app.agent.models import (
    AgentPlan,
    AgentRequest,
    AgentResponse,
    ToolCall,
    ToolResult,
)
from app.agent.tool_registry import ToolRegistry
from app.services.groq_service import GroqService


logger = logging.getLogger("JARVIS")


class Agent:
    """
    Leo Agent Brain.

    Flow:

        User Request
            ↓
        Understand / Plan
            ↓
        Select tools
            ↓
        Execute sequentially
            ↓
        Verify results
            ↓
        Recover / retry when possible
            ↓
        Final response
    """

    def __init__(
        self,
        groq_service: GroqService,
        tool_registry: ToolRegistry,
    ):
        self.groq_service = groq_service
        self.tool_registry = tool_registry

    # ==================================================
    # TOOL DESCRIPTION
    # ==================================================

    def _get_tools_description(self) -> str:
        tools = self.tool_registry.get_tool_schemas()

        if not tools:
            return "No tools are currently available."

        lines = []

        for tool in tools:
            confirmation = (
                "YES"
                if tool.get("requires_confirmation")
                else "NO"
            )

            parameters = tool.get("parameters", {})

            lines.append(
                f"- {tool['name']}: "
                f"{tool['description']} "
                f"| Parameters: {json.dumps(parameters)} "
                f"| Requires confirmation: {confirmation}"
            )

        return "\n".join(lines)

    # ==================================================
    # FOLDER NAME NORMALIZATION
    # ==================================================

    def _normalize_folder_name(
        self,
        folder_name: str,
    ) -> str:
        folder_name = folder_name.strip()

        folder_name = re.sub(
            r"^(the\s+)?",
            "",
            folder_name,
            flags=re.IGNORECASE,
        )

        return folder_name.strip()

    # ==================================================
    # DETECT OPEN FOLDER
    # ==================================================

    def _detect_open_folder(
        self,
        message: str,
    ) -> Optional[ToolCall]:

        if not self.tool_registry.has("open_folder"):
            return None

        text = message.strip()

        patterns = [
            r"^\s*open\s+(?:the\s+)?folder\s+(.+?)\s*$",
            r"^\s*open\s+(?:the\s+)?directory\s+(.+?)\s*$",
            r"^\s*open\s+(?:the\s+)?(.+?)\s*$",
        ]

        for pattern in patterns:
            match = re.match(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            target = match.group(1).strip()

            app_names = {
                "notepad",
                "calculator",
                "calc",
                "paint",
                "mspaint",
                "wordpad",
                "chrome",
                "google chrome",
                "edge",
                "microsoft edge",
                "firefox",
                "browser",
            }

            if target.lower() in app_names:
                return None

            known_folders = {
                "desktop",
                "downloads",
                "download",
                "documents",
                "documents folder",
                "pictures",
                "pictures folder",
                "music",
                "videos",
            }

            if target.lower() in known_folders:
                return ToolCall(
                    tool_name="open_folder",
                    arguments={
                        "folder_name": self._normalize_folder_name(
                            target
                        )
                    },
                )

        return None

    # ==================================================
    # DETECT LIST FILES
    # ==================================================

    def _detect_list_files(
        self,
        message: str,
    ) -> Optional[ToolCall]:

        if not self.tool_registry.has("list_files"):
            return None

        text = message.lower().strip()

        patterns = [
            r"list\s+(?:the\s+)?files(?:\s+in\s+(?:the\s+)?(.+))?",
            r"show\s+(?:the\s+)?files(?:\s+in\s+(?:the\s+)?(.+))?",
            r"what\s+files\s+are\s+in\s+(?:the\s+)?(.+)",
            r"show\s+me\s+(?:the\s+)?files\s+in\s+(?:the\s+)?(.+)",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            folder = (
                match.group(1)
                if match.lastindex
                else None
            )

            folder = (
                folder.strip()
                if folder
                else "Downloads"
            )

            return ToolCall(
                tool_name="list_files",
                arguments={
                    "folder_name": folder
                },
            )

        return None

    # ==================================================
    # DETECT CREATE FOLDER
    # ==================================================

    def _detect_create_folder(
        self,
        message: str,
    ) -> Optional[ToolCall]:

        if not self.tool_registry.has("create_folder"):
            return None

        text = message.strip()

        patterns = [
            r"create\s+(?:a\s+)?folder\s+(?:named\s+|called\s+)?(.+?)\s+(?:on|in|inside)\s+(?:the\s+)?(.+)",
            r"make\s+(?:a\s+)?folder\s+(?:named\s+|called\s+)?(.+?)\s+(?:on|in|inside)\s+(?:the\s+)?(.+)",
            r"new\s+folder\s+(?:named\s+|called\s+)?(.+?)\s+(?:on|in|inside)\s+(?:the\s+)?(.+)",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            folder_name = match.group(1).strip()
            location = match.group(2).strip()

            return ToolCall(
                tool_name="create_folder",
                arguments={
                    "folder_name": folder_name,
                    "location": location,
                },
            )

        return None

    # ==================================================
    # DETECT FIND FILE
    # ==================================================

    def _detect_find_file(
        self,
        message: str,
    ) -> Optional[ToolCall]:

        if not self.tool_registry.has("find_file"):
            return None

        text = message.strip()

        patterns = [
            r"find\s+(?:the\s+)?(?:file\s+)?(?:named\s+|called\s+)?(.+?)\s+(?:in|inside|on)\s+(?:the\s+)?(.+)",
            r"search\s+(?:for\s+)?(?:the\s+)?(?:file\s+)?(?:named\s+|called\s+)?(.+?)\s+(?:in|inside|on)\s+(?:the\s+)?(.+)",
            r"locate\s+(?:the\s+)?(?:file\s+)?(?:named\s+|called\s+)?(.+?)\s+(?:in|inside|on)\s+(?:the\s+)?(.+)",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            file_name = match.group(1).strip()
            search_folder = match.group(2).strip()

            return ToolCall(
                tool_name="find_file",
                arguments={
                    "file_name": file_name,
                    "search_folder": search_folder,
                },
            )

        return None

    # ==================================================
    # DETECT OPEN FILE
    # ==================================================

    def _detect_open_file(
        self,
        message: str,
    ) -> Optional[ToolCall]:

        if not self.tool_registry.has("open_file"):
            return None

        text = message.strip()

        patterns = [
            r"^\s*open\s+(?:the\s+)?file\s+(.+?)\s*$",
            r"^\s*open\s+(?:the\s+)?file\s+at\s+(.+?)\s*$",
        ]

        for pattern in patterns:
            match = re.match(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            return ToolCall(
                tool_name="open_file",
                arguments={
                    "file_path": match.group(1).strip()
                },
            )

        return None

    # ==================================================
    # DETECT OPEN BROWSER
    # ==================================================

    def _detect_open_browser(
        self,
        message: str,
    ) -> Optional[ToolCall]:
        if not self.tool_registry.has("open_browser"):
            return None

        text = message.strip().lower()
        browser_map = {
            "chrome": "chrome",
            "google chrome": "chrome",
            "edge": "edge",
            "microsoft edge": "edge",
            "firefox": "firefox",
        }

        if text in {
            "open browser", "open the browser", "start browser",
            "start the browser", "launch browser", "launch the browser",
            "browser kholo", "browser khol do", "browser khol",
        }:
            return ToolCall(tool_name="open_browser", arguments={"browser_name": "chrome"})

        # Natural Hinglish variants: "chrome kholo", "chrome khol do".
        m = re.match(r"^\s*(chrome|google\s+chrome|edge|microsoft\s+edge|firefox)\s+(?:khol(?:o|na|do)?|open|start|launch)\s*$", text)
        if m:
            return ToolCall(
                tool_name="open_browser",
                arguments={"browser_name": browser_map[m.group(1)]},
            )

        return None

    # ==================================================
    # DETECT NAVIGATE URL
    # ==================================================

    def _detect_navigate_url(
        self,
        message: str,
    ) -> Optional[ToolCall]:
        if not self.tool_registry.has("navigate_to_url"):
            return None

        text = message.strip()
        lower = text.lower()

        # Common site aliases. These are deterministic so Hinglish commands
        # never depend on the LLM guessing a URL.
        sites = {
            "youtube": "https://www.youtube.com",
            "youtube.com": "https://www.youtube.com",
            "google": "https://www.google.com",
            "google.com": "https://www.google.com",
            "github": "https://github.com",
            "github.com": "https://github.com",
            "gmail": "https://mail.google.com",
            "gmail.com": "https://mail.google.com",
            "chatgpt": "https://chatgpt.com",
            "chatgpt.com": "https://chatgpt.com",
            "whatsapp": "https://web.whatsapp.com",
            "whatsapp web": "https://web.whatsapp.com",
            "instagram": "https://www.instagram.com",
            "facebook": "https://www.facebook.com",
            "reddit": "https://www.reddit.com",
        }

        # "YouTube kholo", "Google khol do", "GitHub open karo".
        m = re.match(
            r"^\s*(youtube(?:\.com)?|google(?:\.com)?|github(?:\.com)?|gmail(?:\.com)?|chatgpt(?:\.com)?|whatsapp(?:\s+web)?|instagram|facebook|reddit)\s+(?:khol(?:o|na|do)?|open|start|launch)(?:\s+kar(?:o|do)?)?\s*$",
            lower,
            re.IGNORECASE,
        )
        if m:
            return ToolCall(tool_name="navigate_to_url", arguments={"url": sites[m.group(1).lower()]})

        patterns = [
            r"^\s*(?:go\s+to|open|visit|navigate\s+to)\s+(https?://\S+)\s*$",
            r"^\s*(?:open|visit|go\s+to)\s+((?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/\S*)?)\s*$",
        ]
        for pattern in patterns:
            match = re.match(pattern, text, flags=re.IGNORECASE)
            if match:
                return ToolCall(tool_name="navigate_to_url", arguments={"url": match.group(1).strip()})
        return None

    # ==================================================
    # MATH NORMALIZATION
    # ==================================================

    def _normalize_math_expression(
        self,
        message: str,
    ) -> Optional[str]:

        text = message.lower().strip()

        non_math_patterns = [
            r"\bcreate\b",
            r"\bmake\b",
            r"\bopen\b",
            r"\bclose\b",
            r"\bdelete\b",
            r"\bremove\b",
            r"\blist\b",
            r"\bshow\s+files?\b",
            r"\bfind\b",
            r"\blocate\b",
            r"\bsearch\b",
            r"\bfolder\b",
            r"\bdirectory\b",
            r"\bfile\b",
            r"\bapplication\b",
            r"\bprogram\b",
        ]

        for pattern in non_math_patterns:
            if re.search(pattern, text):
                return None

        text = re.sub(
            r"\b(calculate|calculate\s+this|compute|solve|what\s+is)\b",
            " ",
            text,
        )

        replacements = [
            (r"\bmultiplied\s+by\b", "*"),
            (r"\btimes\b", "*"),
            (r"\binto\b", "*"),
            (r"\bdivided\s+by\b", "/"),
            (r"\bdivide\s+by\b", "/"),
            (r"\bby\b", "/"),
            (r"\bplus\b", "+"),
            (r"\badd\b", "+"),
            (r"\bminus\b", "-"),
            (r"\bsubtract\b", "-"),
        ]

        for pattern, replacement in replacements:
            text = re.sub(
                pattern,
                f" {replacement} ",
                text,
            )

        text = re.sub(
            r"\b(please|what|is|the|answer|of)\b",
            " ",
            text,
        )

        text = re.sub(
            r"[^0-9+\-*/().%\s]",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        if not text:
            return None

        if not re.search(r"\d", text):
            return None

        if not re.search(r"[+\-*/%]", text):
            return None

        try:
            tree = ast.parse(
                text,
                mode="eval",
            )

            allowed_nodes = (
                ast.Expression,
                ast.Constant,
                ast.BinOp,
                ast.UnaryOp,
                ast.Add,
                ast.Sub,
                ast.Mult,
                ast.Div,
                ast.Mod,
                ast.Pow,
                ast.USub,
                ast.UAdd,
            )

            for node in ast.walk(tree):
                if not isinstance(node, allowed_nodes):
                    return None

            return text

        except Exception:
            return None

    # ==================================================
    # DETECT CALCULATOR
    # ==================================================

    def _detect_calculator(
        self,
        message: str,
    ) -> Optional[ToolCall]:

        if not self.tool_registry.has("calculator"):
            return None

        expression = self._normalize_math_expression(
            message
        )

        if not expression:
            return None

        return ToolCall(
            tool_name="calculator",
            arguments={
                "expression": expression
            },
        )

    # ==================================================
    # DETECT TIME
    # ==================================================

    def _detect_time(
        self,
        message: str,
    ) -> Optional[ToolCall]:

        if not self.tool_registry.has("get_time"):
            return None

        text = message.lower()

        time_patterns = [
            r"\bwhat time\b",
            r"\bcurrent time\b",
            r"\btime now\b",
            r"\btime is it\b",
            r"\bwhat's the time\b",
            r"\bdate and time\b",
            r"\bcurrent date\b",
            r"\btoday's date\b",
        ]

        for pattern in time_patterns:
            if re.search(pattern, text):
                return ToolCall(
                    tool_name="get_time",
                    arguments={},
                )

        return None

    # ==================================================
    # DETECT PERCENTAGE
    # ==================================================

    def _detect_percentage(
        self,
        message: str,
    ) -> Optional[ToolCall]:

        if not self.tool_registry.has(
            "calculate_percentage"
        ):
            return None

        text = message.lower()

        match = re.search(
            r"(\d+(?:\.\d+)?)\s*%?\s*(?:of|from)\s*(\d+(?:\.\d+)?)",
            text,
        )

        if not match:
            match = re.search(
                r"(\d+(?:\.\d+)?)\s*percent\s*(?:of)?\s*(\d+(?:\.\d+)?)",
                text,
            )

        if not match:
            return None

        return ToolCall(
            tool_name="calculate_percentage",
            arguments={
                "value": float(match.group(2)),
                "percentage": float(match.group(1)),
            },
        )

    # ==================================================
    # LLM PLANNER
    # ==================================================

    def _create_plan(
        self,
        request: AgentRequest,
    ) -> Dict[str, Any]:

        tools_description = (
            self._get_tools_description()
        )

        prompt = f"""
You are Leo's autonomous Agent Brain.

Your job is to understand the user's request and
create an executable plan using ONLY the available tools.

AVAILABLE TOOLS:
{tools_description}

USER REQUEST:
{request.message}

Return ONLY valid JSON.

Required format:

{{
    "goal": "short description of the user's goal",
    "steps": [
        {{
            "tool_name": "exact_tool_name",
            "arguments": {{}}
        }}
    ]
}}

If no tool is required:

{{
    "goal": "short description",
    "steps": []
}}

STRICT RULES:

1. Never invent a tool.
2. Only use tools listed above.
3. Use exact tool names.
4. Arguments must exactly match the tool parameters.
5. Every step must be independently executable.
6. Order the steps logically.
7. Do not execute anything yourself.
8. Do not put explanations outside JSON.
9. For browser tasks, preserve the browser requested by the user.
10. If the user asks for multiple actions, create multiple ordered steps.
11. Understand natural Hinglish/Hindi commands such as "khol", "kholo", "khol do", "karo", "kar do", "dhundo", "pehla", and "aur phir".
12. Treat quoted text as exact user data (for example a search query) and never include instruction words such as "karo", "aur", "phir", or "first result" inside that data.
"""

        try:
            response = self.groq_service.llms[0].invoke(
                prompt
            )

            raw = response.content.strip()

            if raw.startswith("```"):
                raw = re.sub(
                    r"^```(?:json)?\s*",
                    "",
                    raw,
                    flags=re.IGNORECASE,
                )
                raw = re.sub(
                    r"\s*```$",
                    "",
                    raw,
                ).strip()

            decision = json.loads(raw)

            if not isinstance(decision, dict):
                raise ValueError(
                    "Planner returned invalid object."
                )

            if "goal" not in decision:
                decision["goal"] = request.message

            if "steps" not in decision:
                decision["steps"] = []

            if not isinstance(
                decision["steps"],
                list,
            ):
                decision["steps"] = []

            return decision

        except Exception as e:
            logger.error(
                f"Planner failed: {e}"
            )

            return {
                "goal": request.message,
                "steps": [],
            }

    # ==================================================
    # LLM DECISION FALLBACK
    # ==================================================

    def _decide_action(
        self,
        request: AgentRequest,
    ) -> Dict[str, Any]:

        tools_description = (
            self._get_tools_description()
        )

        prompt = f"""
You are Leo's Agent Brain.

Available tools:
{tools_description}

User request:
{request.message}

Decide how to handle the request.

Return ONLY valid JSON.

Normal response:
{{
    "action": "respond",
    "answer": "your answer"
}}

Tool:
{{
    "action": "tool",
    "tool_name": "exact_tool_name",
    "arguments": {{}}
}}

Rules:
- Never invent tools.
- Only use available tools.
- Use exact tool names.
- Arguments must match tool parameters.
"""

        try:
            response = self.groq_service.llms[0].invoke(
                prompt
            )

            raw = response.content.strip()

            if raw.startswith("```"):
                raw = re.sub(
                    r"^```(?:json)?\s*",
                    "",
                    raw,
                    flags=re.IGNORECASE,
                )
                raw = re.sub(
                    r"\s*```$",
                    "",
                    raw,
                ).strip()

            decision = json.loads(raw)

            if not isinstance(decision, dict):
                raise ValueError(
                    "Invalid agent decision."
                )

            return decision

        except Exception as e:
            logger.error(
                f"Agent decision failed: {e}"
            )

            return {
                "action": "respond",
                "answer": (
                    "Sorry Sirr, I couldn't "
                    "understand that request."
                ),
            }

    # ==================================================
    # DETERMINISTIC BROWSER WORKFLOW
    # ==================================================

    def _detect_browser_workflow(
        self,
        message: str,
    ) -> Optional[List[ToolCall]]:
        """Parse common natural-language browser workflows deterministically.

        Quoted phrases are treated as exact data. The parser supports English,
        Hinglish and common Hindi transliterations without relying on the LLM
        to extract a search query correctly.
        """
        text = message.strip()
        lower = text.lower()

        sites = {
            "youtube": "https://www.youtube.com",
            "youtube.com": "https://www.youtube.com",
            "google": "https://www.google.com",
            "google.com": "https://www.google.com",
        }
        site_key = next((k for k in sites if re.search(rf"\b{re.escape(k)}\b", lower)), None)

        search_markers = re.compile(
            r"\b(?:search|search\s+for|search\s+karo|search\s+kar|"
            r"dhundho|dhoondo|dhundo|dhoondho|khojo|find)\b",
            re.IGNORECASE,
        )
        if not site_key or not search_markers.search(lower):
            return None

        query = ""

        # 1) Quoted text has absolute priority.
        for pattern in (r'["“](.*?)["”]', r"'(.*?)'"):
            match = re.search(pattern, text)
            if match and match.group(1).strip():
                query = match.group(1).strip()
                break

        # 2) Natural form: youtube pe <query> search karo / google par <query> khojo
        if not query:
            match = re.search(
                r"\b(?:youtube|google)(?:\.com)?\s*(?:pe|par|on)?\s+"
                r"(.+?)\s+(?:search\s*)?(?:karo|kar|dhundho|dhoondo|dhundo|khojo|find)\b",
                text,
                re.IGNORECASE,
            )
            if match:
                query = match.group(1).strip()

        # 3) English/Hinglish form: search <query> and/aur/then ...
        if not query:
            match = re.search(
                r"\b(?:search|search\s+for|dhundho|dhoondo|dhundo|khojo|find)\b"
                r"\s*(?:on\s+(?:youtube|google)\s*)?"
                r"(?:[:,-]\s*)?(.+?)(?=\s*(?:,|\s)\s*(?:aur|and|then|phir)\b|$)",
                text,
                re.IGNORECASE,
            )
            if match:
                query = match.group(1).strip()

        query = query.strip(" \t,.-\"'“”")
        if not query:
            return None

        wants_first = bool(re.search(
            r"\b(?:first|1st|top|pehla|pehli|pahla|pahli)\b"
            r"(?:\s+(?:result|video|one|wala|wali))?",
            lower,
            re.IGNORECASE,
        ))

        calls = [
            ToolCall(
                tool_name="open_website",
                arguments={"url": sites[site_key]},
            ),
            ToolCall(
                tool_name="browser_search",
                arguments={"query": query},
            ),
        ]
        if wants_first:
            calls.append(
                ToolCall(
                    tool_name="browser_click_first_result",
                    arguments={},
                )
            )
        return calls

    # ==================================================
    # MULTI-STEP SPLITTER
    # ==================================================

    def _split_multi_step_command(
        self,
        message: str,
    ) -> List[str]:

        text = message.strip()

        parts = [text]

        patterns = [
            r"\s+and\s+then\s+",
            r"\s+then\s+",
        ]

        for pattern in patterns:
            new_parts = []

            for part in parts:
                new_parts.extend(
                    re.split(
                        pattern,
                        part,
                        flags=re.IGNORECASE,
                    )
                )

            parts = new_parts

        return [
            part.strip()
            for part in parts
            if part.strip()
        ]

    # ==================================================
    # LLM TOOLCALL CONVERSION
    # ==================================================

    def _plan_to_tool_calls(
        self,
        plan: Dict[str, Any],
    ) -> List[ToolCall]:

        calls = []

        for step in plan.get("steps", []):

            if not isinstance(step, dict):
                continue

            tool_name = step.get("tool_name")

            if not tool_name:
                continue

            if not self.tool_registry.has(tool_name):
                logger.warning(
                    f"Planner selected unavailable tool: "
                    f"{tool_name}"
                )
                continue

            arguments = step.get(
                "arguments",
                {},
            )

            if not isinstance(arguments, dict):
                arguments = {}

            calls.append(
                ToolCall(
                    tool_name=tool_name,
                    arguments=arguments,
                )
            )

        return calls
     # ============================================
    # PROACTIVE REMINDER DETECTOR
    # ============================================

    def _detect_reminder(self, message: str) -> Optional[ToolCall]:
        if not self.tool_registry.has("create_reminder"):
            return None

        text = message.lower().strip()

        # Daily / recurring: roz 21:35 ..., daily 9 pm ..., har din 7:30 ...
        daily_match = re.search(
            r"\b(?:roz|daily|har\s+din)\s+"
            r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?"
            r"(?:\s+(.+))?$",
            text,
            re.IGNORECASE,
        )

        if daily_match:
            hour = int(daily_match.group(1))
            minute = int(daily_match.group(2) or 0)
            meridiem = daily_match.group(3)
            reminder_message = (daily_match.group(4) or "Reminder").strip()

            if hour > 23 or minute > 59:
                return None

            if meridiem:
                if meridiem.lower() == "pm" and hour < 12:
                    hour += 12
                elif meridiem.lower() == "am" and hour == 12:
                    hour = 0

            now = datetime.now()
            run_at = now.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            if run_at <= now:
                run_at += timedelta(days=1)

            return ToolCall(
                tool_name="create_reminder",
                arguments={
                    "name": f"daily_reminder_{hour:02d}_{minute:02d}",
                    "run_at": run_at.isoformat(timespec="seconds"),
                    "message": reminder_message,
                    "repeat_seconds": 86400,
                },
            )

        # One-time relative: 10 seconds baad / 5 minutes later / 2 hours baad
        match = re.search(
            r"(\d+)\s*(second|seconds|sec|secs|minute|minutes|min|mins|hour|hours|hr|hrs)"
            r"\s*(baad|later)(?:\s+.*)?",
            text,
            re.IGNORECASE,
        )
        if not match:
            return None

        amount = int(match.group(1))
        unit = match.group(2).lower()

        if unit.startswith("second") or unit in {"sec", "secs"}:
            run_at = datetime.now() + timedelta(seconds=amount)
        elif unit.startswith("minute") or unit in {"min", "mins"}:
            run_at = datetime.now() + timedelta(minutes=amount)
        elif unit.startswith("hour") or unit in {"hr", "hrs"}:
            run_at = datetime.now() + timedelta(hours=amount)
        else:
            return None

        reminder_message = re.sub(
            r"^.*?\d+\s*(?:second|seconds|sec|secs|minute|minutes|min|mins|hour|hours|hr|hrs)"
            r"\s*(?:baad|later)\s*",
            "",
            text,
            count=1,
            flags=re.IGNORECASE,
        ).strip() or "Reminder"

        return ToolCall(
            tool_name="create_reminder",
            arguments={
                "name": f"reminder_{int(run_at.timestamp())}",
                "run_at": run_at.isoformat(timespec="seconds"),
                "message": reminder_message,
            },
        )

    def _select_tool(
        self,
        request: AgentRequest,
    ) -> Optional[ToolCall]:

        # Known deterministic detectors first.
        reminder_call = (
            self._detect_reminder(
                request.message
            )
        )

        if reminder_call:
            return reminder_call
        

        create_folder_call = (
            self._detect_create_folder(
                request.message
            )
        )

        if create_folder_call:
            return create_folder_call

        list_files_call = (
            self._detect_list_files(
                request.message
            )
        )

        if list_files_call:
            return list_files_call

        find_file_call = (
            self._detect_find_file(
                request.message
            )
        )

        if find_file_call:
            return find_file_call

        open_file_call = (
            self._detect_open_file(
                request.message
            )
        )

        if open_file_call:
            return open_file_call

        open_folder_call = (
            self._detect_open_folder(
                request.message
            )
        )

        if open_folder_call:
            return open_folder_call

        open_browser_call = (
            self._detect_open_browser(
                request.message
            )
        )

        if open_browser_call:
            return open_browser_call

        navigate_url_call = (
            self._detect_navigate_url(
                request.message
            )
        )

        if navigate_url_call:
            return navigate_url_call

        percentage_call = (
            self._detect_percentage(
                request.message
            )
        )

        if percentage_call:
            return percentage_call

        time_call = (
            self._detect_time(
                request.message
            )
        )

        if time_call:
            return time_call

        calculator_call = (
            self._detect_calculator(
                request.message
            )
        )

        if calculator_call:
            return calculator_call

        # LLM fallback.

        decision = self._decide_action(
            request
        )

        if decision.get("action") != "tool":
            return None

        tool_name = decision.get(
            "tool_name"
        )

        arguments = decision.get(
            "arguments",
            {},
        )

        if not tool_name:
            return None

        if not self.tool_registry.has(
            tool_name
        ):
            return None

        return ToolCall(
            tool_name=tool_name,
            arguments=arguments,
        )

    # ==================================================
    # EXECUTE TOOL
    # ==================================================

    def _execute_tool(
        self,
        tool_call: ToolCall,
    ) -> ToolResult:

        tool = self.tool_registry.get(
            tool_call.tool_name
        )

        if not tool:
            return ToolResult(
                tool_name=tool_call.tool_name,
                success=False,
                error=(
                    f"Tool '{tool_call.tool_name}' "
                    "is not available."
                ),
            )

        if tool.requires_confirmation:
            return ToolResult(
                tool_name=tool_call.tool_name,
                success=False,
                error=(
                    "This tool requires user "
                    "confirmation before execution."
                ),
            )

        try:
            result = self.tool_registry.execute(
                tool_call.tool_name,
                tool_call.arguments,
            )

            return ToolResult(
                tool_name=tool_call.tool_name,
                success=True,
                result=result,
            )

        except Exception as e:
            logger.error(
                f"Tool execution failed: {e}"
            )

            return ToolResult(
                tool_name=tool_call.tool_name,
                success=False,
                error=str(e),
            )

    # ==================================================
    # VERIFY RESULT
    # ==================================================

    def _verify_result(
        self,
        request: AgentRequest,
        tool_call: ToolCall,
        tool_result: ToolResult,
    ) -> bool:

        if not tool_result.success:
            return False

        if tool_result.result is None:
            return True

        return True

    # ==================================================
    # RECOVERY
    # ==================================================

    def _recover_tool_call(
        self,
        request: AgentRequest,
        failed_call: ToolCall,
        failed_result: ToolResult,
    ) -> Optional[ToolCall]:

        tools_description = (
            self._get_tools_description()
        )

        prompt = f"""
You are Leo's recovery system.

User request:
{request.message}

Failed tool:
{failed_call.tool_name}

Arguments:
{json.dumps(failed_call.arguments)}

Error:
{failed_result.error}

Available tools:
{tools_description}

Find a safe alternative only if one clearly exists.

Return ONLY JSON:

{{
    "retry": true,
    "tool_name": "exact_tool_name",
    "arguments": {{}}
}}

OR:

{{
    "retry": false
}}

Never invent tools.
"""

        try:
            response = self.groq_service.llms[0].invoke(
                prompt
            )

            raw = response.content.strip()

            if raw.startswith("```"):
                raw = re.sub(
                    r"^```(?:json)?\s*",
                    "",
                    raw,
                    flags=re.IGNORECASE,
                )
                raw = re.sub(
                    r"\s*```$",
                    "",
                    raw,
                ).strip()

            data = json.loads(raw)

            if not data.get("retry"):
                return None

            tool_name = data.get(
                "tool_name"
            )

            if not tool_name:
                return None

            if not self.tool_registry.has(
                tool_name
            ):
                return None

            arguments = data.get(
                "arguments",
                {},
            )

            if not isinstance(arguments, dict):
                arguments = {}

            return ToolCall(
                tool_name=tool_name,
                arguments=arguments,
            )

        except Exception as e:
            logger.error(
                f"Recovery failed: {e}"
            )

            return None

    # ==================================================
    # FINAL RESPONSE
    # ==================================================

    def _generate_final_response(
        self,
        request: AgentRequest,
        tool_results: List[ToolResult],
    ) -> str:

        successful_results = [
            result
            for result in tool_results
            if result.success
        ]

        if not successful_results:
            return (
                "Sirr, I couldn't complete "
                "that request."
            )

        results_text = "\n".join(
            [
                (
                    f"{result.tool_name}: "
                    f"{result.result}"
                )
                for result in successful_results
            ]
        )

        prompt = f"""
You are Leo.

User request:
{request.message}

Completed actions:
{results_text}

Give a concise natural response.

Do not mention:
- Agent Brain
- Tool Registry
- JSON
- internal implementation
- planning internals

Only describe what was actually completed.
"""

        try:
            response = self.groq_service.llms[0].invoke(
                prompt
            )

            return response.content.strip()

        except Exception as e:
            logger.error(
                f"Final response failed: {e}"
            )

            return "\n".join(
                str(result.result)
                for result in successful_results
            )

    # ==================================================
    # RUN
    # ==================================================

    def run(
        self,
        message: str,
        session_id: Optional[str] = None,
    ) -> AgentResponse:

        if not message or not message.strip():
            return AgentResponse(
                success=False,
                message=(
                    "Please give me a command, Sirr."
                ),
            )

        request = AgentRequest(
            message=message,
            session_id=session_id,
        )

        # ==================================================
        # FIRST: HANDLE KNOWN BROWSER WORKFLOWS
        # ==================================================

        browser_workflow = self._detect_browser_workflow(message)

        if browser_workflow:
            tool_calls: List[ToolCall] = []
            tool_results: List[ToolResult] = []

            for step_call in browser_workflow:
                result = self._execute_tool(step_call)
                tool_calls.append(step_call)
                tool_results.append(result)

                if not result.success:
                    return AgentResponse(
                        success=False,
                        message=(
                            f"Browser step '{step_call.tool_name}' "
                            f"failed. {result.error}"
                        ),
                        plan=AgentPlan(
                            goal=message,
                            steps=[call.tool_name for call in tool_calls],
                        ),
                        tool_calls=tool_calls,
                        tool_results=tool_results,
                    )

            return AgentResponse(
                success=True,
                message=self._generate_final_response(
                    request,
                    tool_results,
                ),
                plan=AgentPlan(
                    goal=message,
                    steps=[call.tool_name for call in tool_calls],
                ),
                tool_calls=tool_calls,
                tool_results=tool_results,
            )

        # ==================================================
        # FIRST: TRY LLM PLANNER FOR COMPLEX COMMANDS
        # ==================================================

        command_parts = (
            self._split_multi_step_command(
                message
            )
        )

        # Explicit multi-step commands use the planner.
        if len(command_parts) > 1:

            plan_data = self._create_plan(
                request
            )

            planned_calls = (
                self._plan_to_tool_calls(
                    plan_data
                )
            )

            # If planner successfully understood
            # the request, execute its ordered steps.
            if planned_calls:

                tool_calls: List[ToolCall] = []
                tool_results: List[ToolResult] = []

                browser_context = "default"

                for step_call in planned_calls:

                    if step_call.tool_name == "open_browser":
                        browser_context = (
                            step_call.arguments.get(
                                "browser_name",
                                "default",
                            )
                        )

                    elif step_call.tool_name == "navigate_to_url":
                        step_call.arguments[
                            "browser_name"
                        ] = browser_context

                    result = self._execute_tool(
                        step_call
                    )

                    tool_calls.append(
                        step_call
                    )

                    tool_results.append(
                        result
                    )

                    verified = self._verify_result(
                        request,
                        step_call,
                        result,
                    )

                    if verified:
                        continue

                    recovery_call = (
                        self._recover_tool_call(
                            request,
                            step_call,
                            result,
                        )
                    )

                    if not recovery_call:
                        return AgentResponse(
                            success=False,
                            message=(
                                f"Step '{step_call.tool_name}' "
                                "failed and could not be recovered."
                            ),
                            plan=AgentPlan(
                                goal=plan_data.get(
                                    "goal",
                                    message,
                                ),
                                steps=[
                                    call.tool_name
                                    for call in tool_calls
                                ],
                            ),
                            tool_calls=tool_calls,
                            tool_results=tool_results,
                        )

                    recovery_result = (
                        self._execute_tool(
                            recovery_call
                        )
                    )

                    tool_calls.append(
                        recovery_call
                    )

                    tool_results.append(
                        recovery_result
                    )

                    if not recovery_result.success:
                        return AgentResponse(
                            success=False,
                            message=(
                                f"Recovery for "
                                f"'{step_call.tool_name}' "
                                "also failed."
                            ),
                            plan=AgentPlan(
                                goal=plan_data.get(
                                    "goal",
                                    message,
                                ),
                                steps=[
                                    call.tool_name
                                    for call in tool_calls
                                ],
                            ),
                            tool_calls=tool_calls,
                            tool_results=tool_results,
                        )

                final_message = (
                    self._generate_final_response(
                        request,
                        tool_results,
                    )
                )

                return AgentResponse(
                    success=True,
                    message=final_message,
                    plan=AgentPlan(
                        goal=plan_data.get(
                            "goal",
                            message,
                        ),
                        steps=[
                            call.tool_name
                            for call in tool_calls
                        ],
                    ),
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                )

        # ==================================================
        # SINGLE COMMAND
        # ==================================================

        tool_call = self._select_tool(
            request
        )

        if not tool_call:

            decision = self._decide_action(
                request
            )

            answer = decision.get(
                "answer"
            )

            if not answer:
                answer = "I'm ready, Sirr."

            return AgentResponse(
                success=True,
                message=answer,
            )

        # ==================================================
        # EXECUTE SINGLE TOOL
        # ==================================================

        tool_result = self._execute_tool(
            tool_call
        )

        # ==================================================
        # RECOVERY FOR SINGLE TOOL
        # ==================================================

        if not self._verify_result(
            request,
            tool_call,
            tool_result,
        ):

            recovery_call = (
                self._recover_tool_call(
                    request,
                    tool_call,
                    tool_result,
                )
            )

            if recovery_call:

                recovery_result = (
                    self._execute_tool(
                        recovery_call
                    )
                )

                if recovery_result.success:

                    return AgentResponse(
                        success=True,
                        message=(
                            self._generate_final_response(
                                request,
                                [recovery_result],
                            )
                        ),
                        plan=AgentPlan(
                            goal=message,
                            steps=[
                                tool_call.tool_name,
                                recovery_call.tool_name,
                            ],
                        ),
                        tool_calls=[
                            tool_call,
                            recovery_call,
                        ],
                        tool_results=[
                            tool_result,
                            recovery_result,
                        ],
                    )

        # ==================================================
        # NORMAL SINGLE RESPONSE
        # ==================================================

        plan = AgentPlan(
            goal=message,
            steps=[
                f"Execute: {tool_call.tool_name}",
                "Verify result",
                "Respond",
            ],
        )

        if not tool_result.success:
            return AgentResponse(
                success=False,
                message=(
                    f"Tool '{tool_call.tool_name}' "
                    f"could not be executed. "
                    f"{tool_result.error}"
                ),
                plan=plan,
                tool_calls=[tool_call],
                tool_results=[tool_result],
            )

        final_message = (
            self._generate_final_response(
                request,
                [tool_result],
            )
        )

        return AgentResponse(
            success=True,
            message=final_message,
            plan=plan,
            tool_calls=[tool_call],
            tool_results=[tool_result],
        )