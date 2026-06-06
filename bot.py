import os
import json
import pysrt
import re
import requests
import http.server
import socketserver
import threading
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

# ==========================================
# RENDER PORT ERROR FIX (DUMMY SERVER)
# ==========================================
def start_dummy_server():
    PORT = 10000
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=start_dummy_server, daemon=True).start()
# ==========================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OMDB_API_KEY = os.getenv("OMDB_API_KEY", "YOUR_OMDB_KEY_HERE") # Place your OMDb API Key here
LANG_FILE = "user_langs.json"

if not os.path.exists(LANG_FILE):
    with open(LANG_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)

def load_langs():
    with open(LANG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_langs(data):
    with open(LANG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Function to clean the filename to extract the movie name
def clean_movie_name(filename):
    name = filename.lower().replace('.srt', '')
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'720p|1080p|2160p|bluray|web-dl|webrip|hdrip|x264|x265|h264|h265|dvdrip', '', name)
    name = re.sub(r'yts|rarbg|psa|galaxyrg|etrg', '', name)
    name = name.replace('.', ' ').replace('_', ' ').replace('-', ' ')
    name = re.sub(r'\b(19|20)\d{2}\b', '', name)
    return name.strip()

# Fetch movie details from OMDb API
def get_movie_details(movie_name):
    url = f"http://www.omdbapi.com/?t={movie_name}&apikey={OMDB_API_KEY}"
    try:
        response = requests.get(url).json()
        if response.get("Response") == "True":
            return response
    except:
        pass
    return None

# Map language codes to beautiful display names (Fixed Malayalam Flag)
LANG_MAPPING = {
    'ml': 'Malayalam 🇮🇳', 'hi': 'Hindi 🇮🇳', 'ta': 'Tamil 🇮🇳', 
    'te': 'Telugu 🇮🇳', 'kn': 'Kannada 🇮🇳', 'en': 'English 🇬🇧',
    'es': 'Spanish 🇪🇸', 'fr': 'French 🇫🇷', 'ar': 'Arabic 🇦🇪'
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ask the user to select their country/region first
    keyboard = [
        [
            InlineKeyboardButton("India 🇮🇳", callback_data='country_india'),
            InlineKeyboardButton("Europe 🇪🇺", callback_data='country_europe'),
        ],
        [
            InlineKeyboardButton("Middle East 🇦🇪", callback_data='country_me'),
            InlineKeyboardButton("Other Countries 🌍", callback_data='country_other')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = (
        "🎬 *Subtitle Translation Bot*\n\n"
        "Welcome! Please select your *Country / Region* first:\n"
    )
    
    if update.message:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # When user selects a Country
    if query.data.startswith('country_'):
        country = query.data.split('_')[1]
        
        if country == 'india':
            keyboard = [
                [InlineKeyboardButton("Malayalam 🇮🇳", callback_data='lang_ml'), InlineKeyboardButton("Tamil 🇮🇳", callback_data='lang_ta')],
                [InlineKeyboardButton("Hindi 🇮🇳", callback_data='lang_hi'), InlineKeyboardButton("Telugu 🇮🇳", callback_data='lang_te')],
                [InlineKeyboardButton("Kannada 🇮🇳", callback_data='lang_kn'), InlineKeyboardButton("English 🇬🇧", callback_data='lang_en')]
            ]
            msg = "🇮🇳 *India* selected. Please choose your target language:"
            
        elif country == 'europe':
            keyboard = [
                [InlineKeyboardButton("English 🇬🇧", callback_data='lang_en'), InlineKeyboardButton("Spanish 🇪🇸", callback_data='lang_es')],
                [InlineKeyboardButton("French 🇫🇷", callback_data='lang_fr'), InlineKeyboardButton("German 🇩🇪", callback_data='lang_de')]
            ]
            msg = "🇪🇺 *Europe* selected. Please choose your target language:"
            
        elif country == 'me':
            keyboard = [
                [InlineKeyboardButton("Arabic 🇦🇪", callback_data='lang_ar'), InlineKeyboardButton("English 🇬🇧", callback_data='lang_en')]
            ]
            msg = "🇦🇪 *Middle East* selected. Please choose your target language:"
            
        else:
            keyboard = [
                [InlineKeyboardButton("English 🇬🇧", callback_data='lang_en')]
            ]
            msg = "🌍 Please choose a language or just type and send any language name directly to me!"

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

    # When user selects a Language
    elif query.data.startswith('lang_'):
        lang = query.data.split('_')[1]
        langs = load_langs()
        langs[str(update.effective_user.id)] = lang
        save_langs(langs)
        
        chosen_lang_name = LANG_MAPPING.get(lang, lang.upper())
        await query.message.reply_text(
            f"✅ Translation language set to: *{chosen_lang_name}*\n\n"
            "Now, please upload your `.srt` subtitle file.",
            parse_mode="Markdown"
        )

# Handle text input if user manually types a language name
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    user_id = str(update.effective_user.id)
    
    await update.message.reply_text(f"🔍 Checking language: *{user_text}*...", parse_mode="Markdown")
    
    try:
        translator = GoogleTranslator(source='auto', target=user_text.lower())
        langs = load_langs()
        langs[user_id] = user_text.lower()
        save_langs(langs)
        
        await update.message.reply_text(
            f"✅ Translation language successfully set to: *{user_text.title()}*\n\n"
            "Now, please upload your `.srt` subtitle file.",
            parse_mode="Markdown"
        )
    except:
        await update.message.reply_text(
            "❌ Invalid Language! Please type a correct language name (e.g., `Spanish`, `Telugu`, `Arabic`)."
        )

async def translate_subtitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if not document.file_name.lower().endswith('.srt'):
        await update.message.reply_text("❌ Please upload a valid .srt file.")
        return

    user_id = str(update.effective_user.id)
    langs = load_langs()
    target_lang = langs.get(user_id, 'ml')

    await update.message.reply_text(f"🌍 Translating to *{target_lang.upper()}*... Please wait.", parse_mode="Markdown")

    cleaned_name = clean_movie_name(document.file_name)
    movie_info = get_movie_details(cleaned_name)

    requested_lang = LANG_MAPPING.get(target_lang, target_lang.title())

    if movie_info:
        title = movie_info.get("Title", "N/A")
        year = movie_info.get("Year", "N/A")
        official_lang = movie_info.get("Language", "N/A")
        director = movie_info.get("Director", "N/A")

        info_msg = (
            f"🎬 *Movie Name:* {title}\n"
            f"🎥 *Director:* {director}\n"
            f"📅 *Year:* {year}\n"
            f"🌐 *Official Language:* {official_lang}\n"
            f"🔄 *Translated Language:* {requested_lang}\n\n"
            f"📥 *Direct Download (DD) Link is ready below:* 👇"
        )
    else:
        info_msg = (
            f"🎬 *Movie Name:* {document.file_name}\n"
            f"🔄 *Translated Language:* {requested_lang}\n\n"
            f"📥 *Direct Download (DD) Link is ready below:* 👇"
        )

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

    for sub in subs:
        if sub.text.strip():
            try:
                sub.text = translator.translate(sub.text)
            except:
                pass

    subs.save(output_file, encoding='utf-8')

    await update.message.reply_text(info_msg, parse_mode="Markdown")

    # Delivers the file right inside the chat (Direct Download style)
    with open(output_file, 'rb') as f:
        await update.message.reply_document(
            document=f,
            filename=f"[DD]_{document.file_name}"
        )

    if os.path.exists(input_file): os.remove(input_file)
    if os.path.exists(output_file): os.remove(output_file)

if __name__ == '__main__':
    if not BOT_TOKEN:
        print("❌ Error: BOT_TOKEN Environment Variable not found!")
        exit(1)

    import asyncio

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    application.add_handler(MessageHandler(filters.Document.ALL, translate_subtitle))

    print("⚡ Bot is starting...")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(application.initialize())
    loop.run_until_complete(application.start())
    if application.updater:
        loop.run_until_complete(application.updater.start_polling())
    
    print("✨ Bot is live with Country-wise Language & DD features!")
    loop.run_forever()




