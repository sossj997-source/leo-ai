# app/self_code/sandbox.py
import subprocess
import tempfile
import os
import logging
import sys
from typing import Tuple

logger = logging.getLogger("J.A.R.V.I.S")


SANDBOX_TIMEOUT = 15
SANDBOX_MEMORY_MB = 512


class SandboxExecutor:
    def __init__(self, timeout: int = SANDBOX_TIMEOUT, memory_mb: int = SANDBOX_MEMORY_MB):
        self.timeout = timeout
        self.memory_mb = memory_mb

    def test_code(self, code: str, function_name: str, test_args: dict = None) -> Tuple[bool, str]:
        test_args = test_args or {}

        # Auto-detect required args from function signature
        auto_args_code = """
import inspect
sig = inspect.signature(FUNC)
args = {}
for pname, param in sig.parameters.items():
    if param.default is inspect.Parameter.empty:
        ptype = param.annotation
        if ptype is int:
            args[pname] = 1
        elif ptype is float:
            args[pname] = 1.0
        elif ptype is bool:
            args[pname] = True
        elif ptype is list:
            args[pname] = []
        elif ptype is dict:
            args[pname] = {}
        else:
            pname_lower = pname.lower()
            if "url" in pname_lower or "link" in pname_lower:
                args[pname] = "https://example.com"
            elif "city" in pname_lower:
                args[pname] = "Delhi"
            elif "num" in pname_lower or "number" in pname_lower or "count" in pname_lower:
                args[pname] = 5
            elif "text" in pname_lower or "string" in pname_lower or "message" in pname_lower:
                args[pname] = "hello"
            elif "path" in pname_lower or "file" in pname_lower:
                args[pname] = "test.txt"
            else:
                args[pname] = "test"
INJECTED_ARGS = args
"""
        auto_args_code = auto_args_code.replace("FUNC", function_name)

        harness = f"""
import sys, json, traceback, inspect
sys.setrecursionlimit(100)

{code}

# Auto-generate args
{auto_args_code}

# Merge with explicit test_args
final_args = dict(INJECTED_ARGS)
final_args.update({repr(test_args)})

try:
    result = {function_name}(**final_args)
    print("__SUCCESS__")
    print(json.dumps({{"result": str(result)[:200]}}))
except Exception as e:
    print("__ERROR__")
    print(traceback.format_exc())
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(harness)
            tmp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=tempfile.gettempdir(),
            )

            stdout = result.stdout
            stderr = result.stderr

            if "__SUCCESS__" in stdout:
                return True, stdout
            elif "__ERROR__" in stdout:
                error_part = stdout.split("__ERROR__", 1)[1].strip()
                return False, error_part
            else:
                return False, f"stdout: {stdout[:500]}\nstderr: {stderr[:500]}"

        except subprocess.TimeoutExpired:
            return False, f"Timeout: code took longer than {self.timeout}s"
        except Exception as e:
            return False, f"Sandbox error: {e}"
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def validate_syntax(self, code: str) -> Tuple[bool, str]:
        try:
            compile(code, "<generated>", "exec")
            return True, "syntax OK"
        except SyntaxError as e:
            return False, f"SyntaxError: {e}"