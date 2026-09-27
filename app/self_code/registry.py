# app/self_code/registry.py
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger("J.A.R.V.I.S")


AUTO_TOOLS_DIR = Path("app/agent/tools/auto_tools")
REGISTRY_FILE = AUTO_TOOLS_DIR / "_registry.json"


class ToolRegistryManager:
    def __init__(self, tools_dir: Path = AUTO_TOOLS_DIR):
        self.tools_dir = tools_dir
        self.registry_file = self.tools_dir / "_registry.json"
        self.tools_dir.mkdir(parents=True, exist_ok=True)

        init_file = self.tools_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Auto-generated tools\n", encoding="utf-8")

        self.registry = self._load()

    def _load(self) -> Dict:
        if self.registry_file.exists():
            try:
                return json.loads(self.registry_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Registry load failed: {e}")
        return {"tools": {}}

    def _save(self):
        self.registry_file.write_text(
            json.dumps(self.registry, indent=2), encoding="utf-8"
        )

    def tool_exists(self, name: str) -> bool:
        return name in self.registry.get("tools", {})

    def save_tool(self, name: str, code: str, description: str) -> Path:
        file_path = self.tools_dir / f"{name}.py"
        file_path.write_text(code, encoding="utf-8")

        self.registry["tools"][name] = {
            "name": name,
            "file": str(file_path),
            "description": description,
        }
        self._save()

        logger.info(f"Tool saved: {name} -> {file_path}")
        return file_path

    def list_tools(self) -> List[Dict]:
        return list(self.registry.get("tools", {}).values())

    def get_tool(self, name: str) -> Optional[Dict]:
        return self.registry.get("tools", {}).get(name)

    def delete_tool(self, name: str) -> bool:
        tool = self.registry.get("tools", {}).pop(name, None)
        if not tool:
            return False
        try:
            Path(tool["file"]).unlink(missing_ok=True)
        except Exception:
            pass
        self._save()
        return True