import os
from telethon import TelegramClient

# Your API credentials from my.telegram.org
API_ID = 38121972          # Replace with your integer api_id
API_HASH = 'e2bc05c031484c609a43e17bb0270168' # Replace with your string api_hash

# The name of the chat/channel/group you want to fetch history from 
# (can be a username like '@username', a phone number, or a invite link/ID)
CHAT_TARGET = '@Seventh'

async def main():
    # Initialize the Telegram client
    async with TelegramClient('telegram_session', API_ID, API_HASH) as client:
        print("Connected to Telegram successfully!")
        
        # Resolve the chat entity
        entity = await client.get_entity(CHAT_TARGET)
        
        # Fetch message history (e.g., the last 100 messages)
        print(f"Fetching messages from {CHAT_TARGET}...")
        async for message in client.iter_messages(entity, limit=100):
            # Print timestamp, sender ID, and message text
            print(f"[{message.date}] ID: {message.id} | {message.text}")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())