import feedparser
from telegram import Bot
import asyncio
import logging
import os

# ================== SETTINGS ==================
TOKEN = os.environ.get("BOT_TOKEN")  # GitHub Secrets-dən oxunur
CHANNEL_ID = "@NBBWorld"             # Kanal username-i
SENT_LINKS_FILE = "sent_links.txt"   # Göndərilmiş linkləri saxlamaq üçün

RSS_URLS = [
    "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://www.france24.com/en/rss",
    "https://www.reutersagency.com/feed/?best-topics=world&post_type=best"
]

MAX_NEWS_PER_FEED = 3
# ==============================================

bot = Bot(token=TOKEN)
logging.basicConfig(level=logging.INFO)

async def fetch_and_send():
    try:
        with open(SENT_LINKS_FILE, "r") as f:
            sent_links = set(f.read().splitlines())
    except FileNotFoundError:
        sent_links = set()

    for rss in RSS_URLS:
        feed = feedparser.parse(rss)
        if not feed.entries:
            logging.warning(f"RSS işləmədi: {rss}")
            continue
        for entry in feed.entries[:MAX_NEWS_PER_FEED]:
            if entry.link in sent_links:
                continue
            sent_links.add(entry.link)
            message = f"📰 {entry.title}\n🔗 {entry.link}"
            try:
                await bot.send_message(chat_id=CHANNEL_ID, text=message)
                logging.info(f"Göndərildi: {entry.title}")
            except Exception as e:
                logging.error(f"Xəta göndərərkən: {e}")
            await asyncio.sleep(2)

    with open(SENT_LINKS_FILE, "w") as f:
        for link in sent_links:
            f.write(link + "\n")

async def main():
    while True:
        await fetch_and_send()
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(main())
