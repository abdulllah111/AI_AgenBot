import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# HTTP_PROXY_URL = os.getenv("http://rkdgphba:fjk6bg6afgku@198.23.239.134:6540/") # e.g., "http://rkdgphba:fjk6bg6afgku@23.95.150.145:6114/"