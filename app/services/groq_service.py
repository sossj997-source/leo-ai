import json
import logging
import os
import time
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
)

from config import (
    GROQ_API_KEYS,
    GROQ_MODEL,
    JARVIS_SYSTEM_PROMPT,
    GENERAL_CHAT_ADDENDUM,
    ASSISTANT_NAME,
    JARVIS_USER_TITLE,
    BASE_DIR,
)

from app.utils.retry import with_retry
from app.utils.time_info import get_time_information
from app.services.memory_manager import MemoryManager


logger = logging.getLogger("JARVIS")

GROQ_REQUEST_TIMEOUT = 60

ALL_APIS_FAILED_MESSAGE = (
    "I'm unable to process your request. "
    "API services are temporarily unavailable."
)


class AllGroqApisFailedError(Exception):
    pass


def escape_curly_braces(text: str) -> str:
    if not text:
        return text

    return text.replace("{", "{{").replace("}", "}}")


def is_rate_limit_error(exc: BaseException) -> bool:
    msg = str(exc).lower()

    return (
        "429" in msg
        or "rate limit" in msg
    )


def mask_api_key(key: str) -> str:
    if key and len(key) > 12:
        return f"{key[:8]}...{key[-4:]}"

    return "***"


class GroqService:

    def __init__(self, vector_store_service):

        if not GROQ_API_KEYS:
            raise ValueError(
                "No Groq API keys found in .env"
            )

        self.llms = [
            ChatGroq(
                groq_api_key=key,
                model_name=GROQ_MODEL,
                temperature=0.6,
                request_timeout=GROQ_REQUEST_TIMEOUT,
            )
            for key in GROQ_API_KEYS
        ]

        self.vector_store_service = (
            vector_store_service
        )

        # Memory system
        self.memory_manager = MemoryManager()

        # User profile
        self.user_profile = ""

        try:
            profile_path = os.path.join(
                BASE_DIR,
                "database",
                "learning_data",
                "userdata.txt",
            )

            with open(
                profile_path,
                "r",
                encoding="utf-8",
            ) as f:
                self.user_profile = f.read().strip()

            logger.info(
                "User profile loaded successfully."
            )

        except Exception as e:
            logger.warning(
                f"Failed to load user profile: {e}"
            )

        logger.info(
            f"Initialized GroqService with "
            f"{len(GROQ_API_KEYS)} API key(s)."
        )

    # --------------------------------------------------
    # TOKEN USAGE
    # --------------------------------------------------

    def _log_token_usage(
        self,
        response,
        source="LLM",
    ):
        """
        Extract and display token usage from a
        LangChain/Groq response.

        Expected:
        Input tokens
        Output tokens
        Total tokens
        """

        try:
            usage = None

            # Newer LangChain response format
            if hasattr(response, "usage_metadata"):
                usage = response.usage_metadata

            # Fallback for older response metadata
            if not usage and hasattr(
                response,
                "response_metadata",
            ):
                metadata = response.response_metadata

                if isinstance(metadata, dict):
                    usage = metadata.get(
                        "token_usage"
                    )

                    if not usage:
                        usage = metadata.get(
                            "usage"
                        )

            if not isinstance(usage, dict):
                logger.info(
                    f"[TOKEN USAGE] {source}: "
                    "Usage data unavailable."
                )
                return

            input_tokens = usage.get(
                "input_tokens",
                usage.get(
                    "prompt_tokens",
                    0,
                ),
            )

            output_tokens = usage.get(
                "output_tokens",
                usage.get(
                    "completion_tokens",
                    0,
                ),
            )

            total_tokens = usage.get(
                "total_tokens",
                input_tokens + output_tokens,
            )

            print(
                "\n"
                "========== LEO TOKEN USAGE ==========\n"
                f"Input tokens : {input_tokens}\n"
                f"Output tokens: {output_tokens}\n"
                f"Total tokens : {total_tokens}\n"
                "======================================\n"
            )

            logger.info(
                f"[TOKEN USAGE] {source} | "
                f"input={input_tokens}, "
                f"output={output_tokens}, "
                f"total={total_tokens}"
            )

        except Exception as e:

            logger.warning(
                f"Failed to read token usage: {e}"
            )

    # --------------------------------------------------
    # NORMAL LLM REQUEST
    # --------------------------------------------------

    def _invoke_llm(
        self,
        prompt,
        messages,
        question,
    ):
        n = len(self.llms)
        last_exc = None

        for i in range(n):

            masked_key = mask_api_key(
                GROQ_API_KEYS[i]
            )

            logger.info(
                f"Trying API key #{i + 1}/{n} "
                f"({masked_key})"
            )

            try:
                chain = prompt | self.llms[i]

                response = with_retry(
                    lambda: chain.invoke(
                        {
                            "history": messages,
                            "question": question,
                        }
                    ),
                    max_retries=2,
                    initial_delay=0.5,
                )

                # TOKEN COUNTER
                self._log_token_usage(
                    response,
                    source=f"Normal LLM key #{i + 1}",
                )

                return response.content

            except Exception as e:

                last_exc = e

                if is_rate_limit_error(e):
                    logger.warning(
                        f"Key #{i + 1} rate limited."
                    )

                else:
                    logger.warning(
                        f"Key #{i + 1} failed: "
                        f"{str(e)[:100]}"
                    )

                if i < n - 1:
                    continue

                break

        raise AllGroqApisFailedError(
            ALL_APIS_FAILED_MESSAGE
        ) from last_exc

    # --------------------------------------------------
    # STREAMING LLM
    # --------------------------------------------------

    def _stream_llm(
        self,
        prompt,
        messages,
        question,
    ):
        n = len(self.llms)

        for i in range(n):

            try:
                chain = prompt | self.llms[i]

                chunk_count = 0
                start_time = time.perf_counter()

                last_chunk = None

                for chunk in chain.stream(
                    {
                        "history": messages,
                        "question": question,
                    }
                ):

                    last_chunk = chunk

                    content = ""

                    if hasattr(chunk, "content"):
                        content = chunk.content or ""

                    elif isinstance(chunk, dict):
                        content = (
                            chunk.get(
                                "content",
                                "",
                            )
                            or ""
                        )

                    if (
                        isinstance(content, str)
                        and content
                    ):
                        chunk_count += 1
                        yield content

                elapsed = (
                    time.perf_counter()
                    - start_time
                )

                # TOKEN COUNTER
                self._log_token_usage(
                    last_chunk,
                    source=f"Streaming LLM key #{i + 1}",
                )

                logger.info(
                    f"Stream completed with "
                    f"key #{i + 1} "
                    f"({chunk_count} chunks, "
                    f"{elapsed:.2f}s)."
                )

                return

            except Exception as e:

                if i < n - 1:

                    logger.info(
                        f"Stream failed on key "
                        f"#{i + 1}, "
                        f"falling back..."
                    )

                    continue

                raise AllGroqApisFailedError(
                    ALL_APIS_FAILED_MESSAGE
                ) from e

    # --------------------------------------------------
    # BUILD PROMPT
    # --------------------------------------------------

    def _build_prompt_and_messages(
        self,
        question,
        chat_history=None,
        extra_system_parts=None,
        mode_addendum="",
    ):

        context = ""

        try:

            retriever = (
                self.vector_store_service
                .get_retriever(k=10)
            )

            docs = retriever.invoke(
                question
            )

            if docs:

                context = "\n".join(
                    doc["content"]
                    for doc in docs
                )

        except Exception as e:

            logger.warning(
                f"Vector store failed: {e}"
            )

        system_message = (
            JARVIS_SYSTEM_PROMPT
        )

        # --------------------------------------------------
        # USER PROFILE
        # --------------------------------------------------

        if self.user_profile:

            system_message += (
                "\n\n===== USER PROFILE =====\n"
                "Use the following saved user profile "
                "as personal context. "
                "If older chat history conflicts "
                "with this profile, prefer this profile.\n\n"
                f"{escape_curly_braces(self.user_profile)}"
                "\n===== END USER PROFILE ====="
            )

        # --------------------------------------------------
        # SAVED MEMORIES
        # --------------------------------------------------

        memories = (
            self.memory_manager.get_memories()
        )

        if memories:

            memory_text = "\n".join(
                f"- {item['memory']}"
                for item in memories
            )

            system_message += (
                "\n\n===== SAVED MEMORIES =====\n"
                "Use these saved memories when relevant:\n"
                f"{memory_text}"
                "\n===== END SAVED MEMORIES ====="
            )

        # --------------------------------------------------
        # CURRENT TIME
        # --------------------------------------------------

        system_message += (
            "\n\nCurrent time: "
            f"{get_time_information()}"
        )

        # --------------------------------------------------
        # PAST CONTEXT
        # --------------------------------------------------

        if context:

            system_message += (
                "\n\nRelevant past context:\n"
                f"{escape_curly_braces(context)}"
            )

        # --------------------------------------------------
        # EXTRA SYSTEM PARTS
        # --------------------------------------------------

        if extra_system_parts:

            system_message += (
                "\n\n"
                + "\n\n".join(
                    extra_system_parts
                )
            )

        # --------------------------------------------------
        # MODE
        # --------------------------------------------------

        if mode_addendum:

            system_message += (
                f"\n\n{mode_addendum}"
            )

        # --------------------------------------------------
        # ASSISTANT NAME
        # --------------------------------------------------

        if ASSISTANT_NAME:

            system_message = (
                system_message.replace(
                    "JARVIS",
                    ASSISTANT_NAME,
                )
            )

        # --------------------------------------------------
        # USER TITLE
        # --------------------------------------------------

        if JARVIS_USER_TITLE:

            system_message += (
                "\n\nAlways address the user as "
                f"{JARVIS_USER_TITLE}."
            )

        # --------------------------------------------------
        # PROMPT
        # --------------------------------------------------

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    system_message,
                ),
                MessagesPlaceholder(
                    variable_name="history",
                ),
                (
                    "human",
                    "{question}",
                ),
            ]
        )

        messages = []

        if chat_history:

            for h, a in chat_history:

                messages.append(
                    HumanMessage(
                        content=h
                    )
                )

                messages.append(
                    AIMessage(
                        content=a
                    )
                )

        return prompt, messages

    # --------------------------------------------------
    # MEMORY EXTRACTION
    # --------------------------------------------------

    def _extract_memory(self, question):

        memory_prompt = """
You are a memory extraction system.

Read the user's message and decide whether it contains
useful information that should be remembered for future
conversations.

Save only stable, useful information such as:
- personal facts
- preferences
- important goals
- long-term projects
- recurring habits
- important instructions about how the assistant
  should interact

Do NOT save:
- casual conversation
- temporary information
- jokes
- greetings
- passwords
- API keys
- authentication codes
- financial credentials
- highly sensitive information

If there is useful information, output ONLY valid JSON:

{
  "save": true,
  "memory": "short clear statement",
  "type": "personal_fact"
}

If nothing should be remembered, output ONLY:

{
  "save": false
}
"""

        try:

            response = self.llms[0].invoke(
                memory_prompt
                + f"\n\nUser message:\n{question}"
            )

            # TOKEN COUNTER
            self._log_token_usage(
                response,
                source="Memory extraction",
            )

            raw = (
                response.content
                .strip()
            )

            if raw.startswith("```"):

                raw = raw.replace(
                    "```json",
                    "",
                )

                raw = raw.replace(
                    "```",
                    "",
                )

                raw = raw.strip()

            result = json.loads(raw)

            if result.get("save") is True:

                memory = (
                    result.get(
                        "memory",
                        "",
                    )
                    .strip()
                )

                memory_type = result.get(
                    "type",
                    "personal_fact",
                )

                if memory:

                    self.memory_manager.add_memory(
                        memory,
                        memory_type,
                    )

        except Exception as e:

            logger.warning(
                f"Memory extraction failed: {e}"
            )

    # --------------------------------------------------
    # NORMAL RESPONSE
    # --------------------------------------------------

    def get_response(
        self,
        question,
        chat_history=None,
    ):

        try:

            prompt, messages = (
                self._build_prompt_and_messages(
                    question,
                    chat_history,
                    mode_addendum=GENERAL_CHAT_ADDENDUM,
                )
            )

            response = self._invoke_llm(
                prompt,
                messages,
                question,
            )

            self._extract_memory(
                question
            )

            return response

        except AllGroqApisFailedError:

            raise

        except Exception as e:

            raise Exception(
                f"Groq error: {str(e)}"
            ) from e

    # --------------------------------------------------
    # NORMAL STREAMING RESPONSE
    # --------------------------------------------------

    def stream_response(
        self,
        question,
        chat_history=None,
    ):

        try:

            prompt, messages = (
                self._build_prompt_and_messages(
                    question,
                    chat_history,
                    mode_addendum=GENERAL_CHAT_ADDENDUM,
                )
            )

            yield from self._stream_llm(
                prompt,
                messages,
                question,
            )

            self._extract_memory(
                question
            )

        except AllGroqApisFailedError:

            raise

        except Exception as e:

            raise Exception(
                f"Stream error: {str(e)}"
            ) from e