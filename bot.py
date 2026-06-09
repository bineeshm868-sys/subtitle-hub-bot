import os
import pysrt

from deep_translator import GoogleTranslator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

CHANNEL_ID = -1002047353995
CHANNEL_URL = "https://t.me/subtitlehubofficial"

# ------------------------
# CHANNEL CHECK
# ------------------------

async def is_user_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id
        )
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


# ------------------------
# START
# ------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏠 Welcome To Subtitle Hub Bot\n\nChoose an option below:",
        reply_markup=main_menu()
    )


# ------------------------
# MAIN MENU
# ------------------------

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Translate Subtitle", callback_data="translate")],
        [InlineKeyboardButton("👤 My Account", callback_data="account")],
        [InlineKeyboardButton("💎 Premium", callback_data="premium")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
        [InlineKeyboardButton("📢 Updates Channel", url=CHANNEL_URL)]
    ])


# ------------------------
# HANDLERS (same as yours)
# ------------------------

# (button_handler and handle_document 그대로 use ചെയ്യാം — no change needed)


# ------------------------
# MAIN (IMPORTANT FIX)
# ------------------------

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
