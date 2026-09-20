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

# ==================================================
# PRIVATE BOT — WHITELIST USER IDS
# ==================================================
# Sirf ye Telegram user IDs bot use kar sakte hain.
# Apna ID @userinfobot se pata karo aur yahan daalo.
ALLOWED_USER_IDS = [
    # 6299386764,   ← apna Telegram user ID yahan add karo
]

# Session store: per-telegram-user session IDs
_user_sessions = {}


def _is_allowed(user_id: int) -> bool:
    """Check if user is whitelisted. If list empty, allow everyone."""
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    
    if not _is_allowed(user.id):
        await update.message.reply_text("Sorry, ye bot private hai.")
        return
    
    welcome = (
        f"Namaste {user.first_name}! Main {ASSISTANT_NAME} hoon.\n\n"
        f"Aapka personal AI assistant — {JARVIS_USER_TITLE}.\n\n"
        f"Kuch bhi poochho, main help karunga."
    )
    await update.message.reply_text(welcome)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help            
