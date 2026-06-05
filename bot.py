import os
import json
import pysrt
import http.server
import socketserver
import threading
from deep_translator import GoogleTranslator
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==========================================
# RENDER PORT ERROR FIX (DUMMY SERVER)
# ==========================================
def start_dummy_server():
    PORT = 10000
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()

# Start the dummy server in the background to prevent Render port errors
threading.Thread(target=start_dummy_server, daemon=True).start()
# ==========================================

# Retrieve bot token from Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
LANG_FILE = "user_langs.json"

# Initialize language storage file if it doesn't exist
if not os.path.exists(LANG_FILE):
    with open(LANG_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)

def load_langs():
    with open(LANG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_langs(data):
    with open(LANG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🎬 *Subtitle Translation Bot*\n\n"
        "1. Select language:\n"
        "`/lang ml` (Malayalam)\n"
        "`/lang hi` (Hindi)\n"
        "`/lang ta` (Tamil)\n\n"
        "2. Upload .srt subtitle file\n"
        "3. Get translated subtitle\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage:\n/lang ml\n/lang hi\n/lang ta"
        )
        return

    lang = context.args[0]
    langs = load_langs()
    langs[str(update.effective_user.id)] = lang
    save_langs(langs)

    await update.message.reply_text(
        f"✅ Translation language set to: *{lang.upper()}*",
        parse_mode="Markdown"
    )

async def translate_subtitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if not document.file_name.lower().endswith('.srt'):
        await update.message.reply_text("❌ Please upload a valid .srt file.")
        return

    user_id = str(update.effective_user.id)
    langs = load_langs()
    target_lang = langs.get(user_id, 'ml') # Default to Malayalam if not set

    await update.message.reply_text(f"🌍 Translating to *{target_lang.upper()}*... Please wait.", parse_mode="Markdown")

    tg_file = await context.bot.get_file(document.file_id)
    input_file = f"{user_id}_input.srt"
    output_file = f"{user_id}_translated.srt"

    await tg_file.download_to_drive(input_file)

    try:
        subs = pysrt.open(input_file, encoding='utf-8')
    except:
        try:
            subs = pysrt.open(input_file, encoding='iso-8859-1')
        except Exception as e:
            await update.message.reply_text(f"❌ Error reading SRT file: {e}")
            if os.path.exists(input_file): os.remove(input_file)
            return

    translator = GoogleTranslator(source='auto', target=target_lang)

    # Translates the subtitle line by line
    for sub in subs:
        if sub.text.strip():
            try:
                sub.text = translator.translate(sub.text)
            except:
                pass

    subs.save(output_file, encoding='utf-8')

    with open(output_file, 'rb') as f:
        await update.message.reply_document(
            document=f,
            filename=f"[Translated]_{document.file_name}"
        )

    # Clean up temporary files
    if os.path.exists(input_file): os.remove(input_file)
    if os.path.exists(output_file): os.remove(output_file)

if __name__ == '__main__':
    if not BOT_TOKEN:
        print("❌ Error: BOT_TOKEN Environment Variable not found!")
        exit(1)

    import asyncio

    # Build the application
    application = Application.builder().token(BOT_TOKEN).build()

    # Link commands and messages to handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("lang", set_language))
    application.add_handler(MessageHandler(filters.Document.ALL, translate_subtitle))

    print("⚡ Bot is starting...")
    
    # Explicitly handle the event loop creation to fix the RuntimeError
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(application.initialize())
    loop.run_until_complete(application.start())
    if application.updater:
        loop.run_until_complete(application.updater.start_polling())
    
    print("✨ Bot is live and polling!")
    loop.run_forever()



