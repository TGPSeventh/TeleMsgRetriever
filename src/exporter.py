import json
import os
from datetime import datetime
from src.fetcher import get_chat_paths

def load_existing_json(json_filepath):
    if os.path.exists(json_filepath):
        try:
            with open(json_filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def normalize_message_schema(msg):
    """
    Enforces strict uniform JSON schema keys across all records.
    """
    return {
        "id": msg.get("id"),
        "sender_id": msg.get("sender_id"),
        "sender_name": msg.get("sender_name", "Unknown"),
        "text": msg.get("text", ""),
        "media_path": msg.get("media_path"),
        "call_info": msg.get("call_info"),
        "reply_to_message_id": msg.get("reply_to_message_id"),
        "date": msg.get("date"),
        "reactions": msg.get("reactions", [])
    }

def merge_messages(old_messages, new_messages):
    msg_map = {msg["id"]: normalize_message_schema(msg) for msg in old_messages}
    for msg in new_messages:
        normalized = normalize_message_schema(msg)
        if not normalized.get("media_path") and msg["id"] in msg_map:
            normalized["media_path"] = msg_map[msg["id"]].get("media_path")
        if not normalized.get("call_info") and msg["id"] in msg_map:
            normalized["call_info"] = msg_map[msg["id"]].get("call_info")
        if not normalized.get("reply_to_message_id") and msg["id"] in msg_map:
            normalized["reply_to_message_id"] = msg_map[msg["id"]].get("reply_to_message_id")
        msg_map[msg["id"]] = normalized
    
    combined = sorted(msg_map.values(), key=lambda x: x["id"])
    return combined

def save_exports(data, chat_target, topic_id=None, my_user_id=None):
    folder, _, master_json_path, html_path = get_chat_paths(chat_target, topic_id=topic_id)
    
    existing_messages = load_existing_json(master_json_path)
    combined_messages = merge_messages(existing_messages, data)
    
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    snapshot_path = os.path.join(folder, f"export_{timestamp_str}.json")
    
    normalized_batch = [normalize_message_schema(m) for m in data]
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(normalized_batch, f, ensure_ascii=False, indent=4)
    print(f"-> Saved timestamped snapshot: {snapshot_path}")

    with open(master_json_path, "w", encoding="utf-8") as f:
        json.dump(combined_messages, f, ensure_ascii=False, indent=4)
    print(f"-> Updated master JSON archive: {master_json_path}")

    _generate_html_file(combined_messages, html_path, chat_title=chat_target, my_user_id=my_user_id)
    print(f"-> Generated HTML viewer: {os.path.abspath(html_path)}")

def _generate_html_file(data, filename, chat_title="Telegram Export", my_user_id=None):
    chronological_data = data
    json_payload = json.dumps(chronological_data, ensure_ascii=False)
    my_id_json = json.dumps(my_user_id)

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{chat_title} - Telegram Mobile Viewer</title>
    <style>
        :root {{
            --bg-color: #0f1923;
            --header-bg: #1e2c3a;
            --incoming-bubble: #1f2c38;
            --outgoing-bubble: #2b5278;
            --text-primary: #f5f5f5;
            --text-secondary: #879ab0;
            --accent-color: #64b5f6;
            --reaction-bg: #243447;
            --input-bg: #17212b;
            --border-color: #111b24;
            --date-badge-bg: rgba(0, 0, 0, 0.45);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
        body {{ background-color: #000; color: var(--text-primary); display: flex; justify-content: center; height: 100vh; overflow: hidden; }}
        
        .app-container {{ background-color: var(--bg-color); width: 100%; max-width: 480px; height: 100%; display: flex; flex-direction: column; position: relative; box-shadow: 0 0 20px rgba(0,0,0,0.8); }}

        header {{ background-color: var(--header-bg); padding: 10px 14px; display: flex; align-items: center; gap: 12px; height: 56px; border-bottom: 1px solid var(--border-color); z-index: 10; flex-shrink: 0; }}
        .back-arrow {{ font-size: 20px; color: var(--text-secondary); cursor: pointer; }}
        .chat-avatar {{ width: 40px; height: 40px; border-radius: 50%; background: #5288c1; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 16px; color: white; flex-shrink: 0; }}
        .header-meta {{ display: flex; flex-direction: column; flex: 1; min-width: 0; }}
        .header-title {{ font-size: 15px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .header-subtitle {{ font-size: 12px; color: var(--text-secondary); }}
        .header-search-icon {{ font-size: 18px; color: var(--text-secondary); cursor: pointer; padding: 8px; }}

        #search-container {{ display: none; background: var(--header-bg); padding: 8px 14px; border-bottom: 1px solid var(--border-color); z-index: 5; }}
        #search-box {{ background: var(--input-bg); border: none; padding: 8px 12px; border-radius: 8px; color: white; font-size: 13px; width: 100%; outline: none; }}

        #chat-container {{ 
            flex: 1; 
            overflow-y: auto; 
            padding: 12px; 
            display: flex; 
            flex-direction: column; 
            gap: 6px; 
            background-color: var(--bg-color);
            background-image: url("data:image/svg+xml,%3Csvg width='80' height='80' viewBox='0 0 80 80' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23ffffff' fill-opacity='0.025' fill-rule='evenodd'%3E%3Cpath d='M0 0h40v40H0V0zm40 40h40v40H40V40zm0-40h2l-2 2V0zm0 4l4-4h2l-6 6V4zm6 2l4-4h2l-6 6V6zm6 2l4-4h2l-6 6V8zm6 2l4-4h2l-6 6V10zm6 2l4-4h2l-6 6V12zm6 2l4-4h2l-6 6V14zm6 2l4-4h2l-6 6V16zm2-16l2 2v2l-4-4h2zm0 6l4-4v2l-2 2h-2zm0 4l4-4v2l-2 2h-2zm0 4l4-4v2l-2 2h-2zm0 4l4-4v2l-2 2h-2zm0 4l4-4v2l-2 2h-2zm0 4l4-4v2l-2 2h-2zm0 4l4-4v2l-2 2h-2zm0 4l4-4v2l-2 2h-2z'/%3E%3C/g%3E%3C/svg%3E");
        }}
        
        .date-divider {{ display: flex; justify-content: center; margin: 10px 0 6px 0; }}
        .date-badge {{ background-color: var(--date-badge-bg); backdrop-filter: blur(4px); color: #fff; font-size: 11.5px; font-weight: 500; padding: 3px 10px; border-radius: 10px; box-shadow: 0 1px 2px rgba(0,0,0,0.2); }}

        .message-row {{ display: flex; gap: 8px; align-items: flex-end; width: 100%; margin-top: 2px; }}
        .message-row.outbound {{ flex-direction: row-reverse; }}

        .bubble-avatar {{ width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 11px; flex-shrink: 0; color: white; margin-bottom: 2px; }}
        
        .bubble {{ background-color: var(--incoming-bubble); padding: 6px 10px 4px 10px; border-radius: 12px 12px 12px 4px; max-width: 80%; position: relative; box-shadow: 0 1px 2px rgba(0,0,0,0.2); min-width: 200px; }}
        .message-row.outbound .bubble {{ background-color: var(--outgoing-bubble); border-radius: 12px 12px 4px 12px; }}

        .sender-name {{ font-size: 12px; font-weight: 600; margin-bottom: 2px; }}
        .message-row.outbound .sender-name {{ display: none; }}

        .message-media {{ margin-bottom: 4px; border-radius: 8px; overflow: hidden; max-width: 260px; cursor: pointer; }}
        .message-media img {{ width: 100%; height: auto; display: block; border-radius: 8px; }}

        .call-content {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
        .call-text-side {{ display: flex; flex-direction: column; gap: 2px; }}
        .call-main-title {{ font-size: 14px; font-weight: 600; color: #fff; }}
        .call-sub-info {{ font-size: 11.5px; color: var(--text-secondary); display: flex; align-items: center; gap: 4px; }}
        .call-check {{ color: #4cd964; font-weight: bold; }}
        .call-icon-badge {{ font-size: 20px; color: var(--accent-color); flex-shrink: 0; display: flex; align-items: center; }}

        .reply-preview {{ border-left: 2px solid var(--accent-color); padding-left: 6px; margin-bottom: 4px; background: rgba(0, 0, 0, 0.15); border-radius: 0 4px 4px 0; padding-top: 2px; padding-bottom: 2px; cursor: pointer; }}
        .reply-sender {{ font-size: 11px; font-weight: 600; color: var(--accent-color); }}
        .reply-text {{ font-size: 11.5px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 220px; }}

        .message-text {{ font-size: 13.5px; line-height: 1.4; white-space: pre-wrap; word-wrap: break-word; color: #fff; }}
        
        .meta-footer {{ display: flex; align-items: center; justify-content: flex-end; gap: 6px; margin-top: 2px; float: right; margin-left: 8px; }}
        .reactions {{ display: flex; flex-wrap: wrap; gap: 3px; float: left; margin-top: 2px; }}
        .timestamp {{ font-size: 10px; color: var(--text-secondary); white-space: nowrap; }}
        .message-row.outbound .timestamp {{ color: #9bc2e6; }}
        
        .reaction-pill {{ background-color: var(--reaction-bg); padding: 1px 6px; border-radius: 10px; font-size: 11px; display: flex; align-items: center; gap: 3px; border: 1px solid rgba(255,255,255,0.05); }}

        .input-bar {{ background-color: var(--input-bg); padding: 10px 12px; display: flex; align-items: center; gap: 10px; border-top: 1px solid var(--border-color); flex-shrink: 0; }}
        .input-bar span {{ color: var(--text-secondary); font-size: 20px; cursor: pointer; }}
        .fake-input {{ flex: 1; background: #0e1621; border-radius: 20px; padding: 9px 14px; color: var(--text-secondary); font-size: 13.5px; }}
    </style>
</head>
<body>
    <div class="app-container">
        <header>
            <div class="back-arrow">‹</div>
            <div class="chat-avatar" id="header-avatar">T</div>
            <div class="header-meta">
                <div class="header-title">{chat_title}</div>
                <div class="header-subtitle" id="msg-count">0 messages</div>
            </div>
            <div class="header-search-icon" id="search-toggle">🔍</div>
        </header>

        <div id="search-container">
            <input type="text" id="search-box" placeholder="Search in chat...">
        </div>

        <div id="chat-container"></div>

        <div class="input-bar">
            <span>📎</span>
            <div class="fake-input">Message</div>
            <span>🎤</span>
        </div>
    </div>

    <script>
        const rawMessages = {json_payload};
        const myUserId = {my_id_json};
        const messageMap = new Map(rawMessages.map(m => [m.id, m]));
        const container = document.getElementById('chat-container');
        const countLabel = document.getElementById('msg-count');
        const searchBox = document.getElementById('search-box');
        const searchContainer = document.getElementById('search-container');
        const searchToggle = document.getElementById('search-toggle');

        const chatTitle = "{chat_title}";
        document.getElementById('header-avatar').textContent = chatTitle.replace('@', '').substring(0, 2).toUpperCase();

        const colors = ['#e17076', '#7bc862', '#e5ca77', '#65aadd', '#a695e7', '#ee7aae', '#6ec9cb', '#faa774'];
        function getColor(id) {{
            if (!id) return colors[0];
            return colors[Math.abs(id) % colors.length];
        }}

        function getInitials(name) {{
            if (!name) return "?";
            return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        }}

        function formatDateHeading(dateString) {{
            if (!dateString) return '';
            let parseStr = dateString;
            if (!parseStr.endsWith('Z') && !parseStr.includes('+') && !parseStr.includes('-', 10)) {{
                parseStr += 'Z';
            }}
            const messageDate = new Date(parseStr);
            if (isNaN(messageDate)) return dateString.split(' ')[0];

            const today = new Date();
            if (messageDate.toDateString() === today.toDateString()) return 'Today';

            const yesterday = new Date();
            yesterday.setDate(today.getDate() - 1);
            if (messageDate.toDateString() === yesterday.toDateString()) return 'Yesterday';

            return messageDate.toLocaleDateString(undefined, {{ month: 'long', day: 'numeric', year: 'numeric' }});
        }}

        function formatMessageTime(dateString) {{
            if (!dateString) return '';
            let parseStr = dateString;
            if (!parseStr.endsWith('Z') && !parseStr.includes('+') && !parseStr.includes('-', 10)) {{
                parseStr += 'Z';
            }}
            const messageDate = new Date(parseStr);
            if (isNaN(messageDate)) return dateString.substring(11, 16);

            return messageDate.toLocaleTimeString([], {{ hour: 'numeric', minute: '2-digit' }});
        }}

        function scrollToMessage(msgId) {{
            const el = document.getElementById('msg-' + msgId);
            if (el) {{
                el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                el.style.backgroundColor = 'rgba(100, 181, 246, 0.2)';
                setTimeout(() => el.style.backgroundColor = '', 1500);
            }}
        }}

        function renderMessages(messages) {{
            container.innerHTML = '';
            countLabel.textContent = `${{messages.length}} messages`;

            let lastDateStr = '';

            messages.forEach((msg) => {{
                const rawDate = msg.date ? msg.date.split(' ')[0] : '';
                
                if (rawDate && rawDate !== lastDateStr) {{
                    lastDateStr = rawDate;
                    const divider = document.createElement('div');
                    divider.className = 'date-divider';
                    divider.innerHTML = `<div class="date-badge">${{formatDateHeading(msg.date)}}</div>`;
                    container.appendChild(divider);
                }}

                const row = document.createElement('div');
                const isOutbound = myUserId && msg.sender_id === myUserId;
                row.className = 'message-row' + (isOutbound ? ' outbound' : '');
                row.id = 'msg-' + msg.id;

                const color = getColor(msg.sender_id);
                const initials = getInitials(msg.sender_name);
                const timeStr = formatMessageTime(msg.date);
                const avatarHtml = isOutbound ? '' : `<div class="bubble-avatar" style="background-color: ${{color}}">${{initials}}</div>`;

                let replyHtml = '';
                if (msg.reply_to_message_id) {{
                    const parentMsg = messageMap.get(msg.reply_to_message_id);
                    const parentText = parentMsg ? (parentMsg.text || (parentMsg.media_path ? '[Media]' : '[Call]')) : 'Original message';
                    const parentSender = parentMsg ? parentMsg.sender_name : 'User';
                    replyHtml = `
                        <div class="reply-preview" onclick="scrollToMessage(${{msg.reply_to_message_id}})">
                            <div class="reply-sender">${{parentSender}}</div>
                            <div class="reply-text">${{escapeHtml(parentText)}}</div>
                        </div>
                    `;
                }}

                let contentHtml = '';
                if (msg.call_info) {{
                    const callType = msg.call_info.video ? 'Incoming Video Call' : 'Incoming Voice Call';
                    const callIconSymbol = msg.call_info.video ? '📹' : '📞';
                    contentHtml = `
                        <div class="call-content">
                            <div class="call-text-side">
                                <div class="call-main-title">${{callType}}</div>
                                <div class="call-sub-info">
                                    <span class="call-check">✓</span> <span>${{timeStr}}, ${{msg.call_info.duration_formatted}}</span>
                                </div>
                            </div>
                            <div class="call-icon-badge">${{callIconSymbol}}</div>
                        </div>
                    `;
                }} else if (msg.media_path) {{
                    contentHtml = `<div class="message-media"><img src="${{msg.media_path}}" loading="lazy" onclick="window.open(this.src, '_blank')"></div>`;
                }}

                let textHtml = msg.text ? `<div class="message-text">${{escapeHtml(msg.text)}}</div>` : '';

                let reactionsHtml = '';
                if (msg.reactions && msg.reactions.length > 0) {{
                    reactionsHtml = '<div class="reactions">' + 
                        msg.reactions.map(r => `<span class="reaction-pill">${{r.reaction}} <span>${{r.count}}</span></span>`).join('') +
                    '</div>';
                }}

                const footerHtml = msg.call_info ? '' : `
                    <div style="overflow: hidden;">
                        ${{reactionsHtml}}
                        <div class="meta-footer">
                            <span class="timestamp">${{timeStr}}</span>
                        </div>
                    </div>
                `;

                row.innerHTML = `
                    ${{avatarHtml}}
                    <div class="bubble">
                        ${{!isOutbound && !msg.call_info ? `<div class="sender-name" style="color: ${{color}}">${{msg.sender_name || 'Unknown'}}</div>` : ''}}
                        ${{replyHtml}}
                        ${{contentHtml}}
                        ${{textHtml}}
                        ${{footerHtml}}
                    </div>
                `;
                container.appendChild(row);
            }});
            container.scrollTop = container.scrollHeight;
        }}

        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}

        searchToggle.addEventListener('click', () => {{
            if (searchContainer.style.display === 'block') {{
                searchContainer.style.display = 'none';
                searchBox.value = '';
                renderMessages(rawMessages);
            }} else {{
                searchContainer.style.display = 'block';
                searchBox.focus();
            }}
        }});

        searchBox.addEventListener('input', (e) => {{
            const term = e.target.value.toLowerCase();
            const filtered = rawMessages.filter(m => 
                (m.text && m.text.toLowerCase().includes(term)) || 
                (m.sender_name && m.sender_name.toLowerCase().includes(term))
            );
            renderMessages(filtered);
        }});

        renderMessages(rawMessages);
    </script>
</body>
</html>
"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)