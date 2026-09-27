# app/self_code/main.py
import logging
from typing import Dict, Any

from app.self_code.generator import CodeGenerator
from app.self_code.sandbox import SandboxExecutor
from app.self_code.registry import ToolRegistryManager
from app.self_code.executor import AutoToolExecutor

logger = logging.getLogger("J.A.R.V.I.S")


MAX_RETRIES = 3


class SelfCodeEngine:
    def __init__(self, groq_api_key: str):
        self.generator = CodeGenerator(groq_api_key)
        self.sandbox = SandboxExecutor()
        self.registry = ToolRegistryManager()
        self.executor = AutoToolExecutor(self.registry.tools_dir)

    def build_tool(self, request: str, test_args: Dict[str, Any] = None) -> Dict:
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            logger.info(f"Self-code attempt {attempt}/{MAX_RETRIES}: {request}")

            try:
                code = self.generator.generate(request, error_context=last_error)
            except Exception as e:
                return {"success": False, "message": f"Generation failed: {e}"}

            func_name = self.generator.extract_function_name(code)
            if not func_name:
                last_error = "No function definition found in generated code."
                continue

            ok, msg = self.sandbox.validate_syntax(code)
            if not ok:
                last_error = msg
                continue

            ok, output = self.sandbox.test_code(code, func_name, test_args or {})
            if not ok:
                last_error = output
                continue

            file_path = self.registry.save_tool(
                name=func_name,
                code=code,
                description=request,
            )

            return {
                "success": True,
                "name": func_name,
                "file": str(file_path),
                "message": f"Tool '{func_name}' created and tested successfully.",
                "attempts": attempt,
            }

        return {
            "success": False,
            "message": f"Failed after {MAX_RETRIES} attempts. Last error: {last_error}",
        }

    def run_tool(self, name: str, **kwargs) -> Any:
        tool = self.registry.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")
        return self.executor.call_tool(name, tool["file"], **kwargs)

    def list_tools(self):
        return self.registry.list_tools()