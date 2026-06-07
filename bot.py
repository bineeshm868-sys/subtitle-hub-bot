import os
import pysrt
import asyncio
from deep_translator import GoogleTranslator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1002047353995  
CHANNEL_URL = "https://t.me/subtitlehubofficial"

LANG_DATA = {
    'india': {'ml': 'Malayalam 🇮🇳', 'hi': 'Hindi 🇮🇳', 'ta': 'Tamil 🇮🇳', 'te': 'Telugu 🇮🇳'},
    'europe': {'en': 'English 🇬🇧', 'es': 'Spanish 🇪🇸', 'fr': 'French 🇫🇷'}
}

async def is_user_joined(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_joined(user_id, context):
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Channel", url=CHANNEL_URL)]])
        await update.message.reply_text("Access restricted. Please join our channel first:", reply_markup=btn)
        return
    
    keyboard = [
        [InlineKeyboardButton("🇮🇳 India", callback_data='country_india'), 
         InlineKeyboardButton("🇪🇺 Europe", callback_data='country_europe')]
    ]
    await update.message.reply_text("Welcome! Please select your region:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('country_'):
        region = query.data.split('_')[1]
        btns = [[InlineKeyboardButton(name, callback_data=f"lang_{code}")] for code, name in LANG_DATA[region].items()]
        await query.message.edit_text(f"Region: {region.upper()}. Select target language:", reply_markup=InlineKeyboardMarkup(btns))
    
    elif query.data.startswith('lang_'):
        lang_code = query.data.split('_')[1]
        context.user_data['target_lang'] = lang_code
        await query.message.edit_text(f"Language configured successfully! Please upload your .srt file.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'target_lang' not in context.user_data:
        await update.message.reply_text("Please select a language first using /start")
        return

    lang = context.user_data['target_lang']
    file = await update.message.document.get_file()
    input_filename = f"{update.effective_user.id}_input.srt"
    output_filename = "translated.srt"
    
    await file.download_to_drive(input_filename)
    
    try:
        subs = pysrt.open(input_filename)
        translator = GoogleTranslator(source='auto', target=lang)
        for sub in subs:
            if sub.text.strip():
                sub.text = translator.translate(sub.text)
        
        subs.save(output_filename, encoding='utf-8')
        await update.message.reply_document(document=open(output_filename, "rb"), caption="Translation complete.")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")
    finally:
        if os.path.exists(input_filename): os.remove(input_filename)
        if os.path.exists(output_filename): os.remove(output_filename)

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("Bot service initialized and running...")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())



