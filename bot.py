import os
import feedparser
from telegram import Bot
import asyncio
import logging
import hashlib
import requests
from bs4 import BeautifulSoup

# ================== SETTINGS ==================
TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@NBBWorld"  # Kanal username-i

RSS_URLS = [
    "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://www.france24.com/en/rss",
    "https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
    "https://rss.cnn.com/rss/cnn_topstories.rss"
]

MAX_NEWS_PER_FEED = 2
SENT_LINKS_FILE = "sent_links.txt"
# ==============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)

# ---------- Duplicate Protection ----------
def generate_hash(link):
    return hashlib.md5(link.encode()).hexdigest()

def load_sent_links():
    try:
        with open(SENT_LINKS_FILE, "r") as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()

def save_sent_links(sent_links):
    with open(SENT_LINKS_FILE, "w") as f:
        for link in sent_links:
            f.write(link + "\n")

# ---------- Google News Link Resolve ----------
def resolve_google_link(url):
    try:
        if "news.google.com" in url:
            resp = requests.get(url, allow_redirects=True, timeout=5)
            return resp.url
    except Exception:
        return url
    return url

# ---------- Get Thumbnail from link ----------
def get_thumbnail(url):
    try:
        resp = requests.get(url, timeout=5)
        soup = BeautifulSoup(resp.text, "html.parser")
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            return og_img["content"]
    except Exception:
        return None
    return None

# ---------- Get Video URL if exists ----------
def get_video_url(entry):
    # Check if media content or enclosure exists
    media_content = entry.get("media_content", [])
    if media_content:
        return media_content[0].get("url")
    enclosure = entry.get("enclosures", [])
    if enclosure:
        return enclosure[0].get("url")
    return None

# ---------- Fetch & Send ----------
async def fetch_and_send():
    sent_links = load_sent_links()

    for rss in RSS_URLS:
        feed = feedparser.parse(rss)
        if not feed.entries:
            logging.warning(f"RSS işləmədi: {rss}")
            continue

        for entry in feed.entries[:MAX_NEWS_PER_FEED]:
            # Stable link for duplicate check
            link = entry.get("link", "")
            real_link = resolve_google_link(link)
            link_hash = generate_hash(real_link)

            if link_hash in sent_links:
                continue
            sent_links.add(link_hash)

            # Try to get thumbnail
            thumbnail = get_thumbnail(real_link)
            video_url = get_video_url(entry)

            # Prepare message
            message = f"🌍 <b>NBB WORLD NEWS</b>\n\n📰 <b>{entry.title}</b>\n\n🔗 <a href='{real_link}'>Read full article</a>"

            try:
                if video_url:
                    await bot.send_video(
                        chat_id=CHANNEL_ID,
                        video=video_url,
                        caption=message,
                        parse_mode="HTML"
                    )
                else:
                    await bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=message,
                        parse_mode="HTML",
                        disable_web_page_preview=False if thumbnail else True
                    )
                logging.info(f"Göndərildi: {entry.title}")
            except Exception as e:
                logging.error(f"Göndərmə xətası: {e}")

            await asyncio.sleep(2)

    save_sent_links(sent_links)

# ---------- Main ----------
async def main():
    await fetch_and_send()

if __name__ == "__main__":
    asyncio.run(main())
