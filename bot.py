import os
import json
import pysrt
import re
import requests
import http.server
import socketserver
import threading
import asyncio
from deep_translator import GoogleTranslator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
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
OMDB_API_KEY = os.getenv("OMDB_API_KEY", "YOUR_OMDB_KEY_HERE")

# --- FORCE JOIN CONFIGURATION ---
CHANNEL_USERNAME = "@Msone_Official"  
CHANNEL_URL = "https://t.me/Msone_Official" 

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

async def is_user_joined(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
    except Exception as e:
        print(f"Force Join Check Error: {e}")
    return False

USER_PENDING_MOVIES = {}

# Eppozhum screen thazhe visible aayi nilkkunna Menu Button layout
def get_permanent_start_keyboard():
    keyboard = [[KeyboardButton("🏠 Menu / Start")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, persistent=True)

async def send_force_join_msg(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    keyboard = [
        [InlineKeyboardButton("📢 Join Updates Channel 📢", url=CHANNEL_URL)],
        [InlineKeyboardButton("🔄 Try Again 🔄", callback_data="check_join")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = "❌ *Access Denied!*\n\nPlease join our update channel first to unlock all features of this Subtitle Bot."
    
    if is_callback:
        await update.callback_query.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

def clean_movie_name(filename):
    name = filename.lower().replace('.srt', '')
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'720p|1080p|2160p|bluray|web-dl|webrip|hdrip|x264|x265|h264|h265|dvdrip', '', name)
    name = re.sub(r'yts|rarbg|psa|galaxyrg|etrg', '', name)
    name = name.replace('.', ' ').replace('_', ' ').replace('-', ' ')
    name = re.sub(r'\b(19|20)\d{2}\b', '', name)
    return name.strip()

def get_movie_details(movie_name):
    url = f"http://www.omdbapi.com/?t={movie_name}&apikey={OMDB_API_KEY}"
    try:
        response = requests.get(url).json()
        if response.get("Response") == "True":
            return response
    except:
        pass
    return None

LANG_MAPPING = {
    'ml': 'Malayalam 🇮🇳', 'hi': 'Hindi 🇮🇳', 'ta': 'Tamil 🇮🇳', 
    'te': 'Telugu 🇮🇳', 'kn': 'Kannada 🇮🇳', 'en': 'English 🇬🇧',
    'es': 'Spanish 🇪🇸', 'fr': 'French 🇫🇷', 'ar': 'Arabic 🇦🇪'
}

def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("India 🇮🇳", callback_data='country_india'), InlineKeyboardButton("Europe 🇪🇺", callback_data='country_europe')],
        [InlineKeyboardButton("Middle East 🇦🇪", callback_data='country_me'), InlineKeyboardButton("Other Countries 🌍", callback_data='country_other')]
    ]
    return InlineKeyboardMarkup(keyboard)

# 4 Main Details + Poster fetch cheyyunna code block
async def send_movie_presentation(chat_id: int, user_id: int, movie_param: str, context: ContextTypes.DEFAULT_TYPE):
    langs = load_langs()
    target_lang = langs.get(str(user_id), 'ml')
    
    movie_info = get_movie_details(clean_movie_name(movie_param))
    requested_lang = LANG_MAPPING.get(target_lang, target_lang.title())
    
    reply_keyboard = get_permanent_start_keyboard()

    if movie_info and movie_info.get("Poster") and movie_info.get("Poster") != "N/A":
        info_msg = (
            f"🎬 *Movie:* {movie_info.get('Title')} ({movie_info.get('Year')})\n"
            f"🎥 *Director:* {movie_info.get('Director')}\n"
            f"🌐 *Official Language:* {movie_info.get('Language')}\n"
            f"🔄 *Requested Translation:* {requested_lang}\n\n"
            f"📥 *Please upload your matching base .srt file below:* 👇"
        )
        await context.bot.send_photo(chat_id=chat_id, photo=movie_info.get("Poster"), caption=info_msg, parse_mode="Markdown", reply_markup=reply_keyboard)
    else:
        info_msg = (
            f"🎬 *Movie Name:* {movie_param.title()}\n"
            f"🔄 *Requested Translation:* {requested_lang}\n\n"
            f"📥 *Please upload your matching base .srt file below:* 👇"
        )
        await context.bot.send_message(chat_id=chat_id, text=info_msg, parse_mode="Markdown", reply_markup=reply_keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    movie_param = None
    if context.args:
        movie_param = " ".join(context.args).replace("_", " ")
        USER_PENDING_MOVIES[user_id] = movie_param

    if not await is_user_joined(user_id, context):
        await send_force_join_msg(update, context)
        return

    if movie_param:
        await update.message.reply_text(f"🎬 *Target Found:* Processing `{movie_param}`...", parse_mode="Markdown", reply_markup=get_permanent_start_keyboard())
        await send_movie_presentation(update.effective_chat.id, user_id, movie_param, context)
        if user_id in USER_PENDING_MOVIES:
            del USER_PENDING_MOVIES[user_id]
        return

    msg = "🎬 *Subtitle Translation Bot*\n\nPlease select your *Country / Region* first:\n"
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if query.data == "check_join":
        if await is_user_joined(user_id, context):
            await query.message.delete()
            
            pending_movie = USER_PENDING_MOVIES.get(user_id)
            if pending_movie:
                await query.message.reply_text("✅ *Verification Successful!*\n\nFetching your requested movie details...", parse_mode="Markdown", reply_markup=get_permanent_start_keyboard())
                await send_movie_presentation(update.effective_chat.id, user_id, pending_movie, context)
                del USER_PENDING_MOVIES[user_id]
            else:
                await query.message.reply_text("✅ *Verification Successful!*\n\nPlease select your Country:", parse_mode="Markdown", reply_markup=get_main_menu_keyboard())
        else:
            await query.answer("❌ You haven't joined the channel yet! Please join and try again.", show_alert=True)
        return
    
    if not await is_user_joined(user_id, context):
        await send_force_join_msg(update, context, is_callback=True)
        return

    if query.data == "back_to_main":
        msg = "🎬 *Subtitle Translation Bot*\n\nPlease select your *Country / Region*:\n"
        await query.message.edit_text(msg, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())
        return

    if query.data.startswith('country_'):
        country = query.data.split('_')[1]
        back_btn = [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]
        
        if country == 'india':
            keyboard = [
                [InlineKeyboardButton("Malayalam 🇮🇳", callback_data='lang_ml'), InlineKeyboardButton("Tamil 🇮🇳", callback_data='lang_ta')],
                [InlineKeyboardButton("Hindi 🇮🇳", callback_data='lang_hi'), InlineKeyboardButton("Telugu 🇮🇳", callback_data='lang_te')],
                [InlineKeyboardButton("Kannada 🇮🇳", callback_data='lang_kn'), InlineKeyboardButton("English 🇬🇧", callback_data='lang_en')],
                back_btn
            ]
            msg = "🇮🇳 *India* selected. Choose your language target:"
        elif country == 'europe':
            keyboard = [
                [InlineKeyboardButton("English 🇬🇧", callback_data='lang_en'), InlineKeyboardButton("Spanish 🇪🇸", callback_data='lang_es')],
                [InlineKeyboardButton("French 🇫🇷", callback_data='lang_fr'), InlineKeyboardButton("German 🇩🇪", callback_data='lang_de')],
                back_btn
            ]
            msg = "🇪🇺 *Europe* selected. Choose your language target:"
        elif country == 'me':
            keyboard = [
                [InlineKeyboardButton("Arabic 🇦🇪", callback_data='lang_ar'), InlineKeyboardButton("English 🇬🇧", callback_data='lang_en')],
                back_btn
            ]
            msg = "🇦🇪 *Middle East* selected. Choose your language target:"
        else:
            keyboard = [[InlineKeyboardButton("English 🇬🇧", callback_data='lang_en')], back_btn]
            msg = "🌍 Enter any global language name directly via message text input anytime."

        await query.message.edit_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith('lang_'):
        lang = query.data.split('_')[1]
        langs = load_langs()
        langs[str(user_id)] = lang
        save_langs(langs)
        
        await query.message.reply_text(
            f"✅ Preference set to: *{LANG_MAPPING.get(lang, lang.upper())}*\n\nSend your base .srt file.",
            reply_markup=get_permanent_start_keyboard()
        )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_joined(user_id, context):
        await send_force_join_msg(update, context)
        return

    user_text = update.message.text.strip()
    
    # Permanent layout click tracker routing block
    if user_text in ["🏠 Menu / Start", "/start"]:
        msg = "🎬 *Subtitle Translation Bot*\n\nPlease select your *Country / Region* first:\n"
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())
        return

    await update.message.reply_text(f"🔍 Checking availability for: *{user_text}*...", parse_mode="Markdown")
    try:
        GoogleTranslator(source='auto', target=user_text.lower())
        langs = load_langs()
        langs[str(user_id)] = user_text.lower()
        save_langs(langs)
        
        await update.message.reply_text(f"✅ Target dynamically set to: *{user_text.title()}*\n\nSend your file.", parse_mode="Markdown", reply_markup=get_permanent_start_keyboard())
    except:
        await update.message.reply_text("❌ Language unmapped. Try standard formats like `Spanish` or `Telugu`.")

async def translate_subtitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_joined(user_id, context):
        await send_force_join_msg(update, context)
        return

    document = update.message.document
    if not document.file_name.lower().endswith('.srt'):
        await update.message.reply_text("❌ Extension error. Drop clean .srt documents.")
        return

    langs = load_langs()
    target_lang = langs.get(str(user_id), 'ml')
    await update.message.reply_text(f"⏳ Compiling translation layer for *{target_lang.upper()}*...", parse_mode="Markdown")

    cleaned_name = clean_movie_name(document.file_name)
    movie_info = get_movie_details(cleaned_name)
    requested_lang = LANG_MAPPING.get(target_lang, target_lang.title())

    if movie_info:
        info_msg = (
            f"🎬 *Movie:* {movie_info.get('Title')} ({movie_info.get('Year')})\n"
            f"🎥 *Director:* {movie_info.get('Director')}\n"
            f"🌐 *Official Language:* {movie_info.get('Language')}\n"
            f"🔄 *Translated Language:* {requested_lang}\n\n"
            f"📥 *Direct Download (DD) File Below:* 👇"
        )
    else:
        info_msg = (
            f"🎬 *Movie Name:* {document.file_name}\n"
            f"🔄 *Translated Language:* {requested_lang}\n\n"
            f"📥 *Direct Download (DD) File Below:* 👇"
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
            await update.message.reply_text(f"❌ Read execution failure: {e}")
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

    if movie_info and movie_info.get("Poster") and movie_info.get("Poster") != "N/A":
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=movie_info.get("Poster"), caption=info_msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(info_msg, parse_mode="Markdown")

    # FIX: Using 'with open()' scope structure blocks file leaks and protects Render framework from crashing early
    with open(output_file, 'rb') as f:
        await update.message.reply_document(
            document=f, 
            filename=f"[DD]_{document.file_name}", 
            reply_markup=get_permanent_start_keyboard()
        )

    if os.path.exists(input_file): os.remove(input_file)
    if os.path.exists(output_file): os.remove(output_file)

async def main():
    if not BOT_TOKEN:
        print("❌ Error: BOT_TOKEN Environment Variable missing!")
        return

    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    application.add_handler(MessageHandler(filters.Document.ALL, translate_subtitle))
    
    print("⚡ Bot starting safely layout workflow...")
    await application.initialize()
    await application.start()
    if application.updater:
        await application.updater.start_polling()
    
    await asyncio.Event().wait()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
