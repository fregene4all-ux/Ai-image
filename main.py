import os
import asyncio
import base64
import io
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from openai import AsyncOpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = "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"
RUNWAY_API_KEY = "key_ed9bbf5785302611db8f938d4e3bfe705651d1b1c131299a5a3ed8a0d29316c141c359f49889931b2a0f7e681f4146d63151057491e8ddfa259f9d03a17ff067"

client = AsyncOpenAI(api_key=OPENAI_API_KEY)
user_history = defaultdict(list)

IMAGE_PROMPT_TEMPLATE = "cinematic DSLR style, ultra-realistic face detail, dramatic lighting, shallow depth of field, 8k resolution, professional photography: {}"
VIDEO_PROMPT_TEMPLATE = "cinematic motion, film look, natural camera movement, realistic lighting, professional cinematography: {}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Image Mode", callback_data="mode_image"),
         InlineKeyboardButton("Video Mode", callback_data="mode_video")],
        [InlineKeyboardButton("History", callback_data="history"),
         InlineKeyboardButton("Reset", callback_data="reset")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select mode:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "mode_image":
        context.user_data["mode"] = "image"
        await query.edit_message_text("Image mode active. Send a prompt.")
    elif query.data == "mode_video":
        context.user_data["mode"] = "video"
        await query.edit_message_text("Video mode active. Send a prompt.")
    elif query.data == "history":
        history = user_history.get(user_id, [])
        if not history:
            await query.edit_message_text("No history.")
        else:
            text = "Last prompts:\n" + "\n".join([f"{i+1}. {h}" for i, h in enumerate(history[-5:])])
            await query.edit_message_text(text)
    elif query.data == "reset":
        user_history[user_id] = []
        context.user_data["mode"] = None
        await query.edit_message_text("History cleared. Select mode:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Image Mode", callback_data="mode_image"),
             InlineKeyboardButton("Video Mode", callback_data="mode_video")]
        ]))

async def generate_images(prompt: str):
    enhanced = IMAGE_PROMPT_TEMPLATE.format(prompt)
    response = await client.images.generate(
        model="gpt-image-1",
        prompt=enhanced,
        n=3,
        size="1024x1024",
        response_format="b64_json"
    )
    images = []
    for img in response.data:
        decoded = base64.b64decode(img.b64_json)
        images.append(io.BytesIO(decoded))
    return images

async def generate_video(prompt: str):
    return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    mode = context.user_data.get("mode", "image")
    user_history[user_id].append(text)
    if len(user_history[user_id]) > 50:
        user_history[user_id] = user_history[user_id][-50:]
    progress = await update.message.reply_text("Starting...")
    try:
        if mode == "image":
            await progress.edit_text("Enhancing prompt...")
            await asyncio.sleep(0.5)
            await progress.edit_text("Generating...")
            images = await generate_images(text)
            await progress.edit_text("Sending results...")
            media = [InputMediaPhoto(img) for img in images]
            await update.message.reply_media_group(media=media)
            await progress.delete()
        elif mode == "video":
            await progress.edit_text("Enhancing prompt...")
            await asyncio.sleep(0.5)
            await progress.edit_text("Generating video...")
            result = await generate_video(text)
            await progress.edit_text("Video generation is currently unavailable.")
    except Exception as e:
        await progress.edit_text("Error occurred. Please try again.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update and update.message:
        await update.message.reply_text("An error occurred.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
