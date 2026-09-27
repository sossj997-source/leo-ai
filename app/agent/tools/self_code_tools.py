# app/agent/tools/self_code_tools.py
import logging
from config import GROQ_API_KEYS
from app.self_code.main import SelfCodeEngine

logger = logging.getLogger("J.A.R.V.I.S")

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = SelfCodeEngine(groq_api_key=GROQ_API_KEYS[0])
    return _engine


def register_self_code_tools(tool_registry):
    @tool_registry.register(
        name="build_tool",
        description="Generate, test, and register a new Python tool from a natural language request.",
    )
    def build_tool(request: str) -> str:
        engine = _get_engine()
        result = engine.build_tool(request)
        if result["success"]:
            return f"Tool '{result['name']}' created. Attempts: {result.get('attempts', 1)}."
        return f"Failed: {result['message']}"

    @tool_registry.register(
        name="run_auto_tool",
        description="Run a previously generated tool by name with kwargs.",
    )
    def run_auto_tool(name: str, kwargs_json: str = "{}") -> str:
        import json
        engine = _get_engine()
        try:
            kwargs = json.loads(kwargs_json)
            result = engine.run_tool(name, **kwargs)
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {e}"

    @tool_registry.register(
        name="list_auto_tools",
        description="List all self-generated tools.",
    )
    def list_auto_tools() -> str:
        engine = _get_engine()
        tools = engine.list_tools()
        if not tools:
            return "No auto-generated tools yet."
        lines = [f"- {t['name']}: {t['description']}" for t in tools]
        return "\n".join(lines)

    logger.info("Self-code tools registered")