import asyncio
import base64
import logging

import edge_tts


logger = logging.getLogger("JARVIS")


class EdgeTTSService:

    def __init__(
        self,
        voice="en-US-GuyNeural"
    ):
        self.voice = voice

    async def _generate_audio(
        self,
        text: str
    ):

        communicate = edge_tts.Communicate(
            text,
            self.voice
        )

        audio_data = bytearray()

        async for chunk in communicate.stream():

            if chunk["type"] == "audio":
                audio_data.extend(
                    chunk["data"]
                )

        return bytes(audio_data)

    def text_to_speech(
        self,
        text: str
    ):

        if not text or not text.strip():
            return None

        text = text.strip()

        if len(text) > 500:
            text = text[:500]

        try:

            audio_bytes = asyncio.run(
                self._generate_audio(text)
            )

            if not audio_bytes:
                return None

            return base64.b64encode(
                audio_bytes
            ).decode("utf-8")

        except Exception as e:

            logger.error(
                f"Edge TTS failed: {repr(e)}"
            )

            return None