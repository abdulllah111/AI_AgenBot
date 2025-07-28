class States:
    MAIN_MENU = 0
    WAITING_FOR_TEXT = 1
    WAITING_FOR_IMAGE = 2
    WAITING_FOR_VOICE = 3
    WAITING_FOR_STRUCTURED_PROMPT = 4
    WAITING_FOR_CODE = 5
    WAITING_FOR_URL = 6
    WAITING_FOR_SEARCH_QUERY = 7

class Buttons:
    TEXT_GENERATION = "text_generation"
    IMAGE_UNDERSTANDING = "image_understanding"
    VOICE_PROCESSING = "voice_processing"
    STRUCTURED_OUTPUT = "structured_output"
    EXECUTE_CODE = "execute_code"
    ANALYZE_URL = "analyze_url"
    GOOGLE_SEARCH = "google_search"
    BACK_TO_MAIN_MENU = "back_to_main_menu"

class ButtonText:
    TEXT_GENERATION = "Генерация текста"
    IMAGE_UNDERSTANDING = "Понимание изображений"
    VOICE_PROCESSING = "Обработка голоса"
    STRUCTURED_OUTPUT = "Структурированный вывод"
    EXECUTE_CODE = "Выполнить код"
    ANALYZE_URL = "Анализ URL"
    GOOGLE_SEARCH = "Google Поиск"
    BACK = "⬅️ Назад"
