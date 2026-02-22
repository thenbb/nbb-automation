import os
import feedparser
from telegram import Bot
import asyncio
import logging
import hashlib
import requests
import subprocess  # Manual run üçün git pull

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@NBBWorld"

RSS_URLS = [
    # 🌍 WORLD NEWS
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.cnn.com/rss/edition_world.rss",
    "https://www.theguardian.com/world/rss",
    "https://feeds.skynews.com/feeds/rss/world.xml",

    # 💻 TECHNOLOGY
    "https://feeds.feedburner.com/TechCrunch/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",

    # 💰 BUSINESS
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",

    # 🔬 SCIENCE
    "https://www.sciencedaily.com/rss/top/science.xml",
    "https://www.nature.com/subjects/science.rss",
    "https://www.sciencenews.org/feed"
]

SENT_FILE = "sent_links.txt"
MAX_NEWS_PER_FEED = 2

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)

# Manual run üçün həmişə son sent_links.txt-i GitHub-dan çəkmək
def git_pull_sent_file():
    try:
        subprocess.run(["git", "pull"], check=True)
        print("Latest sent_links.txt pulled from GitHub")
    except Exception as e:
        print("Git pull failed:", e)

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
    except Exception as e:
        logging.warning(f"Link resolve error: {url} → {e}")
        return url

async def send_news(title, link, image=None):
    text = f"""🌍 <b>NBB WORLD NEWS</b>

📰 {title}

🔗 <a href="{link}">Read full article</a>
"""
    try:
        if image:
            await bot.send_photo(CHANNEL_ID, image, caption=text, parse_mode="HTML")
        else:
            await bot.send_message(CHANNEL_ID, text, parse_mode="HTML")
        logging.info(f"Sent: {title}")
    except Exception as e:
        logging.error(f"Telegram send error: {e}")

async def main():
    git_pull_sent_file()  # <-- Manual run üçün əlavə edildi
    sent = load_sent()
    print(f"Loaded {len(sent)} sent links.")

    for rss in RSS_URLS:
        print(f"Parsing RSS: {rss}")
        feed = feedparser.parse(rss)

        if not feed.entries:
            print(f"No entries found for: {rss}")
            continue

        for entry in feed.entries[:MAX_NEWS_PER_FEED]:
            link = real_link(entry.link)
            h = hashlib.md5(link.encode()).hexdigest()

            if h in sent:
                print(f"Already sent: {entry.title}")
                continue

            image = None
            if hasattr(entry, "media_content") and entry.media_content:
                image = entry.media_content[0]["url"]

            await send_news(entry.title, link, image)
            sent.add(h)
            await asyncio.sleep(2)

    save_sent(sent)
    print(f"Saved {len(sent)} total links.")

if __name__ == "__main__":
    import traceback
    try:
        print("BOT STARTING...")
        asyncio.run(main())
    except Exception as e:
        print("CRASHED!")
        traceback.print_exc()
