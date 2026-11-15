import asyncio
import time
from src.client import create_telegram_client
from src.fetcher import fetch_chat_history, fetch_all_forum_topics
from src.exporter import save_exports, generate_group_hub_html


async def run_sync(target_chat, limit, topic_id):
    """Executes a single incremental fetch, merge, snapshot, and HTML update pass."""
    client = create_telegram_client()
    
    try:
        async with client:
            print("\n[Sync Started] Connected to Telegram...")
            me = await client.get_me()
            my_user_id = me.id if me else None  # type: ignore

            topics = []
            if not topic_id:
                try:
                    topics = await fetch_all_forum_topics(client, target_chat)
                except Exception as e:
                    print(f"ℹ️ Standard chat mode or topics check skipped: {e}")

            if topics:
                # Generate master group hub dashboard at the root level
                generate_group_hub_html(target_chat, topics)

                for topic in topics:
                    print(f"\n----------------------------------------")
                    print(f"Archiving Topic: [{topic['id']}] {topic['title']}")
                    print(f"----------------------------------------")
                    
                    messages = await fetch_chat_history(client, target_chat, limit=limit, topic_id=topic['id'])
                    
                    if messages:
                        save_exports(messages, target_chat, topic_id=topic['id'], my_user_id=my_user_id)
                        print(f"[Sync Complete] Topic '{topic['title']}' updated ({len(messages)} messages processed).")
                    else:
                        print(f"-> No new messages in topic '{topic['title']}'.")
            else:
                messages = await fetch_chat_history(client, target_chat, limit=limit, topic_id=topic_id)
                if messages:
                    save_exports(messages, target_chat, topic_id=topic_id, my_user_id=my_user_id)
                    print(f"[Sync Complete] Export folder updated successfully ({len(messages)} messages processed).")
                else:
                    print("[Sync Complete] No new messages found. Local archive is already up to date.")
                    
    except Exception as e:
        print(f"[Sync Error] {e}")

async def main():
    print("=== Telegram History Retriever ===")
    print("Accepted formats for target chat:")
    print("  - Public Username/Channel: @channel_name")
    print("  - Invite Link / Hash: https://t.me/+AbCdEfGhI or +AbCdEfGhI")
    print("  - Phone Number: +639123456789")
    print("  - Direct Numeric ID: 123456789\n")
    
    target_chat = input("Enter target chat: ").strip()
    if not target_chat:
        print("Error: Target chat cannot be empty.")
        return

    topic_input = input("Enter Topic ID if pulling from a specific forum topic (leave blank to auto-discover all topics): ").strip()
    topic_id = int(topic_input) if topic_input.isdigit() else None

    limit_input = input("Enter message limit per fetch (leave blank or type 'all' for complete history): ").strip()
    
    if limit_input.lower() in ["", "all", "none"]:
        limit = None
        print(f"\nTarget chat: {target_chat} (Fetching full history / incremental delta)")
    else:
        try:
            limit = int(limit_input)
            print(f"\nTarget chat: {target_chat} (Fetching up to {limit} messages per pass)")
        except ValueError:
            limit = None

    # Dynamic Execution Mode Prompt
    print("\n--- Execution Mode ---")
    print("  [1] Run once and exit")
    print("  [2] Run continuously in a recurring loop")
    mode_choice = input("Select mode [1 or 2, default 1]: ").strip()

    if mode_choice == "2":
        print("\n--- Select Sync Interval (in seconds) ---")
        print("  [1] 30 seconds (Real-time incremental sync)")
        print("  [2] 300 seconds (5 minutes)")
        print("  [3] 900 seconds (15 minutes)")
        print("  [4] 1800 seconds (30 minutes)")
        print("  [5] 3600 seconds (60 minutes / 1 hour - Default)")
        print("  [6] Custom interval in seconds")
        
        interval_choice = input("Select interval option [1-6, default 5]: ").strip()
        
        if interval_choice == "1":
            interval_seconds = 30
        elif interval_choice == "2":
            interval_seconds = 300
        elif interval_choice == "3":
            interval_seconds = 900
        elif interval_choice == "4":
            interval_seconds = 1800
        elif interval_choice == "6":
            custom_interval = input("Enter custom interval in seconds (minimum 30s): ").strip()
            try:
                interval_seconds = int(custom_interval)
                if interval_seconds < 30:
                    print("⚠️ Warning: Intervals under 30 seconds risk Telegram flood limits. Adjusting to 30s minimum.")
                    interval_seconds = 30
            except ValueError:
                interval_seconds = 3600
        else:
            interval_seconds = 3600

        print("\n--- Select Total Run Duration (how long the script stays active) ---")
        print("  [1] Run indefinitely until stopped manually (Ctrl+C)")
        print("  [2] Run for a specific duration (in hours)")
        
        duration_choice = input("Select duration option [1 or 2, default 1]: ").strip()
        
        max_duration_seconds = None
        if duration_choice == "2":
            hours_input = input("Enter total run duration in hours (e.g., 2, 12, 24): ").strip()
            try:
                hours = float(hours_input)
                max_duration_seconds = hours * 3600
                print(f"⏱️ Script will automatically stop after {hours} hours.")
            except ValueError:
                print("⚠️ Invalid input. Running indefinitely.")

        minutes_display = round(interval_seconds / 60, 1)
        print(f"\n[Active] Recurring sync started for {target_chat}:")
        print(f"  • Interval: Every {interval_seconds} seconds (~{minutes_display if interval_seconds >= 60 else f'{interval_seconds}s'} mins)")
        print(f"  • Duration limit: {f'{max_duration_seconds / 3600} hours' if max_duration_seconds else 'Infinite'}")
        print("Press Ctrl+C at any time to stop.\n")

        start_time = time.time()
        
        while True:
            if max_duration_seconds and (time.time() - start_time >= max_duration_seconds):
                print("\n[Duration Reached] Total specified run duration has elapsed. Shutting down cleanly.")
                break

            await run_sync(target_chat, limit, topic_id)
            print(f"\nWaiting {interval_seconds} seconds until the next sync...")
            await asyncio.sleep(interval_seconds)
    else:
        print(f"\nRunning one-time fetch for {target_chat}...")
        await run_sync(target_chat, limit, topic_id)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram stopped by user.")