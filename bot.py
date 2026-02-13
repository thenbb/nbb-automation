import os
import feedparser
from telegram import Bot
import asyncio
import logging
import hashlib
import requests

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

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)


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
        r = requests.get(url, timeout=5, allow_redirects=True)
        return r.url
    except:
        return url


async def send_news(title, link, image=None):
    text = f"🌍 <b>NBB WORLD NEWS</b>\n\n📰 <b>{title}</b>\n\n🔗 <a href='{link}'>Read full article</a>"

    if image:
        await bot.send_photo(CHANNEL_ID, image, caption=text, parse_mode="HTML")
    else:
        await bot.send_message(CHANNEL_ID, text, parse_mode="HTML")


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

            elif "links" in entry:
                for l in entry.links:
                    if l.type.startswith("image"):
                        image = l.href

            await send_news(entry.title, link, image)

            sent.add(h)
            await asyncio.sleep(2)

    save_sent(sent)


if __name__ == "__main__":
    asyncio.run(main())
