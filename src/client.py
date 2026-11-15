import os
from telethon import TelegramClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Explicitly cast or validate environment variables as strings for Pylance safety
API_ID_RAW = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")

# Fallback or parse safely
API_ID = int(API_ID_RAW) if API_ID_RAW else 0
API_HASH_STR: str = API_HASH if API_HASH is not None else ""

def create_telegram_client(session_name="session_name"):
    """
    Initializes and returns the Telethon TelegramClient instance.
    """
    if not API_ID or not API_HASH_STR:
        raise ValueError("⚠️ TELEGRAM_API_ID or TELEGRAM_API_HASH is missing from your environment variables or .env file.")
        
    return TelegramClient(session_name, API_ID, API_HASH_STR)