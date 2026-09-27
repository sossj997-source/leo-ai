# app/telegram_bot.py
import logging
import os
import io
import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from config import (
    TELEGRAM_BOT_TOKEN,
    LEO_API_URL,
    ASSISTANT_NAME,
    JARVIS_USER_TITLE,
)

logger = logging.getLogger("J.A.R.V.I.S")

# ==================================================
# PRIVATE BOT - WHITELIST
# ==================================================
ALLOWED_USER_IDS = [
    6299386764,   # Sirr
]

# Rate limit: per-user daily message cap
DAILY_LIMIT = 300
_user_daily_count = {}

# Session store
_user_sessions = {}


def _is_allowed(user_id: int) -> bool:
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS


def _check_rate(user_id: int) -> bool:
    """Returns True if under limit, False if exceeded."""
    import datetime
    today = datetime.date.today().isoformat()
    key = f"{user_id}:{today}"
    count = _user_daily_count.get(key, 0)
    if count >= DAILY_LIMIT:
        return False
    _user_daily_count[key] = count + 1
    return True


async def _ask_leo(message: str, session_id: str, realtime: bool = False) -> tuple:
    """Send message to Leo API. Returns (reply_text, new_session_id)."""
    endpoint = "/chat/realtime" if realtime else "/chat"
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{LEO_API_URL}{endpoint}",
            json={"message": message, "session_id": session_id},
        )
    if response.status_code != 200:
        return f"Error: {response.status_code}", session_id
    data = response.json()
    return data.get("response", "No response"), data.get("session_id", session_id)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not _is_allowed(user.id):
        await update.message.reply_text("Sorry, ye bot private hai.")
        return
    welcome = (
        f"Namaste {user.first_name}! Main {ASSISTANT_NAME} hoon.\n\n"
        f"Aapka personal AI assistant — {JARVIS_USER_TITLE}.\n\n"
        f"Text ya voice note bhejo — dono chalega."
    )
    await update.message.reply_text(welcome)


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(f"Tumhara Telegram ID: `{user.id}`", parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not _is_allowed(user.id):
        await update.message.reply_text("Sorry, ye bot private hai.")
        return
    help_text = (
        f"*{ASSISTANT_NAME} Help*\n\n"
        "/start - Start\n"
        "/help - Yeh help\n"
        "/myid - Tumhara Telegram ID\n"
        "/clear - Fresh session\n"
        "/realtime - Web search toggle\n\n"
        "Text ya voice note bhejo."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not _is_allowed(user.id):
        await update.message.reply_text("Sorry, ye bot private hai.")
        return
    _user_sessions.pop(user.id, None)
    await update.message.reply_text("Session clear. Fresh start.")


async def realtime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not _is_allowed(user.id):
        await update.message.reply_text("Sorry, ye bot private hai.")
        return
    current = context.user_data.get("realtime", False)
    context.user_data["realtime"] = not current
    state = "ON — web search bhi hoga" if context.user_data["realtime"] else "OFF — general mode"
    await update.message.reply_text(f"Realtime mode {state}.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not _is_allowed(user.id):
        await update.message.reply_text("Sorry, ye bot private hai.")
        return
    if not _check_rate(user.id):
        await update.message.reply_text(f"Daily limit ({DAILY_LIMIT}) khatam. Kal try karo.")
        return

    user_message = update.message.text
    if not user_message:
        return

    session_id = _user_sessions.get(user.id)
    realtime = context.user_data.get("realtime", False)
    await update.message.chat.send_action(action="typing")

    try:
        reply, new_session = await _ask_leo(user_message, session_id, realtime)
        _user_sessions[user.id] = new_session
        if len(reply) > 4000:
            reply = reply[:4000] + "...\n\n(truncated)"
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"Telegram bot error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice notes: transcribe via Groq Whisper, send to Leo, reply with voice."""
    user = update.effective_user
    if not _is_allowed(user.id):
        await update.message.reply_text("Sorry, ye bot private hai.")
        return
    if not _check_rate(user.id):
        await update.message.reply_text(f"Daily limit ({DAILY_LIMIT}) khatam. Kal try karo.")
        return

    from groq import Groq
    from config import GROQ_API_KEYSS

    await update.message.chat.send_action(action="typing")

    try:
        # Download voice file
        voice_file = await update.message.voice.get_file()
        audio_bytes = await voice_file.download_as_bytearray()

        # Transcribe via Groq Whisper
        groq_client = Groq(api_key=GROQ_API_KEYS[0])
        transcription = groq_client.audio.transcriptions.create(
            file=("voice.ogg", bytes(audio_bytes)),
            model="whisper-large-v3-turbo",
            language="hi",
        )
        user_text = transcription.text.strip()
        if not user_text:
            await update.message.reply_text("Kuch samajh nahi aaya. Phir bolo.")
            return

        # Send to Leo
        session_id = _user_sessions.get(user.id)
        realtime = context.user_data.get("realtime", False)
        reply, new_session = await _ask_leo(user_text, session_id, realtime)
        _user_sessions[user.id] = new_session

        # Reply text (show transcription + reply)
        short_reply = reply[:4000] + ("..." if len(reply) > 4000 else "")
        await update.message.reply_text(f"🎤 _{user_text}_\n\n{short_reply}", parse_mode="Markdown")

        # Reply voice — only first 300 chars
        try:
            from app.services.tts_service import EdgeTTSService
            import base64
            tts = EdgeTTSService(voice="en-IN-PrabhatNeural")
            voice_b64 = tts.text_to_speech(reply[:300])
            if voice_b64:
                audio_out = base64.b64decode(voice_b64)
                await update.message.reply_voice(voice=io.BytesIO(audio_out))
        except Exception as tts_err:
            logger.warning(f"TTS reply failed: {tts_err}")

    except Exception as e:
        logger.error(f"Voice handler error: {e}")
        await update.message.reply_text(f"Voice error: {str(e)}")


def start_telegram_bot():
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled")
        return None
    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("myid", myid_command))
        application.add_handler(CommandHandler("clear", clear_command))
        application.add_handler(CommandHandler("realtime", realtime_command))
        application.add_handler(MessageHandler(filters.VOICE, handle_voice))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        logger.info("Telegram bot initialized")
        return application
    except Exception as e:
        logger.error(f"Telegram bot init failed: {e}")
        return None