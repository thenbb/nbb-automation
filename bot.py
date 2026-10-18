
import os
import re
import html
import hashlib
import logging
import asyncio
from urllib.parse import (
    urlsplit, urlunsplit, parse_qsl, urlencode
)

import feedparser
import requests
from telegram import Bot
from telegram.error import TelegramError

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@NBBWorld")

SENT_FILE = "sent_links.txt"
MAX_NEWS_PER_RUN = 5
MAX_NEWS_PER_FEED = 2
MAX_SENT_HISTORY = 5000
REQUEST_TIMEOUT = 12

RSS_URLS = [
    # WORLD NEWS
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.cnn.com/rss/edition_world.rss",
    "https://www.theguardian.com/world/rss",
    "https://feeds.skynews.com/feeds/rss/world.xml",

    # TECHNOLOGY
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",

    # BUSINESS
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",

    # SCIENCE
    "https://www.sciencedaily.com/rss/top/science.xml",
    "https://www.nature.com/subjects/science.rss",
    "https://www.sciencenews.org/feed",
]

IMPORTANT_KEYWORDS = {
    "world", "global", "government", "president",
    "prime minister", "election", "war", "conflict",
    "attack", "ceasefire", "military", "sanction",
    "crisis", "earthquake", "flood", "wildfire",
    "storm", "climate", "economy", "inflation",
    "interest rate", "central bank", "market", "trade",
    "business", "technology", "artificial intelligence",
    "cyber", "security", "research", "science", "health",
    "space", "energy", "oil", "gas", "bank", "company",
    "court", "law", "policy", "minister", "diplomacy",
    "nato", "united nations", "ukraine", "russia",
    "china", "united states", "middle east",
}

LOW_VALUE_KEYWORDS = {
    "horoscope", "crossword", "recipe",
    "celebrity style", "shopping guide", "best deals",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("NBB")


def clean_url(url):
    try:
        parts = urlsplit(url.strip())

        tracking = {
            "fbclid", "gclid", "mc_cid", "mc_eid",
            "ref", "ref_src", "utm_source", "utm_medium",
            "utm_campaign", "utm_term", "utm_content",
        }

        query = [
            (key, value)
            for key, value in parse_qsl(
                parts.query, keep_blank_values=True
            )
            if key.lower() not in tracking
        ]

        path = re.sub(r"/+$", "", parts.path) or "/"

        return urlunsplit((
            parts.scheme.lower(),
            parts.netloc.lower(),
            path,
            urlencode(query, doseq=True),
            "",
        ))

    except Exception:
        return url.strip()


def article_keys(url, title):
    normalized_url = clean_url(url)

    normalized_title = re.sub(
        r"[^a-z0-9]+", " ", title.lower()
    ).strip()

    url_key = "url:" + hashlib.sha256(
        normalized_url.encode("utf-8")
    ).hexdigest()

    title_key = "title:" + hashlib.sha256(
        normalized_title.encode("utf-8")
    ).hexdigest()

    return url_key, title_key


def load_sent():
    try:
        with open(SENT_FILE, "r", encoding="utf-8") as file:
            return {
                line.strip()
                for line in file
                if line.strip()
            }

    except FileNotFoundError:
        return set()

    except OSError:
        log.exception("Could not read sent history")
        raise


def save_sent(sent):
    values = list(sent)[-MAX_SENT_HISTORY:]
    temporary_file = SENT_FILE + ".tmp"

    with open(temporary_file, "w", encoding="utf-8") as file:
        if values:
            file.write("\n".join(values) + "\n")

    os.replace(temporary_file, SENT_FILE)


def resolve_link(url):
    url = clean_url(url)

    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            headers={"User-Agent": "NBBNewsBot/1.0"},
        )
        response.raise_for_status()
        return clean_url(response.url)

    except requests.RequestException as error:
        log.warning("Link resolution failed: %s", error)
        return url


def entry_image(entry):
    try:
        for field in ("media_content", "media_thumbnail"):
            items = entry.get(field) or []

            if items and items[0].get("url"):
                return items[0]["url"]

        for link in entry.get("links", []):
            if (
                link.get("type", "").startswith("image/")
                and link.get("href")
            ):
                return link["href"]

        for field in ("summary", "description"):
            match = re.search(
                r'<img[^>]+src=["\']([^"\']+)["\']',
                str(entry.get(field, "")),
                re.I,
            )

            if match:
                return html.unescape(match.group(1))

    except Exception:
        log.exception("Image extraction failed")

    return None


def is_relevant(title, summary=""):
    text = (title + " " + summary).lower()

    if len(title.strip()) < 25:
        return False

    if any(word in text for word in LOW_VALUE_KEYWORDS):
        return False

    return any(
        word in text for word in IMPORTANT_KEYWORDS
    )


def fetch_candidates():
    candidates = []

    for rss in RSS_URLS:
        log.info("Reading RSS: %s", rss)

        try:
            feed = feedparser.parse(
                rss,
                request_headers={
                    "User-Agent": "NBBNewsBot/1.0"
                },
            )

            if getattr(feed, "bozo", False):
                log.warning("RSS parsing warning: %s", rss)

            if not feed.entries:
                log.warning("No entries found: %s", rss)
                continue

            accepted = 0

            for entry in feed.entries:
                title = str(entry.get("title", "")).strip()
                link = str(entry.get("link", "")).strip()

                summary = re.sub(
                    r"<[^>]+>", " ",
                    str(entry.get("summary", "")),
                )
                summary = re.sub(
                    r"\s+", " ",
                    html.unescape(summary),
                ).strip()

                if not title or not link:
                    continue

                if not is_relevant(title, summary):
                    log.info("Filtered: %s", title)
                    continue

                candidates.append({
                    "title": title,
                    "link": link,
                    "image": entry_image(entry),
                })

                accepted += 1

                if accepted >= MAX_NEWS_PER_FEED:
                    break

        except Exception:
            log.exception("RSS feed failed: %s", rss)

    return candidates


async def send_news(bot, title, link, image=None):
    message = (
        "🌍 <b>NBB WORLD NEWS</b>\n\n"
        f"📰 {html.escape(title.strip())}\n\n"
        f'🔗 <a href="{html.escape(link, quote=True)}">'
        "Read full article</a>"
    )

    try:
        if image:
            try:
                await bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=image,
                    caption=message,
                    parse_mode="HTML",
                )
                return True

            except TelegramError:
                log.exception("Photo failed; trying text")

        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode="HTML",
        )

        return True

    except TelegramError:
        log.exception("Telegram delivery failed: %s", title)
        return False

    except Exception:
        log.exception("Unexpected delivery error: %s", title)
        return False


async def main():
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing from GitHub Secrets."
        )

    sent = load_sent()
    log.info("Loaded %d history keys", len(sent))

    candidates = fetch_candidates()
    unique = []
    current_run_keys = set()
       
    for item in candidates:
        original_link = item["link"]
        link = resolve_link(original_link)

        url_key, title_key = article_keys(
            link, item["title"]
        )

        legacy_keys = {
            hashlib.md5(link.encode("utf-8")).hexdigest(),
            hashlib.md5(clean_url(link).encode("utf-8")).hexdigest(),
            hashlib.md5(original_link.encode("utf-8")).hexdigest(),
            hashlib.md5(clean_url(original_link).encode("utf-8")).hexdigest(),
        }

        keys = {url_key, title_key, *legacy_keys}

        if keys.intersection(sent):
            log.info("Already sent: %s", item["title"])
            continue

        if keys.intersection(current_run_keys):
            log.info("Duplicate in this run: %s", item["title"])
            continue

        item["link"] = link
        item["keys"] = keys
        unique.append(item)
        current_run_keys.update(keys)

    posted = 0

    async with Bot(token=TOKEN) as bot:
        for item in unique:
            if posted >= MAX_NEWS_PER_RUN:
                break

            success = await send_news(
                bot,
                item["title"],
                item["link"],
                item["image"],
            )

            if success:
                sent.update(item["keys"])
                save_sent(sent)
                posted += 1

                log.info("Posted: %s", item["title"])
                await asyncio.sleep(2)

            else:
                log.error(
                    "Not saved because delivery failed: %s",
                    item["title"],
                )

    log.info("Run complete. Posted: %d", posted)


if __name__ == "__main__":
    asyncio.run(main())
