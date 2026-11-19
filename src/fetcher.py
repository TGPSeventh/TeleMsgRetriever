import os
import json
import asyncio
from telethon import errors
from telethon.tl.types import (
    MessageActionPhoneCall,
    DocumentAttributeSticker,
    ReactionEmoji,
    ReactionCustomEmoji,
    ReactionPaid,
)

try:
    from telethon.tl.functions.channels import GetForumTopicsRequest  # type: ignore
except ImportError:
    try:
        from telethon.tl.functions.messages import GetForumTopicsRequest  # type: ignore
    except ImportError:
        GetForumTopicsRequest = None


def get_base_export_dir():
    """
    Uses Google Drive exports folder when running in Colab with Drive mounted,
    and falls back to relative 'exports' locally.
    """
    colab_drive_exports = "/content/drive/MyDrive/telegram_retriever/exports"
    if os.path.exists("/content/drive/MyDrive"):
        os.makedirs(colab_drive_exports, exist_ok=True)
        return colab_drive_exports
    os.makedirs("exports", exist_ok=True)
    return "exports"


def get_group_root_path(target_chat):
    """
    Returns the root folder path for the group:
    <base_export_dir>/chat_<name>/
    """
    clean_target = str(target_chat).strip()
    base_name = (
        clean_target.replace("https://t.me/", "")
        .replace("http://t.me/", "")
        .replace("t.me/", "")
        .replace("+", "")
        .lstrip("@")
    )
    clean_name = base_name[5:] if base_name.startswith("chat_") else base_name

    folder_name = f"chat_{clean_name}"
    base_export_dir = get_base_export_dir()
    folder_path = os.path.join(base_export_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


def get_chat_paths(target_chat, topic_id=None):
    """
    Standardizes chat targets into nested folder structures:
    - Root group: <base_export_dir>/chat_<name>/
    - Nested topic: <base_export_dir>/chat_<name>/topic_<id>/
    """
    clean_target = str(target_chat).strip()
    base_name = (
        clean_target.replace("https://t.me/", "")
        .replace("http://t.me/", "")
        .replace("t.me/", "")
        .replace("+", "")
        .lstrip("@")
    )
    clean_name = base_name[5:] if base_name.startswith("chat_") else base_name

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


def _format_entity_name(entity, fallback_id=None):
    if entity is None:
        return str(fallback_id) if fallback_id is not None else "Unknown"
    first = getattr(entity, "first_name", "") or ""
    last = getattr(entity, "last_name", "") or ""
    full_name = f"{first} {last}".strip()
    if full_name:
        return full_name
    title = getattr(entity, "title", None)
    if title:
        return title
    username = getattr(entity, "username", None)
    if username:
        return f"@{username}"
    ent_id = getattr(entity, "id", None) or fallback_id
    return str(ent_id) if ent_id is not None else "Unknown"


async def _resolve_peer_name(client, peer, name_cache):
    if peer is None:
        return "Unknown"

    peer_id = (
        getattr(peer, "user_id", None)
        or getattr(peer, "channel_id", None)
        or getattr(peer, "chat_id", None)
        or getattr(peer, "id", None)
    )

    if peer_id in name_cache:
        return name_cache[peer_id]

    try:
        entity = await client.get_entity(peer)
        label = _format_entity_name(entity, fallback_id=peer_id)
    except Exception:
        label = str(peer_id) if peer_id is not None else "Unknown"

    name_cache[peer_id] = label
    return label


def _reaction_to_label(rec_obj):
    if isinstance(rec_obj, ReactionEmoji):
        return rec_obj.emoticon
    if isinstance(rec_obj, ReactionCustomEmoji):
        return f"⭐:{rec_obj.document_id}"
    if isinstance(rec_obj, ReactionPaid):
        return "💎"
    return getattr(rec_obj, "emoticon", None) or str(rec_obj)


async def _extract_reactions(message, client=None, name_cache=None, me_name=None, peer_name=None):
    """
    Extracts all reactions from message.reactions.results across ReactionEmoji,
    ReactionCustomEmoji, and ReactionPaid, resolving reactor display names when
    available via recent_reactions or known chat participants.
    """
    reactions_list = []
    reactions_obj = getattr(message, "reactions", None)
    results = getattr(reactions_obj, "results", None)
    if not results:
        return reactions_list

    if name_cache is None:
        name_cache = {}

    recent_map = {}
    recent_reactions = getattr(reactions_obj, "recent_reactions", None) or []
    for rr in recent_reactions:
        r_label = _reaction_to_label(getattr(rr, "reaction", None))
        reactor_label = (
            await _resolve_peer_name(client, getattr(rr, "peer_id", None), name_cache)
            if client is not None
            else str(getattr(rr, "peer_id", "Unknown"))
        )
        recent_map.setdefault(r_label, [])
        if reactor_label not in recent_map[r_label]:
            recent_map[r_label].append(reactor_label)

    for r in results:
        emoji = _reaction_to_label(getattr(r, "reaction", None))
        count = int(getattr(r, "count", 1) or 1)
        reactors = list(recent_map.get(emoji, []))

        # Fallback when Telegram omits recent_reactions (common in DMs / some chats)
        if not reactors:
            is_chosen = getattr(r, "chosen_order", None) is not None
            if is_chosen and me_name:
                reactors.append(me_name)
                if count > 1 and peer_name and peer_name != me_name:
                    reactors.append(peer_name)
            elif count == 1 and peer_name and (not me_name or peer_name != me_name):
                reactors.append(peer_name)

        reactions_list.append({
            "reaction": emoji,
            "count": count,
            "reactors": reactors,
        })

    return reactions_list


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
            "limit": 100,
        }

        result = await client(GetForumTopicsRequest(**request_params))  # type: ignore

        if hasattr(result, "topics"):
            for topic in result.topics:
                topics_list.append({
                    "id": topic.id,
                    "title": topic.title,
                })
            print(f"📁 Discovered {len(topics_list)} topics in forum supergroup {target_chat}.")
    except Exception as e:
        print(f"⚠️ This supergroup may not have forums enabled or accessible: {e}")

    return topics_list


async def fetch_chat_history(client, target_chat, limit=None, topic_id=None, overlap_window=50):
    """
    Fetches chat history incrementally, downloading photos, stickers, voice audio, call logs, and reply links.
    Re-checks a small overlap window of recent messages on incremental syncs so newly added reactions
    on recent messages are captured without re-downloading existing media.
    """
    messages_data = []
    existing_by_id = {}
    name_cache = {}

    folder_path, media_dir, master_path, _ = get_chat_paths(target_chat, topic_id=topic_id)

    highest_id = 0
    if os.path.exists(master_path):
        try:
            with open(master_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if isinstance(existing_data, list) and existing_data:
                    existing_by_id = {
                        msg["id"]: msg for msg in existing_data if isinstance(msg, dict) and "id" in msg
                    }
                    highest_id = max(existing_by_id.keys())
                    print(
                        f"📄 Found archive at {master_path}. "
                        f"Refreshing from ID {max(0, highest_id - overlap_window)}..."
                    )
        except Exception as e:
            print(f"⚠️ Could not read master JSON for incremental fetch: {e}")

    try:
        me_entity = await client.get_me()
        me_name = _format_entity_name(me_entity)
        if me_entity and getattr(me_entity, "id", None):
            name_cache[me_entity.id] = me_name

        entity = await client.get_entity(target_chat)
        peer_name = None
        if getattr(entity, "id", None) and getattr(entity, "id", None) != getattr(me_entity, "id", None):
            peer_name = _format_entity_name(entity)
            name_cache[entity.id] = peer_name

        kwargs = {}
        if topic_id:
            kwargs["reply_to"] = topic_id

        if highest_id > 0 and limit is None:
            kwargs["min_id"] = max(0, highest_id - overlap_window)

        print("Downloading message batches, media, stickers, voice notes, call logs, and replies from Telegram...")

        async for message in client.iter_messages(entity, limit=limit, **kwargs):
            if not message.id:
                continue

            sender_name = "Unknown"
            if message.sender:
                sender_id_val = getattr(message.sender, "id", None)
                sender_name = _format_entity_name(message.sender, fallback_id=sender_id_val)
                if sender_id_val is not None:
                    name_cache[sender_id_val] = sender_name
                if not peer_name and sender_id_val and sender_id_val != getattr(me_entity, "id", None):
                    peer_name = sender_name

            reactions_list = await _extract_reactions(
                message,
                client=client,
                name_cache=name_cache,
                me_name=me_name,
                peer_name=peer_name,
            )

            prev_msg = existing_by_id.get(message.id)
            media_relative_path = prev_msg.get("media_path") if prev_msg else None
            is_sticker = False
            is_voice = False

            # Explicit check for sticker/voice attributes on documents
            if message.media and hasattr(message.media, "document") and getattr(message.media.document, "attributes", None):
                doc = message.media.document
                for attr in doc.attributes:
                    if isinstance(attr, DocumentAttributeSticker) or attr.__class__.__name__ == "DocumentAttributeSticker":
                        is_sticker = True
                    elif attr.__class__.__name__ == "DocumentAttributeAudio" and getattr(attr, "voice", False):
                        is_voice = True

            if getattr(message, "sticker", False):
                is_sticker = True
            if getattr(message, "voice", False):
                is_voice = True

            # Download media only if not already present locally
            existing_abs_media = (
                os.path.join(folder_path, media_relative_path) if media_relative_path else None
            )
            if existing_abs_media and os.path.exists(existing_abs_media):
                pass
            elif message.photo or message.media:
                try:
                    os.makedirs(media_dir, exist_ok=True)
                    downloaded_path = await client.download_media(message, file=media_dir)
                    if downloaded_path:
                        filename = os.path.basename(downloaded_path)
                        media_relative_path = f"media/{filename}"
                except Exception as e:
                    print(f"⚠️ Failed to download media for message {message.id}: {e}")

            call_info = None
            if isinstance(message.action, MessageActionPhoneCall):
                action = message.action
                reason = type(action.reason).__name__ if hasattr(action, "reason") and action.reason else "Completed"
                duration = getattr(action, "duration", 0)

                call_info = {
                    "video": getattr(action, "video", False),
                    "duration": duration,
                    "duration_formatted": f"{duration // 60}m {duration % 60}s" if duration else "Missed / Cancelled",
                    "reason": reason,
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
                "reactions": reactions_list,
            })

            if len(messages_data) % 100 == 0:
                await asyncio.sleep(0.5)

    except errors.FloodWaitError as e:
        print(f"⚠️ Telegram rate limit hit. Must wait {e.seconds} seconds.")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"Error fetching history: {e}")

    return messages_data