import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from config.settings import TELEGRAM_BOT_TOKEN, GEMINI_API_KEY
from services.gemini_service import GeminiService
from handlers.command_handlers import (
    start,
    help_command,
    new_chat,
    button_callback_handler,
    main_menu
)
from handlers.message_handlers import (
    handle_all_messages,
    handle_voice_message,
    handle_image_message,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Start the bot."""
    # Initialize GeminiService
    gemini_service = GeminiService()

    application_builder = Application.builder().token(TELEGRAM_BOT_TOKEN)

    application = application_builder.build()

    # Store gemini_service in bot_data so handlers can access it
    application.bot_data['gemini_service'] = gemini_service

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("new", new_chat))

    # Callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
