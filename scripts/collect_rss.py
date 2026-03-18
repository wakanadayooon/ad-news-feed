"""RSS feed collector — fetches new articles from all sources."""

import json
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

import yaml

from detect_platform import detect_platform

ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = ROOT / "data" / "sources.yaml"
CALENDAR_PATH = ROOT / "data" / "calendar.json"
USER_AGENT = "Mozilla/5.0 (compatible; AdNewsFeed/1.0; +https://github.com/wakanadayooon/ad-news-feed)"


def load_sources():
    with open(SOURCES_PATH) as f:
        return yaml.safe_load(f)


def load_calendar():
    if CALENDAR_PATH.exists():
        with open(CALENDAR_PATH) as f:
            return json.load(f)
    return {"articles": [], "classifications": {}}


def save_calendar(cal):
    CALENDAR_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CALENDAR_PATH, "w", encoding="utf-8") as f:
        json.dump(cal, f, ensure_ascii=False, indent=2)


def article_id(url, title):
    raw = f"{url}|{title}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def fetch_feed(url):
    """Fetch and parse an RSS/Atom feed, return list of entries."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=15) as resp:
            data = resp.read()
    except (URLError, TimeoutError) as e:
        print(f"  SKIP {url}: {e}")
        return []

    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        print(f"  SKIP {url}: XML parse error")
        return []

    entries = []
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    # RSS 2.0
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        desc = (item.findtext("description") or "").strip()
        entries.append({"title": title, "link": link, "pub_raw": pub, "description": desc})

    # Atom
    if not entries:
        for entry in root.findall(".//atom:entry", ns):
            title = (entry.findtext("atom:title", "", ns) or "").strip()
            link_el = entry.find("atom:link[@rel='alternate']", ns)
            if link_el is None:
                link_el = entry.find("atom:link", ns)
            link = link_el.get("href", "") if link_el is not None else ""
            pub = (entry.findtext("atom:published", "", ns) or
                   entry.findtext("atom:updated", "", ns) or "").strip()
            desc = (entry.findtext("atom:summary", "", ns) or
                    entry.findtext("atom:content", "", ns) or "").strip()
            entries.append({"title": title, "link": link, "pub_raw": pub, "description": desc})

    return entries


def parse_date(raw):
    """Try to parse various date formats, return YYYY-MM-DD or today."""
    for fmt in [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def collect_rss_feeds():
    sources = load_sources()
    cal = load_calendar()
    existing_ids = {a["id"] for a in cal["articles"]}
    new_count = 0

    for platform, cfg in sources.items():
        if platform == "youtube":
            continue  # handled by youtube_transcript.py

        color = cfg.get("color", "#6B7280")
        label = cfg.get("label", platform)
        feeds = cfg.get("feeds", [])

        for feed_cfg in feeds:
            name = feed_cfg["name"]
            url = feed_cfg["url"]
            lang = feed_cfg.get("lang", "en")
            print(f"Fetching: {name}")

            entries = fetch_feed(url)
            for entry in entries:
                aid = article_id(entry["link"], entry["title"])
                if aid in existing_ids:
                    continue

                date = parse_date(entry["pub_raw"])

                # For industry-media sources, detect platform from content
                art_platform = platform
                art_label = label
                art_color = color
                if platform == "industry-media":
                    detected = detect_platform(
                        entry["title"], entry["description"], name
                    )
                    art_platform = detected["platform"]
                    art_label = detected["label"]
                    art_color = detected["color"]

                article = {
                    "id": aid,
                    "platform": art_platform,
                    "platform_label": art_label,
                    "color": art_color,
                    "source": name,
                    "title": entry["title"],
                    "link": entry["link"],
                    "description": entry["description"][:300],
                    "date": date,
                    "lang": lang,
                    "type": "article",
                    "category": "unclassified",
                }
                cal["articles"].append(article)
                existing_ids.add(aid)
                new_count += 1

    # Sort by date descending
    cal["articles"].sort(key=lambda a: a["date"], reverse=True)

    # Keep last 90 days max (avoid infinite growth)
    cutoff = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ninety_days_ago = datetime(
        datetime.now().year, datetime.now().month, datetime.now().day
    )
    from datetime import timedelta
    cutoff_str = (ninety_days_ago - timedelta(days=90)).strftime("%Y-%m-%d")
    cal["articles"] = [a for a in cal["articles"] if a["date"] >= cutoff_str]

    save_calendar(cal)
    print(f"\nDone: {new_count} new articles added. Total: {len(cal['articles'])}")


if __name__ == "__main__":
    collect_rss_feeds()
