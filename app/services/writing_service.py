# app/services/writing_service.py
import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger("J.A.R.V.I.S")


class WritingService:
    """Handles all writing tasks - emails, reports, blogs, letters, summaries"""

    def __init__(self, groq_service):
        self.groq_service = groq_service
        self.output_dir = "outputs"
        self.template_dir = "app/templates"
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info("📝 WritingService initialized")

    def _load_template(self, template_name: str) -> str:
        """Load a writing template"""
        try:
            path = os.path.join(self.template_dir, f"{template_name}.txt")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            logger.warning(f"Template load failed: {e}")
        return ""

    def _save_output(self, content: str, filename: str = None) -> str:
        """Save written content to outputs folder"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"output_{timestamp}.txt"
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"💾 Saved output: {path}")
        return path

    def _generate(self, prompt: str, system: str = None) -> str:
        """
        Internal LLM call for writing.
        Uses groq_service's internal method safely.
        """
        try:
            system_msg = system or (
                "You are a professional writer. "
                "Output only the final written content. "
                "No explanations, no thinking, no meta-commentary."
            )

            full_prompt = f"{system_msg}\n\n{prompt}"

            # Try multiple methods in order of preference
            response = None

            # Method 1: get_response (most likely)
            if hasattr(self.groq_service, "get_response"):
                try:
                    response = self.groq_service.get_response(full_prompt)
                except Exception as e1:
                    logger.warning(f"get_response failed: {e1}")

            # Method 2: _invoke_llm with messages
            if response is None and hasattr(self.groq_service, "_invoke_llm"):
                try:
                    messages = [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt}
                    ]
                    response = self.groq_service._invoke_llm(messages=messages)
                except Exception as e2:
                    logger.warning(f"_invoke_llm failed: {e2}")

            # Method 3: Direct client (if exists)
            if response is None and hasattr(self.groq_service, "client"):
                try:
                    response = self.groq_service.client.chat.completions.create(
                        model=getattr(self.groq_service, "model", "llama-3.3-70b-versatile"),
                        messages=[
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=2048
                    )
                except Exception as e3:
                    logger.warning(f"direct client failed: {e3}")

            # Handle response
            if response is None:
                return "Error: No working LLM method found in groq_service."

            # If string
            if isinstance(response, str):
                return response.strip()

            # If response object with .choices
            if hasattr(response, "choices"):
                return response.choices[0].message.content.strip()

            # If dict
            if isinstance(response, dict):
                if "choices" in response:
                    return response["choices"][0]["message"]["content"].strip()
                if "content" in response:
                    return str(response["content"]).strip()

            return str(response).strip()

        except Exception as e:
            logger.error(f"Writing generation failed: {e}")
            return f"Error: {str(e)}"

    # ---- PUBLIC WRITING METHODS ----

    def write_email(self, purpose: str, recipient: str = "Sir", tone: str = "professional") -> Dict[str, Any]:
        """Write an email"""
        template = self._load_template("email")
        prompt = f"""Write a {tone} email.

Purpose: {purpose}
Recipient: {recipient}

{template}

Write the complete email with subject line, greeting, body, and closing."""
        content = self._generate(prompt)
        filename = f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = self._save_output(content, filename)
        return {"type": "email", "content": content, "path": path}

    def write_report(self, topic: str, details: str = "", length: str = "medium") -> Dict[str, Any]:
        """Write a structured report"""
        template = self._load_template("report")
        prompt = f"""Write a {length} professional report on the following topic.

Topic: {topic}
Additional details: {details}

{template}

Write the complete report with title, introduction, main sections, and conclusion."""
        content = self._generate(prompt)
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = self._save_output(content, filename)
        return {"type": "report", "content": content, "path": path}

    def write_blog(self, topic: str, tone: str = "casual", word_count: int = 500) -> Dict[str, Any]:
        """Write a blog post"""
        template = self._load_template("blog")
        prompt = f"""Write a {tone} blog post of approximately {word_count} words.

Topic: {topic}

{template}

Write the complete blog post with a catchy title, introduction, body, and conclusion."""
        content = self._generate(prompt)
        filename = f"blog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = self._save_output(content, filename)
        return {"type": "blog", "content": content, "path": path}

    def write_letter(self, purpose: str, recipient: str = "Sir", tone: str = "formal") -> Dict[str, Any]:
        """Write a formal or informal letter"""
        template = self._load_template("letter")
        prompt = f"""Write a {tone} letter.

Purpose: {purpose}
Recipient: {recipient}

{template}

Write the complete letter with date, address, salutation, body, and closing."""
        content = self._generate(prompt)
        filename = f"letter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = self._save_output(content, filename)
        return {"type": "letter", "content": content, "path": path}

    def write_summary(self, text: str, length: str = "short") -> Dict[str, Any]:
        """Summarize given text"""
        template = self._load_template("summary")
        prompt = f"""Summarize the following text in a {length} summary.

Text:
{text}

{template}

Write the summary."""
        content = self._generate(prompt)
        filename = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = self._save_output(content, filename)
        return {"type": "summary", "content": content, "path": path}

    def improve_text(self, text: str, style: str = "professional") -> Dict[str, Any]:
        """Improve existing text"""
        prompt = f"""Improve the following text in a {style} style. Keep the meaning intact but make it better.

Original text:
{text}

Write the improved version."""
        content = self._generate(prompt)
        filename = f"improved_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = self._save_output(content, filename)
        return {"type": "improved_text", "content": content, "path": path}

    def list_outputs(self) -> list:
        """List all saved writing outputs"""
        try:
            files = []
            for f in os.listdir(self.output_dir):
                path = os.path.join(self.output_dir, f)
                files.append({
                    "filename": f,
                    "size": os.path.getsize(path),
                    "modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
                })
            return sorted(files, key=lambda x: x["modified"], reverse=True)
        except Exception as e:
            logger.error(f"List outputs failed: {e}")
            return []

    def read_output(self, filename: str) -> Optional[str]:
        """Read a saved output"""
        try:
            path = os.path.join(self.output_dir, filename)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            logger.error(f"Read output failed: {e}")
        return None