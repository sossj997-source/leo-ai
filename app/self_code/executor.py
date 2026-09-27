# app/self_code/executor.py
import importlib.util
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("J.A.R.V.I.S")


class AutoToolExecutor:
    def __init__(self, tools_dir: Path):
        self.tools_dir = tools_dir
        self._loaded_modules = {}

    def load_tool(self, name: str, file_path: str):
        try:
            spec = importlib.util.spec_from_file_location(
                f"auto_tool_{name}", file_path
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load tool {name}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._loaded_modules[name] = module
            return module

        except Exception as e:
            logger.error(f"Tool load failed {name}: {e}")
            raise

    def call_tool(self, name: str, file_path: str, **kwargs) -> Any:
        if name not in self._loaded_modules:
            self.load_tool(name, file_path)

        module = self._loaded_modules[name]

        if not hasattr(module, name):
            raise AttributeError(f"Function {name} not found in tool module")

        func = getattr(module, name)
        return func(**kwargs)