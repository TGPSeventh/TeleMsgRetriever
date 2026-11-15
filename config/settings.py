import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
TARGET_CHAT = os.getenv("TARGET_CHAT")

if not API_ID or not API_HASH:
    raise ValueError("Missing Telegram API credentials in environment variables.")

API_ID = int(API_ID)