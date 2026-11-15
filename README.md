# Telegram Archiver

An automated, high-fidelity Telegram archiver and vault generator that exports chat histories into mobile-optimized, native-styled HTML vaults. It prioritizes absolute directory integrity, incremental synchronization, reply-threading, and strict schema standardization across diverse message types.

---

## Features

* **Strict Uniform Schema:** Normalizes all text, media, call logs, and reply interactions into a predictable JSON format.
* **Incremental Delta Synchronization:** Automatically detects local high-water marks (`_master.json`) to fetch and append only newer messages, preventing redundant network requests.
* **Forum Topic Discovery:** Automatically scans supergroups to discover forum topics and archives each sub-thread into its own isolated folder structure.
* **Native Mobile HTML Viewer:** Generates self-contained mobile web vaults featuring Telegram-styled message bubbles, date badges, interactive reply previews, media lightboxes, reaction pills, and live chat search.
* **Robust Path Resolution:** Uses absolute pathing to handle Windows environments cleanly.

---

## Project Structure

```text
telegram_retriever/
│
├── exports/
│   ├── chat_<name>/                  # Root chat archives & media
│   └── chat_<name>_topic_<id>/       # Isolated forum topic archives & media
│
├── src/
│   ├── __init__.py
│   ├── fetcher.py                    # Telethon client integration, delta fetching & topic scanning
│   └── exporter.py                   # Schema normalization, incremental merging & HTML vault generation
│
└── main.py                           # Execution runner


---

# Installation & Setup

---

## Clone or navigate to your project directory:
```text
cd C:\Users\TGPSe\Projects\telegram_retriever


---

## Install dependencies:
```text
Make sure you have Telethon installed:
pip install telethon

---

## Configure API Credentials:
```text
Open main.py and replace your Telegram api_id and api_hash:
api_id = 1234567
api_hash = 'your_api_hash'

---

## Usage
```text
Run the main synchronization script to automatically scan supergroups, discover topics, download media, and compile your HTML viewers:
python main.py

---

## JSON Message Schema

```text
Every message stored in the master archive follows this rigid schema structure:

JSON
{
    "id": 107,
    "sender_id": 987654321,
    "sender_name": "Seventh",
    "text": "all of it ends one way or another",
    "media_path": "media/img_107.jpg",
    "call_info": null,
    "reply_to_message_id": 106,
    "date": "2026-10-27 18:27:00",
    "reactions": [
        {
            "reaction": "❤️",
            "count": 1
        }
    ]
}
