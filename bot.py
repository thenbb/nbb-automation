import os
import feedparser
from telegram import Bot
import asyncio
import logging
import hashlib
import requests
from googletrans import Translator

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@NBBWorld"

RSS_URLS = [
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.france24.com/en/rss",
    "https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
    "http://rss.cnn.com/rss/edition_world.rss",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"
]

SENT_FILE = "sent_links.txt"
MAX_NEWS_PER_FEED = 2

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
translator = Translator()

def load_sent():
    try:
        with open(SENT_FILE, "r") as f:
            return set(f.read().splitlines())
    except:
        return set()

def save_sent(data):
    with open(SENT_FILE, "w") as f:
        for x in data:
            f.write(x + "\n")

def real_link(url):
    try:
        r = requests.get(url, timeout=10, allow_redirects=True)
        return r.url
    except:
        return url

def safe_translate(text, lang):
    try:
        return translator.translate(text, dest=lang).text
    except:
        return text

async def send_news(title, link, image=None):
    az = safe_translate(title, "az")
    ru = safe_translate(title, "ru")

    text = f"""🌍 <b>NBB WORLD NEWS</b>

📰 {title}
📰 {az}
📰 {ru}

🔗 <a href="{link}">Read full article</a>
"""

    try:
        if image:
            await bot.send_photo(CHANNEL_ID, image, caption=text, parse_mode="HTML")
        else:
            await bot.send_message(CHANNEL_ID, text, parse_mode="HTML")
    except Exception as e:
        logging.error(e)

async def main():
    sent = load_sent()

    for rss in RSS_URLS:
        feed = feedparser.parse(rss)

        for entry in feed.entries[:MAX_NEWS_PER_FEED]:
            link = real_link(entry.link)
            h = hashlib.md5(link.encode()).hexdigest()

            if h in sent:
                continue

            image = None
            if "media_content" in entry:
                image = entry.media_content[0]["url"]

            await send_news(entry.title, link, image)
            sent.add(h)
            await asyncio.sleep(2)

    save_sent(sent)

if __name__ == "__main__":
    asyncio.run(main())
