import os
import pysrt

from deep_translator import GoogleTranslator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

CHANNEL_ID = -1002047353995
CHANNEL_URL = "https://t.me/subtitlehubofficial"


# ---------------- CHECK JOIN ----------------
async def is_user_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id
        )
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


# ---------------- MENU ----------------
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Translate Subtitle", callback_data="translate")],
        [InlineKeyboardButton("👤 Account", callback_data="account")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ])


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if not await is_user_joined(user_id, context):

        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton("✅ I Joined", callback_data="check_join")]
        ]

        await update.message.reply_text(
            "🔒 Please join our channel to use this bot:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await update.message.reply_text(
        "🏠 Welcome Subtitle Translator Bot",
        reply_markup=main_menu()
    )


# ---------------- BUTTON HANDLER ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    # CHECK JOIN
    if query.data == "check_join":

        if await is_user_joined(user_id, context):
            await query.message.edit_text(
                "✅ Verified!\n\nNow use the bot.",
                reply_markup=main_menu()
            )
        else:
            await query.answer("❌ You haven't joined yet!", show_alert=True)

    elif query.data == "translate":
        context.user_data["step"] = "lang"
        await query.message.edit_text("🌐 Send language code (ml/en/hi/etc)")

    elif query.data == "account":
        await query.message.edit_text("👤 Free User Account")

    elif query.data == "help":
        await query.message.edit_text(
            "ℹ️ Steps:\n1. Select translate\n2. Send language code\n3. Upload .srt file"
        )


# ---------------- TEXT HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if context.user_data.get("step") == "lang":
        context.user_data["lang"] = update.message.text
        context.user_data["step"] = "file"

        await update.message.reply_text("✅ Language saved. Now send .srt file")
    else:
        await update.message.reply_text("Use /start")


# ---------------- FILE HANDLER ----------------
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if "lang" not in context.user_data:
        await update.message.reply_text("❌ First select language")
        return

    file = update.message.document

    if not file.file_name.endswith(".srt"):
        await update.message.reply_text("❌ Only .srt files allowed")
        return

    lang = context.user_data["lang"]

    input_file = f"{update.effective_user.id}.srt"
    output_file = f"translated_{update.effective_user.id}.srt"

    msg = await update.message.reply_text("⏳ Translating...")

    file_obj = await file.get_file()
    await file_obj.download_to_drive(input_file)

    try:
        subs = pysrt.open(input_file)
        translator = GoogleTranslator(source="auto", target=lang)

        for sub in subs:
            if sub.text.strip():
                try:
                    sub.text = translator.translate(sub.text)
                except:
                    pass

        subs.save(output_file, encoding="utf-8")

        await msg.edit_text("✅ Translation Done")

        await update.message.reply_document(
            document=open(output_file, "rb"),
            caption="🎉 Translated Subtitle"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

    finally:
        if os.path.exists(input_file):
            os.remove(input_file)
        if os.path.exists(output_file):
            os.remove(output_file)


# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()

