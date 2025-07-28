from telegram import Update
from telegram.ext import ContextTypes
from services.gemini_service import GeminiService

gemini_service = GeminiService()

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text
    response = await gemini_service.generate_text_response(user_id, text)
    await update.message.reply_text(response)

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    voice_file = await context.bot.get_file(update.message.voice.file_id)
    voice_data = await voice_file.download_as_bytearray()
    
    # In a real application, you would replace the line below with a call to a speech-to-text API.
    # For now, we'll just acknowledge receipt of the voice message and pass its caption.
    caption = update.message.caption or ""
    response = await gemini_service.generate_response_with_audio(user_id, caption, bytes(voice_data))
    await update.message.reply_text(response)

async def handle_image_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    photo_file = await context.bot.get_file(update.message.photo[-1].file_id)
    photo_data = await photo_file.download_as_bytearray()
    
    caption = update.message.caption or ""
    response = await gemini_service.generate_response_with_image(user_id, caption, bytes(photo_data))
    await update.message.reply_text(response)