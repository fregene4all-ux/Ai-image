import os
import asyncio
import logging
import tempfile
import requests
import replicate

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8968819657:AAEHb4SFyRfSlPlRvqhRu1sNr-vG6XoWNMw"
replicate.api_token = "r8_2XTLoJflR5MFndOH9M3dLGNdA1tlBds0PtG59"

VIDEO_KEYWORDS = ["video", "cinematic", "motion", "scene"]

IMAGE_MODEL = "stability-ai/sdxl"
VIDEO_MODEL = "luma/ray"
TRANSFORM_MODEL = "tencentarc/photomaker"

def enhance_image_prompt(prompt):
    return f"ultra realistic portrait of {prompt}, 8k DSLR photo, cinematic lighting, highly detailed face, professional photography"

def enhance_video_prompt(prompt):
    return f"cinematic video of {prompt}, realistic motion, film look, natural lighting, handheld camera, ultra realistic"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send a prompt or upload a photo.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text

    if not prompt:
        return

    is_video = any(k in prompt.lower() for k in VIDEO_KEYWORDS)

    await update.message.reply_text("Generating...")

    try:
        final_prompt = enhance_video_prompt(prompt) if is_video else enhance_image_prompt(prompt)
        model = VIDEO_MODEL if is_video else IMAGE_MODEL

        output = await asyncio.to_thread(
            replicate.run,
            model,
            {"prompt": final_prompt}
        )

        if isinstance(output, list):
            output = output[0]

        if not output:
            await update.message.reply_text("No output returned from model.")
            return

        if is_video:
            await update.message.reply_video(video=output)
        else:
            await update.message.reply_photo(photo=output)

    except Exception as e:
        logger.error(e)
        await update.message.reply_text(f"Error: {str(e)}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    caption = update.message.caption or "improve this portrait, ultra realistic, cinematic lighting"

    await update.message.reply_text("Transforming image...")

    file_path = None

    try:
        file = await context.bot.get_file(photo.file_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            file_path = tmp.name
            await file.download_to_drive(file_path)

        upload = requests.post(
            "https://tmpfiles.org/api/v1/upload",
            files={"file": open(file_path, "rb")}
        ).json()

        image_url = upload["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")

        output = await asyncio.to_thread(
            replicate.run,
            TRANSFORM_MODEL,
            {
                "prompt": caption,
                "input_image": image_url
            }
        )

        if isinstance(output, list):
            output = output[0]

        if not output:
            await update.message.reply_text("No output returned.")
            return

        await update.message.reply_photo(photo=output)

    except Exception as e:
        logger.error(e)
        await update.message.reply_text(f"Error: {str(e)}")

    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.run_polling()

if __name__ == "__main__":
    main()
