# app/services/tts_service.py
import asyncio
import base64
import logging
import threading

import edge_tts


logger = logging.getLogger("JARVIS")


class EdgeTTSService:

    def __init__(self, voice="hi-IN-MadhurNeural"):
        self.voice = voice

    async def _generate_audio(self, text: str):
        communicate = edge_tts.Communicate(text, self.voice)
        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
        return bytes(audio_data)

    def text_to_speech(self, text: str):
        if not text or not text.strip():
            return None

        text = text.strip()
        if len(text) > 500:
            text = text[:500]

        result = {"audio": None, "error": None}

        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                audio_bytes = loop.run_until_complete(self._generate_audio(text))
                loop.close()
                if audio_bytes:
                    result["audio"] = base64.b64encode(audio_bytes).decode("utf-8")
            except Exception as e:
                result["error"] = repr(e)

        thread = threading.Thread(target=run_async)
        thread.start()
        thread.join(timeout=30)

        if result["error"]:
            logger.error(f"Edge TTS failed: {result['error']}")
            return None

        return result["audio"]