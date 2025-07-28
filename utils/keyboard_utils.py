from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config.constants import Buttons, ButtonText

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(ButtonText.TEXT_GENERATION, callback_data=Buttons.TEXT_GENERATION)],
        [InlineKeyboardButton(ButtonText.IMAGE_UNDERSTANDING, callback_data=Buttons.IMAGE_UNDERSTANDING)],
        [InlineKeyboardButton(ButtonText.VOICE_PROCESSING, callback_data=Buttons.VOICE_PROCESSING)],
        [InlineKeyboardButton(ButtonText.STRUCTURED_OUTPUT, callback_data=Buttons.STRUCTURED_OUTPUT)],
        [InlineKeyboardButton(ButtonText.EXECUTE_CODE, callback_data=Buttons.EXECUTE_CODE)],
        [InlineKeyboardButton(ButtonText.ANALYZE_URL, callback_data=Buttons.ANALYZE_URL)],
        [InlineKeyboardButton(ButtonText.GOOGLE_SEARCH, callback_data=Buttons.GOOGLE_SEARCH)],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_button_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(ButtonText.BACK, callback_data=Buttons.BACK_TO_MAIN_MENU)]
    ]
    return InlineKeyboardMarkup(keyboard)
