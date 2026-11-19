from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 1234567  # Replace with your Telegram API ID
api_hash = 'e2bc05c031484c609a43e17bb0270168'  # Replace with your Telegram API Hash

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("SESSION STRING:", client.session.save())