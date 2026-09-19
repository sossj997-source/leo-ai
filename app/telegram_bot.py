# app/telegram_bot.py
import logging
import os
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

# Session store: per-telegram-user session IDs
_user_sessions = {}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    welcome = (
        f"Namaste {user.first_name}! Main {ASSISTANT_NAME} hoon.\n\n"
        f"Aapka personal AI assistant — {JARVIS_USER_TITLE}.\n\n"
        f"Kuch bhi poochho, main help karunga."
    )
    await update.message.reply_text(welcome)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        f"*{ASSISTANT_NAME} Help*\n\n"
        "Commands:\n"
        "/start - Start conversation\n"
        "/help - Show this help\n"
        "/clear - Start fresh session\n"
        "/realtime - Toggle realtime mode\n\n"
        "Just type your message to chat!"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear session."""
    user_id = update.effective_user.id
    _user_sessions.pop(user_id, None)
    await update.message.reply_text("Session clear ho gaya. Fresh start karo!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages."""
    user_id = update.effective_user.id
    user_message = update.message.text

    if not user_message:
        return

    # Get or create session
    session_id = _user_sessions.get(user_id)

    # Determine mode (default: general)
    realtime = context.user_data.get("realtime", False)
    endpoint = "/chat/realtime" if realtime else "/chat"

    # Send typing indicator
    await update.message.chat.send_action(action="typing")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{LEO_API_URL}{endpoint}",
                json={"message": user_message, "session_id": session_id},
            )

        if response.status_code != 200:
            await update.message.reply_text(
                f"Error: {response.status_code}"
            )
            return

        data = response.json()
        _user_sessions[user_id] = data.get("session_id")
        reply = data.get("response", "No response")

        # Telegram has 4096 char limit
        if len(reply) > 4000:
            reply = reply[:4000] + "...\n\n(message truncated)"

        await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Telegram bot error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")


async def realtime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle realtime mode."""
    current = context.user_data.get("realtime", False)
    context.user_data["realtime"] = not current

    if context.user_data["realtime"]:
        await update.message.reply_text("Realtime mode ON — ab web search bhi hoga.")
    else:
        await update.message.reply_text("Realtime mode OFF — general chat mode.")


def start_telegram_bot():
    """Start the Telegram bot (called from main.py)."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled")
        return None

    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("clear", clear_command))
        application.add_handler(CommandHandler("realtime", realtime_command))
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )

        logger.info("Telegram bot initialized")
        return application

    except Exception as e:
        logger.error(f"Telegram bot init failed: {e}")
        return None