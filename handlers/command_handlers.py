from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import json
from config.constants import States, Buttons, ButtonText
from utils.keyboard_utils import get_main_menu_keyboard, get_back_button_keyboard

# Helper function to set user state
def set_user_state(context: ContextTypes.DEFAULT_TYPE, state: int) -> None:
    context.user_data['state'] = state

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    gemini_service = context.bot_data['gemini_service']
    set_user_state(context, States.MAIN_MENU)
    reply_text = "Выберите действие:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(reply_text, reply_markup=get_main_menu_keyboard())
    else:
        await update.message.reply_text(reply_text, reply_markup=get_main_menu_keyboard())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await main_menu(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Я бот, который использует Gemini API для ответа на ваши сообщения.\n"
        "Используйте кнопки ниже для выбора действия или команду /new для начала нового диалога.\n\n"
        "Для получения подробной информации о каждой функции, выберите ее в меню."
    )
    await update.message.reply_text(help_text, reply_markup=get_main_menu_keyboard())

async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    gemini_service = context.bot_data['gemini_service']
    user_id = update.effective_user.id
    gemini_service.reset_chat_session(user_id)
    set_user_state(context, States.MAIN_MENU) # Reset state to main menu
    await update.message.reply_text("Начат новый диалог. Предыдущий контекст сброшен.", reply_markup=get_main_menu_keyboard())

# Callback handler for main menu buttons
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    gemini_service = context.bot_data['gemini_service']
    query = update.callback_query
    await query.answer() # Acknowledge the callback query

    user_id = query.from_user.id
    data = query.data

    if data == Buttons.BACK_TO_MAIN_MENU:
        await main_menu(update, context)
        return

    if data == Buttons.TEXT_GENERATION:
        set_user_state(context, States.WAITING_FOR_TEXT)
        await query.edit_message_text("Отправьте мне текстовое сообщение, и я отвечу.", reply_markup=get_back_button_keyboard())
    elif data == Buttons.IMAGE_UNDERSTANDING:
        set_user_state(context, States.WAITING_FOR_IMAGE)
        await query.edit_message_text("Отправьте мне изображение (с подписью или без), и я проанализирую его.", reply_markup=get_back_button_keyboard())
    elif data == Buttons.VOICE_PROCESSING:
        set_user_state(context, States.WAITING_FOR_VOICE)
        await query.edit_message_text("Отправьте мне голосовое сообщение (с подписью или без). Я обработаю подпись.", reply_markup=get_back_button_keyboard())
    elif data == Buttons.STRUCTURED_OUTPUT:
        set_user_state(context, States.WAITING_FOR_STRUCTURED_PROMPT)
        await query.edit_message_text("Отправьте мне промпт и JSON-схему в формате: `prompt`\n`{\"key\": \"value\"}`", reply_markup=get_back_button_keyboard())
    elif data == Buttons.EXECUTE_CODE:
        set_user_state(context, States.WAITING_FOR_CODE)
        await query.edit_message_text("Отправьте мне Python код для выполнения.", reply_markup=get_back_button_keyboard())
    elif data == Buttons.ANALYZE_URL:
        set_user_state(context, States.WAITING_FOR_URL)
        await query.edit_message_text("Отправьте мне URL для анализа (с необязательным промптом). Формат: `URL`\n`[prompt]`", reply_markup=get_back_button_keyboard())
    elif data == Buttons.GOOGLE_SEARCH:
        set_user_state(context, States.WAITING_FOR_SEARCH_QUERY)
        await query.edit_message_text("Отправьте мне поисковый запрос (с необязательным промптом). Формат: `запрос`\n`[prompt]`", reply_markup=get_back_button_keyboard())