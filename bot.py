import os
import asyncio
from telethon import events
from src.client import create_telegram_client
from src.fetcher import fetch_chat_history, fetch_all_forum_topics
from src.exporter import save_exports, generate_group_hub_html

# Initialize client (uses user session so you can scrape groups you have access to)
client = create_telegram_client("bot_session")

@client.on(events.NewMessage(pattern=r'/archive\s+(.+)'))
async def handle_archive_command(event):
    """
    Triggered when you send: /archive @channel_name or group link
    """
    args = event.pattern_match.group(1).strip()
    parts = args.split()
    
    target_chat = parts[0]
    topic_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
    
    status_msg = await event.reply(f"🔄 Starting archive process for `{target_chat}`{f' (Topic ID: {topic_id})' if topic_id else ''}...")
    
    try:
        me = await client.get_me()
        my_user_id = me.id if me else None  # type: ignore

        topics = []
        if not topic_id:
            try:
                topics = await fetch_all_forum_topics(client, target_chat)
            except Exception as e:
                print(f"ℹ️ Standard chat mode or topics check skipped: {e}")

        if topics:
            generate_group_hub_html(target_chat, topics)
            for topic in topics:
                messages = await fetch_chat_history(client, target_chat, limit=None, topic_id=topic['id'])
                if messages:
                    save_exports(messages, target_chat, topic_id=topic['id'], my_user_id=my_user_id)
            
            await status_msg.edit(f"✅ **Archive Complete!**\n\nSuccessfully archived supergroup `{target_chat}` with **{len(topics)} forum topics**.\n📁 Check your local `exports/` folder for the Master Hub (`index.html`).")
        else:
            messages = await fetch_chat_history(client, target_chat, limit=None, topic_id=topic_id)
            if messages:
                save_exports(messages, target_chat, topic_id=topic_id, my_user_id=my_user_id)
                await status_msg.edit(f"✅ **Archive Complete!**\n\nSuccessfully processed **{len(messages)} messages** for `{target_chat}`.")
            else:
                await status_msg.edit(f"⚠️ Archive finished, but no messages were found or chat is up to date.")
                
    except Exception as e:
        await status_msg.edit(f"❌ **Archive Failed:**\n`{str(e)}`")

@client.on(events.NewMessage(pattern=r'/help'))
async def handle_help_command(event):
    help_text = (
        "🤖 **Telegram Archiver Bot Help**\n\n"
        "Trigger commands directly in chat:\n"
        "• `/archive @channel_name` - Archives a normal chat/channel or auto-discovers all forum topics.\n"
        "• `/archive @group_name 123` - Archives a specific topic ID inside a forum.\n"
        "• `/help` - Shows this command list."
    )
    await event.reply(help_text)

async def main():
    print("🤖 Telegram Bot listener is active. Send /help or /archive to your saved messages or chat...")
    
    # Uses context manager and silences Pylance stub warning safely
    async with client:
        print("Connected! Listening for commands...")
        await client.run_until_disconnected()  # type: ignore

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped cleanly.")