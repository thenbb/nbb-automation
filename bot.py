import os
import feedparser
from telegram import Bot
import asyncio
import logging
import hashlib

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
# ==============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)

sent_links = set()

def generate_hash(link):
    return hashlib.md5(link.encode()).hexdigest()

async def fetch_and_send():
    global sent_links

    for rss in RSS_URLS:
        feed = feedparser.parse(rss)

        if not feed.entries:
            logging.warning(f"RSS işləmədi: {rss}")
            continue

        for entry in feed.entries[:MAX_NEWS_PER_FEED]:
            link_hash = generate_hash(entry.link)

            if link_hash in sent_links:
                continue

            sent_links.add(link_hash)

            message = f"""
🌍 <b>NBB WORLD NEWS</b>

📰 <b>{entry.title}</b>

🔗 <a href="{entry.link}">Read full article</a>
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

async def main():
    await fetch_and_send()

if __name__ == "__main__":
    asyncio.run(main())
