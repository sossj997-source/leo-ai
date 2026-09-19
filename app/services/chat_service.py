import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Iterator
import uuid
import re

from config import CHATS_DATA_DIR, MAX_CHAT_HISTORY_TURNS

from app.models import ChatMessage
from app.services.groq_service import GroqService
from app.services.realtime_service import RealTimeGroqService
from app.services.tts_service import EdgeTTSService


logger = logging.getLogger("JARVIS")

SAVE_EVERY_N_CHUNKS = 5


class ChatService:

    def __init__(
        self,
        groq_service: GroqService,
        realtime_service: RealTimeGroqService = None,
        tts_service: EdgeTTSService = None
    ):

        self.groq_service = groq_service
        self.realtime_service = realtime_service

        # Edge TTS
        self.tts_service = (
            tts_service
            if tts_service
            else EdgeTTSService()
        )

        self.sessions: Dict[
            str,
            List[ChatMessage]
        ] = {}

    # ==================================================
    # SESSION LOAD
    # ==================================================

    def load_session_from_disk(
        self,
        session_id: str
    ) -> bool:

        safe_id = (
            session_id
            .replace("-", "_")
            .replace(" ", "_")
        )

        filepath = (
            Path(CHATS_DATA_DIR)
            / f"chat_{safe_id}.json"
        )

        if not filepath.exists():
            return False

        try:

            with open(
                filepath,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            self.sessions[session_id] = [
                ChatMessage(**m)
                for m in data.get(
                    "messages",
                    []
                )
            ]

            return True

        except Exception as e:

            logger.warning(
                f"Failed to load {session_id}: {e}"
            )

            return False

    # ==================================================
    # SESSION VALIDATION
    # ==================================================

    def validate_session_id(
        self,
        session_id: str
    ) -> bool:

        if (
            not session_id
            or not session_id.strip()
            or len(session_id) > 255
        ):
            return False

        if (
            ".." in session_id
            or "/" in session_id
            or "\\" in session_id
        ):
            return False

        return True

    # ==================================================
    # GET / CREATE SESSION
    # ==================================================

    def get_or_create_session(
        self,
        session_id: Optional[str] = None
    ) -> str:

        if not session_id:

            session_id = str(
                uuid.uuid4()
            )

            self.sessions[
                session_id
            ] = []

            logger.info(
                f"New session created: {session_id}"
            )

            return session_id

        if not self.validate_session_id(
            session_id
        ):

            raise ValueError(
                "Invalid session ID format."
            )

        if session_id in self.sessions:
            return session_id

        if self.load_session_from_disk(
            session_id
        ):

            logger.info(
                f"Session loaded from disk: "
                f"{session_id}"
            )

            return session_id

        self.sessions[
            session_id
        ] = []

        logger.info(
            f"New session created with ID: "
            f"{session_id}"
        )

        return session_id

    # ==================================================
    # ADD MESSAGE
    # ==================================================

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ):

        if session_id not in self.sessions:

            self.sessions[
                session_id
            ] = []

        self.sessions[
            session_id
        ].append(
            ChatMessage(
                role=role,
                content=content
            )
        )

    # ==================================================
    # GET HISTORY
    # ==================================================

    def get_chat_history(
        self,
        session_id: str
    ) -> List[ChatMessage]:

        return self.sessions.get(
            session_id,
            []
        )

    # ==================================================
    # FORMAT HISTORY
    # ==================================================

    def format_history_for_llm(
        self,
        session_id: str,
        exclude_last: bool = False
    ) -> List[tuple]:

        messages = self.get_chat_history(
            session_id
        )

        history = []

        messages_to_process = (
            messages[:-1]
            if exclude_last and messages
            else messages
        )

        i = 0

        while i < len(
            messages_to_process
        ) - 1:

            if (
                messages_to_process[i].role
                == "user"
                and
                messages_to_process[i + 1].role
                == "assistant"
            ):

                history.append(
                    (
                        messages_to_process[i].content,
                        messages_to_process[i + 1].content
                    )
                )

                i += 2

            else:

                i += 1

        return history[
            -MAX_CHAT_HISTORY_TURNS:
        ]

    # ==================================================
    # NORMAL CHAT
    # ==================================================

    def process_message(
        self,
        session_id: str,
        user_message: str
    ) -> str:

        logger.info(
            f"[GENERAL] Session: "
            f"{session_id} | User: "
            f"{user_message[:50]}"
        )

        self.add_message(
            session_id,
            "user",
            user_message
        )

        chat_history = (
            self.format_history_for_llm(
                session_id,
                exclude_last=True
            )
        )

        response = (
            self.groq_service.get_response(
                question=user_message,
                chat_history=chat_history
            )
        )

        self.add_message(
            session_id,
            "assistant",
            response
        )

        return response

    # ==================================================
    # REALTIME CHAT
    # ==================================================

    def process_realtime_message(
        self,
        session_id: str,
        user_message: str
    ) -> str:

        if not self.realtime_service:

            raise ValueError(
                "Realtime service is not initialized."
            )

        logger.info(
            f"[REALTIME] Session: "
            f"{session_id} | User: "
            f"{user_message[:50]}"
        )

        self.add_message(
            session_id,
            "user",
            user_message
        )

        chat_history = (
            self.format_history_for_llm(
                session_id,
                exclude_last=True
            )
        )

        response = (
            self.realtime_service.get_response(
                question=user_message,
                chat_history=chat_history
            )
        )

        self.add_message(
            session_id,
            "assistant",
            response
        )

        return response

    # ==================================================
    # TTS SENTENCE BUFFER
    # ==================================================

    def _extract_complete_sentences(
        self,
        buffer: str
    ):

        """
        Extract complete sentences from streaming text.

        Example:
            "Hello Sirr. How are"
        becomes:
            ["Hello Sirr."]
            remaining = "How are"
        """

        sentences = []

        pattern = re.compile(
            r"(.+?[.!?](?:\s+|$))",
            re.DOTALL
        )

        while True:

            match = pattern.match(
                buffer
            )

            if not match:
                break

            sentence = (
                match.group(1)
                .strip()
            )

            if sentence:
                sentences.append(
                    sentence
                )

            buffer = buffer[
                match.end():
            ]

        return sentences, buffer

    # ==================================================
    # GENERATE TTS
    # ==================================================

    def _generate_tts(
        self,
        text: str
    ):

        if not text or not text.strip():
            return None

        try:

            audio = (
                self.tts_service
                .text_to_speech(
                    text
                )
            )

            if audio:

                return {
                    "audio": audio
                }

        except Exception as e:

            logger.warning(
                f"TTS failed: {repr(e)}"
            )

        return None

    # ==================================================
    # NORMAL STREAM
    # ==================================================

    def process_message_stream(
        self,
        session_id: str,
        user_message: str
    ) -> Iterator:

        self.add_message(
            session_id,
            "user",
            user_message
        )

        self.add_message(
            session_id,
            "assistant",
            ""
        )

        chat_history = (
            self.format_history_for_llm(
                session_id,
                exclude_last=True
            )
        )

        chunk_count = 0

        tts_buffer = ""

        try:

            for chunk in (
                self.groq_service
                .stream_response(
                    question=user_message,
                    chat_history=chat_history
                )
            ):

                if not isinstance(
                    chunk,
                    str
                ):
                    continue

                # Save text
                self.sessions[
                    session_id
                ][-1].content += chunk

                chunk_count += 1

                if (
                    chunk_count
                    % SAVE_EVERY_N_CHUNKS
                    == 0
                ):

                    self.save_chat_session(
                        session_id,
                        log_timing=False
                    )

                # Send text immediately
                yield chunk

                # Add to TTS buffer
                tts_buffer += chunk

                sentences, tts_buffer = (
                    self._extract_complete_sentences(
                        tts_buffer
                    )
                )

                # Generate audio sentence-by-sentence
                for sentence in sentences:

                    audio_event = (
                        self._generate_tts(
                            sentence
                        )
                    )

                    if audio_event:

                        yield audio_event

            # Remaining text
            if tts_buffer.strip():

                audio_event = (
                    self._generate_tts(
                        tts_buffer.strip()
                    )
                )

                if audio_event:
                    yield audio_event

        finally:

            self.save_chat_session(
                session_id
            )

    # ==================================================
    # REALTIME STREAM
    # ==================================================

    def process_realtime_message_stream(
        self,
        session_id: str,
        user_message: str
    ) -> Iterator:

        if not self.realtime_service:

            raise ValueError(
                "Realtime service is not initialized."
            )

        self.add_message(
            session_id,
            "user",
            user_message
        )

        self.add_message(
            session_id,
            "assistant",
            ""
        )

        chat_history = (
            self.format_history_for_llm(
                session_id,
                exclude_last=True
            )
        )

        chunk_count = 0

        tts_buffer = ""

        try:

            for chunk in (
                self.realtime_service
                .stream_response(
                    question=user_message,
                    chat_history=chat_history
                )
            ):

                # --------------------------------------
                # SEARCH RESULT
                # --------------------------------------

                if isinstance(
                    chunk,
                    dict
                ):

                    yield chunk

                    continue

                # --------------------------------------
                # TEXT
                # --------------------------------------

                if not isinstance(
                    chunk,
                    str
                ):

                    continue

                self.sessions[
                    session_id
                ][-1].content += chunk

                chunk_count += 1

                if (
                    chunk_count
                    % SAVE_EVERY_N_CHUNKS
                    == 0
                ):

                    self.save_chat_session(
                        session_id,
                        log_timing=False
                    )

                # Send text immediately
                yield chunk

                # --------------------------------------
                # TTS BUFFER
                # --------------------------------------

                tts_buffer += chunk

                sentences, tts_buffer = (
                    self._extract_complete_sentences(
                        tts_buffer
                    )
                )

                # --------------------------------------
                # SENTENCE TTS
                # --------------------------------------

                for sentence in sentences:

                    audio_event = (
                        self._generate_tts(
                            sentence
                        )
                    )

                    if audio_event:

                        yield audio_event

            # ------------------------------------------
            # REMAINING TEXT
            # ------------------------------------------

            if tts_buffer.strip():

                audio_event = (
                    self._generate_tts(
                        tts_buffer.strip()
                    )
                )

                if audio_event:

                    yield audio_event

        finally:

            self.save_chat_session(
                session_id
            )

    # ==================================================
    # SAVE SESSION
    # ==================================================

    def save_chat_session(
        self,
        session_id: str,
        log_timing: bool = True
    ):

        if (
            session_id not in self.sessions
            or not self.sessions[session_id]
        ):

            return

        safe_id = (
            session_id
            .replace("-", "_")
            .replace(" ", "_")
        )

        filepath = (
            Path(CHATS_DATA_DIR)
            / f"chat_{safe_id}.json"
        )

        data = {
            "session_id": session_id,
            "messages": [
                m.dict()
                for m in self.sessions[
                    session_id
                ]
            ]
        }

        try:

            t0 = (
                time.perf_counter()
                if log_timing
                else 0
            )

            with open(
                filepath,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    data,
                    f,
                    indent=2,
                    ensure_ascii=False
                )

            if log_timing:

                logger.info(
                    "Saved session to disk in "
                    f"{time.perf_counter() - t0:.3f}s"
                )

        except Exception as e:

            logger.error(
                f"Failed to save session: {e}"
            )