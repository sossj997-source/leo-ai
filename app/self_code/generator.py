# app/self_code/generator.py
import logging
import re
from typing import Optional

from groq import Groq

logger = logging.getLogger("J.A.R.V.I.S")


SYSTEM_PROMPT = """You are a Python code generator for Leo, a personal AI assistant.

Your job: generate a single Python function based on the user's request.

RULES:
1. Output ONLY Python code - no explanation, no markdown fences, no commentary.
2. The function name must be a valid snake_case identifier.
3. Use only Python standard library + these packages if needed: requests, httpx, json, os, sys, subprocess, pathlib, datetime, re, math, random, hashlib, base64, urllib, shutil, tempfile, csv, sqlite3, threading, time, typing.
4. If the request needs a package that's not in the list above, use subprocess to call a system tool OR raise ValueError with clear message.
5. Include a docstring - one line describing what the tool does.
6. Return a serializable value (str, dict, list, int, float, bool, None).
7. No side effects on the host system unless explicitly requested.
8. No reading/writing files outside the current working directory unless explicitly requested.
9. Handle errors with try/except and return error string on failure.
10. Keep it short - 5-30 lines.

Format:
def function_name(args) -> return_type:
    \"\"\"One line docstring.\"\"\"
    ...
"""


class CodeGenerator:
    def __init__(self, groq_api_key: str, model: str = "openai/gpt-oss-120b"):
        self.client = Groq(api_key=groq_api_key)
        self.model = model

    def generate(self, request: str, error_context: Optional[str] = None) -> str:
        prompt = f"User request: {request}"
        if error_context:
            prompt += f"\n\nPrevious attempt failed with this error:\n{error_context}\n\nFix the code."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            raw = response.choices[0].message.content.strip()
            return self._strip_markdown(raw)

        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            raise RuntimeError(f"Code generation failed: {e}")

    def extract_function_name(self, code: str) -> Optional[str]:
        match = re.search(r"^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", code, re.MULTILINE)
        return match.group(1) if match else None

    @staticmethod
    def _strip_markdown(text: str) -> str:
        text = re.sub(r"^```(?:python)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()