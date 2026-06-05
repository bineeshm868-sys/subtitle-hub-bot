import os
import json
import pysrt

from deep_translator import GoogleTranslator
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "8706812094:AAF_uHALk9yYIWnO1pb6gGrznO3dKT6P3Ew"

LANG_FILE = "user_langs.json"

# Create language storage file if not exists
if not os.path.exists(LANG_FILE):
    with open(LANG_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)


def load_langs():
    with open(LANG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_langs(data):
    with open(LANG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🎬 Subtitle Translation Bot\n\n"
        "1. Select language:\n"
        "/lang ml\n"
        "/lang hi\n"
        "/lang ta\n"
        "/lang fr\n\n"
        "2. Upload .srt subtitle file\n"
        "3. Get translated subtitle\n"
    )
    await update.message.reply_text(msg)


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage:\n/lang ml\n/lang hi\n/lang fr"
        )
        return

    lang = context.args[0]

    langs = load_langs()
    langs[str(update.effective_user.id)] = lang
    save_langs(langs)

    await update.message.reply_text(
        f"✅ Translation language set to: {lang}"
    )


async def translate_subtitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if not document.file_name.lower().endswith(".srt"):
        await update.message.reply_text("❌ Please send an .srt file.")
        return

    user_id = str(update.effective_user.id)

    langs = load_langs()
    target_lang = langs.get(user_id, "en")

    await update.message.reply_text(
        f"🌍 Translating to {target_lang}...\nPlease wait."
    )

    tg_file = await context.bot.get_file(document.file_id)

    input_file = f"{user_id}_input.srt"
    output_file = f"{user_id}_translated.srt"

    await tg_file.download_to_drive(input_file)

    try:
        subs = pysrt.open(input_file, encoding="utf-8")

        translator = GoogleTranslator(
            source="auto",
            target=target_lang
        )

        total = len(subs)

        for index, sub in enumerate(subs):
            text = sub.text.replace("\n", " ")

            if text.strip():
                try:
                    translated = translator.translate(text)
                    sub.text = translated
                except Exception:
                    pass

            if index % 100 == 0:
                print(f"{index}/{total}")

        subs.save(output_file, encoding="utf-8")

        with open(output_file, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=f"translated_{document.file_name}"
            )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error:\n{str(e)}"
        )

    finally:
        if os.path.exists(input_file):
            os.remove(input_file)

        if os.path.exists(output_file):
            os.remove(output_file)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lang", set_language))

    app.add_handler(
        MessageHandler(
            filters.Document.ALL,
            translate_subtitle
        )
    )

    print("Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
