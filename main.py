import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from config.settings import TELEGRAM_BOT_TOKEN
from handlers.command_handlers import (
    start,
    help_command,
    new_chat,
    button_callback_handler, # New: for handling button presses
    main_menu # New: for returning to main menu
)
from handlers.message_handlers import (
    handle_all_messages, # New: handles all text messages based on state
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
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("new", new_chat))
    # No longer need specific command handlers for structured_output, execute_code, analyze_url, search
    # as they are now handled via buttons and handle_all_messages

    # Callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    # Message handlers
    # handle_all_messages will now manage text input based on user state
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()