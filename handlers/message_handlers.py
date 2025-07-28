from telegram import Update
from telegram.ext import ContextTypes
from services.gemini_service import GeminiService
from config.constants import States, Buttons
from utils.keyboard_utils import get_main_menu_keyboard, get_back_button_keyboard
import json

gemini_service = GeminiService()

# Helper function to set user state (redefined here for clarity, can be moved to a common util if needed)
def set_user_state(context: ContextTypes.DEFAULT_TYPE, state: int) -> None:
    context.user_data['state'] = state

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    current_state = context.user_data.get('state', States.MAIN_MENU)
    text = update.message.text
    response_text = ""
    reply_markup = None

    if current_state == States.WAITING_FOR_TEXT:
        response_text = await gemini_service.generate_text_response(user_id, text)
        reply_markup = get_back_button_keyboard()
    elif current_state == States.WAITING_FOR_STRUCTURED_PROMPT:
        parts = text.split('\n', 1)
        if len(parts) < 2:
            response_text = "Пожалуйста, укажите промпт и JSON-схему, разделенные новой строкой.\nФормат: `prompt`\n`{\"key\": \"value\"}`"
            reply_markup = get_back_button_keyboard()
        else:
            prompt_text = parts[0]
            try:
                schema = json.loads(parts[1])
                response_text = await gemini_service.generate_structured_output(user_id, prompt_text, schema)
                response_text = f"```json\n{response_text}\n```"
                reply_markup = get_back_button_keyboard()
            except json.JSONDecodeError:
                response_text = "Неверный формат JSON схемы. Пожалуйста, убедитесь, что JSON корректен.\nФормат: `prompt`\n`{\"key\": \"value\"}`"
                reply_markup = get_back_button_keyboard()
    elif current_state == States.WAITING_FOR_CODE:
        code = text
        response_text = await gemini_service.execute_code(user_id, code, "Выполни следующий код Python:")
        reply_markup = get_back_button_keyboard()
    elif current_state == States.WAITING_FOR_URL:
        parts = text.split('\n', 1)
        url = parts[0]
        prompt_text = parts[1] if len(parts) > 1 else "Проанализируй содержимое этой страницы."
        if not url.startswith(('http://', 'https://')):
            response_text = "Пожалуйста, введите корректный URL, начинающийся с http:// или https://.\nФормат: `URL`\n`[prompt]`"
            reply_markup = get_back_button_keyboard()
        else:
            response_text = await gemini_service.analyze_url_context(user_id, url, prompt_text)
            reply_markup = get_back_button_keyboard()
    elif current_state == States.WAITING_FOR_SEARCH_QUERY:
        parts = text.split('\n', 1)
        query = parts[0]
        prompt_text = parts[1] if len(parts) > 1 else "Найди информацию по этому запросу."
        response_text = await gemini_service.perform_google_search(user_id, query, prompt_text)
        reply_markup = get_back_button_keyboard()
    elif current_state == States.MAIN_MENU:
        response_text = "Пожалуйста, выберите действие из меню ниже или используйте команду /help."
        reply_markup = get_main_menu_keyboard()
    else:
        response_text = "Неизвестное состояние. Пожалуйста, выберите действие из меню или используйте команду /help."
        reply_markup = get_main_menu_keyboard()

    await update.message.reply_text(response_text, reply_markup=reply_markup)
    if current_state != States.MAIN_MENU: # Only reset state if it was not main menu already
        set_user_state(context, States.MAIN_MENU)

async def handle_image_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    current_state = context.user_data.get('state', States.MAIN_MENU)

    if current_state == States.WAITING_FOR_IMAGE:
        photo_file = await context.bot.get_file(update.message.photo[-1].file_id)
        photo_data = await photo_file.download_as_bytearray()
        
        caption = update.message.caption or ""
        response = await gemini_service.generate_response_with_image(user_id, caption, bytes(photo_data))
        await update.message.reply_text(response, reply_markup=get_back_button_keyboard())
        set_user_state(context, States.MAIN_MENU)
    else:
        await update.message.reply_text("Пожалуйста, выберите 'Понимание изображений' из меню, чтобы отправить изображение.", reply_markup=get_main_menu_keyboard())

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    current_state = context.user_data.get('state', States.MAIN_MENU)

    if current_state == States.WAITING_FOR_VOICE:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        voice_data = await voice_file.download_as_bytearray()
        
        caption = update.message.caption or ""
        response = await gemini_service.generate_response_with_audio(user_id, caption, bytes(voice_data))
        await update.message.reply_text(response, reply_markup=get_back_button_keyboard())
        set_user_state(context, States.MAIN_MENU)
    else:
        await update.message.reply_text("Пожалуйста, выберите 'Обработка голоса' из меню, чтобы отправить голосовое сообщение.", reply_markup=get_main_menu_keyboard())