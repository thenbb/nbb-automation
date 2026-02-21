import os
import feedparser
from telegram import Bot
import asyncio
import logging
import hashlib
import requests
import html
from googletrans import Translator  # pip install googletrans==4.0.0-rc1

# ================== SETTINGS ==================
TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@NBBWorld"

RSS_URLS = [
    "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://www.france24.com/en/rss",
    "https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
    "http://rss.cnn.com/rss/edition_world.rss"
]

SENT_FILE = "sent_links.txt"
MAX_NEWS_PER_FEED = 2
TARGET_LANGS = ["az", "ru"]  # Avtomatik tərcümə üçün dillər

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
translator = Translator()
# ==============================================

def load_sent():
    try:
        with open(SENT_FILE, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()

def save_sent(data):
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        for x in data:
            f.write(x + "\n")

def resolve_link(url):
    """Google News redirect linkləri həll et"""
    try:
        r = requests.get(url, timeout=5, allow_redirects=True)
        return r.url
    except Exception:
        return url

def generate_hash(title, link):
    """Title + link hash → duplicate protection daha stabil"""
    return hashlib.md5((title + link).encode("utf-8")).hexdigest()

async def send_news(title, link, image=None, videos=None):
    """Telegram-a göndərmə"""
    text = f"🌍 <b>NBB WORLD NEWS</b>\n\n📰 <b>{html.escape(title)}</b>\n\n🔗 <a href='{link}'>Read full article</a>"

    # Video varsa, öncə video göndər, sonra şəkil
    if videos:
        for video_url in videos:
            try:
                await bot.send_video(CHANNEL_ID, video_url, caption=text, parse_mode="HTML")
                logging.info(f"Video göndərildi: {title}")
            except Exception as e:
                logging.warning(f"Video göndərmə xətası: {e}")
    elif image:
        try:
            await bot.send_photo(CHANNEL_ID, image, caption=text, parse_mode="HTML")
            logging.info(f"Şəkil göndərildi: {title}")
        except Exception as e:
            logging.warning(f"Şəkil göndərmə xətası: {e}")
    else:
        try:
            await bot.send_message(CHANNEL_ID, text, parse_mode="HTML")
            logging.info(f"Mesaj göndərildi: {title}")
        except Exception as e:
            logging.warning(f"Mesaj göndərmə xətası: {e}")

async def main():
    sent = load_sent()

    for rss in RSS_URLS:
        feed = feedparser.parse(rss)
        if not feed.entries:
            logging.warning(f"RSS işləmədi: {rss}")
            continue

        for entry in feed.entries[:MAX_NEWS_PER_FEED]:
            link = resolve_link(entry.link)
            h = generate_hash(entry.title, link)
            if h in sent:
                continue

            # Media
            image = None
            videos = []

            if "media_content" in entry:
                for m in entry.media_content:
                    if "video" in m.get("type", ""):
                        videos.append(m.get("url"))
                    elif "image" in m.get("type", ""):
                        image = m.get("url")

            elif "links" in entry:
                for l in entry.links:
                    if l.type.startswith("image"):
                        image = l.href
                    elif "video" in l.type:
                        videos.append(l.href)

            # Avtomatik tərcümə
            for lang in TARGET_LANGS:
                try:
                    translated_title = translator.translate(entry.title, dest=lang).text
                    await send_news(translated_title, link, image=image, videos=videos)
                except Exception as e:
                    logging.warning(f"Tərcümə xətası ({lang}): {e}")

            sent.add(h)
            await asyncio.sleep(2)

    save_sent(sent)

if __name__ == "__main__":
    asyncio.run(main())
