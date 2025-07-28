from telegram import Update
from telegram.ext import ContextTypes
from services.gemini_service import GeminiService

gemini_service = GeminiService()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот, который использует Gemini API для ответа на ваши сообщения. "
        "Отправьте мне текст, голосовое сообщение или изображение. "
        "Используйте /new для начала нового диалога."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/start - Начать диалог\n"
        "/help - Показать это сообщение\n"
        "/new - Начать новый диалог (сбросить контекст)\n\n"
        "Вы можете отправлять мне текстовые сообщения, голосовые сообщения и изображения. "
        "Я постараюсь ответить на них с помощью Gemini. "
        "Обратите внимание, что для голосовых сообщений требуется дополнительная настройка Speech-to-Text сервиса."
    )

async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    gemini_service.reset_chat_session(user_id)
    await update.message.reply_text("Начат новый диалог. Предыдущий контекст сброшен.")