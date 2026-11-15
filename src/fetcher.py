import os
import json
import asyncio
from telethon import errors
from telethon.tl.types import MessageActionPhoneCall, DocumentAttributeSticker

try:
    from telethon.tl.functions.channels import GetForumTopicsRequest  # type: ignore
except ImportError:
    try:
        from telethon.tl.functions.messages import GetForumTopicsRequest  # type: ignore
    except ImportError:
        GetForumTopicsRequest = None

def get_group_root_path(target_chat):
    r"""
    Returns the root absolute folder path for the group:
    C:\Users\TGPSe\Projects\telegram_retriever\exports\chat_<name>\
    """
    clean_target = str(target_chat).strip()
    base_name = clean_target.replace('https://t.me/', '').replace('t.me/', '').replace('+', '').lstrip('@')
    clean_name = base_name[5:] if base_name.startswith('chat_') else base_name
    
    folder_name = f"chat_{clean_name}"
    base_export_dir = r"C:\Users\TGPSe\Projects\telegram_retriever\exports"
    folder_path = os.path.join(base_export_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

def get_chat_paths(target_chat, topic_id=None):
    r"""
    Standardizes chat targets into nested absolute folder structures:
    - Root group: exports\chat_<name>\
    - Nested topic: exports\chat_<name>\topic_<id>\
    """
    clean_target = str(target_chat).strip()
    base_name = clean_target.replace('https://t.me/', '').replace('t.me/', '').replace('+', '').lstrip('@')
    clean_name = base_name[5:] if base_name.startswith('chat_') else base_name
    
    group_folder = get_group_root_path(target_chat)
    
    if topic_id:
        folder_name = f"topic_{topic_id}"
        folder_path = os.path.join(group_folder, folder_name)
        file_prefix = f"chat_{clean_name}_topic_{topic_id}"
    else:
        folder_path = group_folder
        file_prefix = f"chat_{clean_name}"
        
    os.makedirs(folder_path, exist_ok=True)
    media_path = os.path.join(folder_path, "media")
    os.makedirs(media_path, exist_ok=True)
    
    master_path = os.path.join(folder_path, f"{file_prefix}_master.json")
    html_path = os.path.join(folder_path, f"{file_prefix}_viewer.html")
    
    return folder_path, media_path, master_path, html_path

async def fetch_all_forum_topics(client, target_chat):
    """
    Scans a supergroup and retrieves all forum topics so they can be archived individually.
    """
    entity = await client.get_entity(target_chat)
    topics_list = []
    
    if GetForumTopicsRequest is None:
        print("⚠️ Forum topics request schema is not supported in this Telethon version.")
        return topics_list

    try:
        request_params = {
            "peer": entity,
            "offset_date": None,
            "offset_id": 0,
            "offset_topic": 0,
            "limit": 100
        }
        
        result = await client(GetForumTopicsRequest(**request_params))  # type: ignore
        
        if hasattr(result, 'topics'):
            for topic in result.topics:
                topics_list.append({
                    "id": topic.id,
                    "title": topic.title
                })
            print(f"📁 Discovered {len(topics_list)} topics in forum supergroup {target_chat}.")
    except Exception as e:
        print(f"⚠️ This supergroup may not have forums enabled or accessible: {e}")
        
    return topics_list

async def fetch_chat_history(client, target_chat, limit=None, topic_id=None):
    """
    Fetches chat history incrementally, downloading photos, stickers, voice audio, call logs, and reply links.
    """
    messages_data = []
    
    folder_path, media_dir, master_path, _ = get_chat_paths(target_chat, topic_id=topic_id)
    
    highest_id = 0
    if os.path.exists(master_path):
        try:
            with open(master_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if existing_data:
                    highest_id = max(msg["id"] for msg in existing_data)
                    print(f"📄 Found local archive at {master_path}. Fetching messages newer than ID {highest_id}...")
        except Exception as e:
            print(f"⚠️ Could not read master JSON for incremental fetch: {e}")

    try:
        entity = await client.get_entity(target_chat)
        
        kwargs = {}
        if topic_id:
            kwargs['reply_to'] = topic_id
            
        if highest_id > 0 and limit is None:
            kwargs['min_id'] = highest_id

        print("Downloading message batches, media, stickers, voice notes, call logs, and replies from Telegram...")
        
        async for message in client.iter_messages(entity, limit=limit, **kwargs):
            if not message.id:
                continue
                
            sender_name = "Unknown"
            if message.sender:
                if hasattr(message.sender, 'first_name') and message.sender.first_name:
                    sender_name = message.sender.first_name
                    if getattr(message.sender, 'last_name', None):
                        sender_name += f" {message.sender.last_name}"
                elif hasattr(message.sender, 'title') and message.sender.title:
                    sender_name = message.sender.title

            reactions_list = []
            if message.reactions and message.reactions.results:
                for r in message.reactions.results:
                    emoji = getattr(r.reaction, 'emoticon', str(r.reaction))
                    reactions_list.append({
                        "reaction": emoji,
                        "count": r.count
                    })

            media_relative_path = None
            is_sticker = False
            is_voice = False

            # Explicit check for sticker/voice attributes on documents
            if message.media and hasattr(message.media, 'document'):
                doc = message.media.document
                for attr in doc.attributes:
                    if isinstance(attr, DocumentAttributeSticker) or attr.__class__.__name__ == 'DocumentAttributeSticker':
                        is_sticker = True
                    elif attr.__class__.__name__ == 'DocumentAttributeAudio' and getattr(attr, 'voice', False):
                        is_voice = True

            if getattr(message, 'sticker', False):
                is_sticker = True
            if getattr(message, 'voice', False):
                is_voice = True

            # Download media handling for photos, documents, stickers, and voice notes
            if message.photo or message.media:
                try:
                    os.makedirs(media_dir, exist_ok=True)
                    # Pass the message object directly to download the attached file document
                    downloaded_path = await client.download_media(message, file=media_dir)
                    if downloaded_path:
                        filename = os.path.basename(downloaded_path)
                        media_relative_path = f"media/{filename}"
                except Exception as e:
                    print(f"⚠️ Failed to download media for message {message.id}: {e}")

            call_info = None
            if isinstance(message.action, MessageActionPhoneCall):
                action = message.action
                reason = type(action.reason).__name__ if hasattr(action, 'reason') and action.reason else "Completed"
                duration = getattr(action, 'duration', 0)
                
                call_info = {
                    "video": getattr(action, 'video', False),
                    "duration": duration,
                    "duration_formatted": f"{duration // 60}m {duration % 60}s" if duration else "Missed / Cancelled",
                    "reason": reason
                }

            reply_to_id = None
            if message.reply_to and message.reply_to.reply_to_msg_id:
                reply_to_id = message.reply_to.reply_to_msg_id

            messages_data.append({
                "id": message.id,
                "sender_id": message.sender_id,
                "sender_name": sender_name,
                "text": message.text or "",
                "media_path": media_relative_path,
                "is_sticker": is_sticker,
                "is_voice": is_voice,
                "call_info": call_info,
                "reply_to_message_id": reply_to_id,
                "date": message.date.strftime("%Y-%m-%d %H:%M:%S") if message.date else None,
                "reactions": reactions_list
            })
            
            if len(messages_data) % 100 == 0:
                await asyncio.sleep(0.5)
        
    except errors.FloodWaitError as e:
        print(f"⚠️ Telegram rate limit hit. Must wait {e.seconds} seconds.")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"Error fetching history: {e}")

    return messages_data