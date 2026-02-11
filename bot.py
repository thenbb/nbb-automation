import os
import feedparser
from telegram import Bot
import asyncio
import logging

# ================== SETTINGS ==================
TOKEN = os.environ.get("BOT_TOKEN")  # GitHub Secrets-dən
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
    # Əvvəlki linkləri yüklə
    try:
        with open(SENT_LINKS_FILE, "r") as f:
            sent_links = set(f.read().splitlines())
    except FileNotFoundError:
        sent_links = set()

    # TEST mesajı → dərhal yoxlamaq üçün
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text="💡 TEST MESAJI")
        logging.info("TEST MESAJI göndərildi ✅")
    except Exception as e:
        logging.error(f"TEST mesajı xəta: {e}")

    # RSS xəbərləri
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

    # Göndərilmiş linkləri saxla
    with open(SENT_LINKS_FILE, "w") as f:
        for link in sent_links:
            f.write(link + "\n")

async def main():
    await fetch_and_send()

if __name__ == "__main__":
    asyncio.run(main())
