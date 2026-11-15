from telethon import TelegramClient
from config.settings import API_ID, API_HASH

def create_telegram_client(session_name: str = "session_data") -> TelegramClient:
    """Initializes and returns the Telethon TelegramClient instance."""
    return TelegramClient(session_name, API_ID, API_HASH)

