import os
import feedparser
from telegram import Bot
import asyncio
import logging
import hashlib
import requests
from urllib.parse import urlparse, urlunparse

# ================== SETTINGS ==================
TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@NBBWorld"

RSS_URLS = [
    "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://www.france24.com/en/rss",
    "https://www.reutersagency.com/feed/?best-topics=world&post_type=best"
]

MAX_NEWS_PER_FEED = 2
SENT_LINKS_FILE = "sent_links.txt"
# ==============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)

# ---------------- Helper Functions ----------------

def generate_hash(value: str) -> str:
    return hashlib.md5(value.encode()).hexdigest()

def load_sent_links() -> set:
    try:
        with open(SENT_LINKS_FILE, "r") as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()

def save_sent_links(sent_links: set):
    with open(SENT_LINKS_FILE, "w") as f:
        for link in sent_links:
            f.write(link + "\n")

def clean_link(url: str) -> str:
    """Query param-ları silərək linki təmizləyir"""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

def resolve_google_link(url: str) -> str:
    """Google News redirect-lərini həll edir"""
    try:
        if "news.google.com" in url:
            resp = requests.get(url, allow_redirects=True, timeout=5)
            return resp.url
    except Exception:
        return url
    return url

def get_unique_id(entry) -> str:
    """Duplicate protection üçün universal ID"""
    if hasattr(entry, 'id') and entry.id:
        return entry.id
    # Google News üçün redirect-i həll et və linki təmizlə
    return clean_link(resolve_google_link(entry.link))

# ---------------- Main Function ----------------

async def fetch_and_send():
    sent_links = load_sent_links()

    for rss in RSS_URLS:
        feed = feedparser.parse(rss)
        if not feed.entries:
            logging.warning(f"RSS işləmədi: {rss}")
            continue

        for entry in feed.entries[:MAX_NEWS_PER_FEED]:
            unique_id = get_unique_id(entry)
            link_hash = generate_hash(unique_id)

            if link_hash in sent_links:
                continue  # Already sent

            sent_links.add(link_hash)

            message = f"""
🌍 <b>NBB WORLD NEWS</b>

📰 <b>{entry.title}</b>

🔗 <a href="{resolve_google_link(entry.link)}">Read full article</a>
"""

            try:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=message,
                    parse_mode="HTML",
                    disable_web_page_preview=False
                )
                logging.info(f"Göndərildi: {entry.title}")

            except Exception as e:
                logging.error(f"Göndərmə xətası: {e}")

            await asyncio.sleep(2)

    save_sent_links(sent_links)

async def main():
    await fetch_and_send()

if __name__ == "__main__":
    asyncio.run(main())
