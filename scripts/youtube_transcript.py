"""YouTube transcript collector — fetches subtitles and generates summaries."""

import json
import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError
from html import unescape

import yaml

from detect_platform import detect_platform

ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = ROOT / "data" / "sources.yaml"
CALENDAR_PATH = ROOT / "data" / "calendar.json"
TRANSCRIPTS_DIR = ROOT / "docs" / "transcripts"
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
    with open(CALENDAR_PATH, "w", encoding="utf-8") as f:
        json.dump(cal, f, ensure_ascii=False, indent=2)


def article_id(url, title):
    raw = f"{url}|{title}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def fetch_youtube_rss(channel_id):
    """Fetch recent videos from YouTube channel RSS."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=15) as resp:
            data = resp.read()
    except (URLError, TimeoutError) as e:
        print(f"  SKIP channel {channel_id}: {e}")
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }

    root = ET.fromstring(data)
    entries = []
    for entry in root.findall("atom:entry", ns):
        video_id = entry.findtext("yt:videoId", "", ns)
        title = entry.findtext("atom:title", "", ns)
        published = entry.findtext("atom:published", "", ns)
        media_group = entry.find("media:group", ns)
        description = ""
        if media_group is not None:
            description = media_group.findtext("media:description", "", ns) or ""
        entries.append({
            "video_id": video_id,
            "title": title,
            "published": published,
            "description": description[:300],
            "link": f"https://www.youtube.com/watch?v={video_id}",
        })
    return entries


def fetch_subtitles(video_id):
    """Fetch auto-generated English subtitles for a YouTube video."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (URLError, TimeoutError):
        return None

    # Extract captions URL from page source
    caption_match = re.search(r'"captionTracks":\[.*?"baseUrl":"(.*?)"', html)
    if not caption_match:
        return None

    caption_url = caption_match.group(1).replace("\\u0026", "&")
    # Prefer English
    if "lang=en" not in caption_url:
        en_match = re.search(
            r'"captionTracks":\[.*?"baseUrl":"(.*?lang=en.*?)"', html
        )
        if en_match:
            caption_url = en_match.group(1).replace("\\u0026", "&")

    req2 = Request(caption_url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req2, timeout=15) as resp:
            caption_xml = resp.read()
    except (URLError, TimeoutError):
        return None

    try:
        root = ET.fromstring(caption_xml)
    except ET.ParseError:
        return None

    texts = []
    for text_el in root.findall(".//text"):
        t = text_el.text or ""
        t = unescape(t).strip()
        if t:
            texts.append(t)

    return " ".join(texts) if texts else None


def summarize_text(text):
    """Summarize using Hugging Face transformers (facebook/bart-large-cnn)."""
    try:
        from transformers import pipeline
        summarizer = pipeline(
            "summarization",
            model="facebook/bart-large-cnn",
            device=-1,  # CPU
        )
        # BART max input is ~1024 tokens, truncate to ~3000 chars
        truncated = text[:3000]
        result = summarizer(
            truncated,
            max_length=200,
            min_length=50,
            do_sample=False,
        )
        return result[0]["summary_text"]
    except ImportError:
        print("  transformers not installed, using fallback summary")
        return fallback_summary(text)
    except Exception as e:
        print(f"  Summarization error: {e}, using fallback")
        return fallback_summary(text)


def fallback_summary(text):
    """Extract the most keyword-dense paragraph as summary."""
    ad_keywords = [
        "campaign", "ads", "bidding", "conversion", "targeting", "audience",
        "budget", "performance", "creative", "optimization", "update",
        "feature", "new", "change", "launch", "strategy", "ROAS", "CPA",
        "click", "impression", "search", "display", "video", "shopping",
        "pmax", "demand gen", "remarketing", "pixel", "tag", "tracking",
    ]

    sentences = re.split(r'[.!?]\s+', text)
    # Group into chunks of 3 sentences
    chunks = []
    for i in range(0, len(sentences), 3):
        chunk = ". ".join(sentences[i:i+3])
        if len(chunk) > 50:
            chunks.append(chunk)

    if not chunks:
        return text[:500]

    # Score each chunk by keyword density
    best_chunk = ""
    best_score = -1
    for chunk in chunks:
        lower = chunk.lower()
        score = sum(1 for kw in ad_keywords if kw in lower)
        if score > best_score:
            best_score = score
            best_chunk = chunk

    return best_chunk[:500]


def generate_transcript_page(video_id, title, channel_name, summary, full_text, date):
    """Generate an HTML page for the transcript."""
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - Transcript</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; color: #333; line-height: 1.7; }}
h1 {{ font-size: 1.4rem; }}
.meta {{ color: #666; font-size: 0.9rem; margin-bottom: 1.5rem; }}
.summary {{ background: #f0f7ff; border-left: 4px solid #4285f4; padding: 1rem; margin: 1.5rem 0; border-radius: 4px; }}
.summary h2 {{ margin-top: 0; font-size: 1.1rem; }}
details {{ margin-top: 1.5rem; }}
summary {{ cursor: pointer; font-weight: bold; font-size: 1.1rem; padding: 0.5rem 0; }}
.full-text {{ white-space: pre-wrap; font-size: 0.95rem; line-height: 1.8; }}
a {{ color: #4285f4; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="meta">
  <strong>{channel_name}</strong> | {date} |
  <a href="https://www.youtube.com/watch?v={video_id}" target="_blank">Watch on YouTube</a>
</div>
<div class="summary">
  <h2>Summary</h2>
  <p>{summary}</p>
</div>
<details>
  <summary>Full Transcript</summary>
  <div class="full-text">{full_text}</div>
</details>
</body>
</html>"""
    path = TRANSCRIPTS_DIR / f"{video_id}.html"
    path.write_text(html, encoding="utf-8")
    return f"transcripts/{video_id}.html"


def collect_youtube():
    sources = load_sources()
    cal = load_calendar()
    existing_ids = {a["id"] for a in cal["articles"]}
    yt_cfg = sources.get("youtube", {})
    channels = yt_cfg.get("channels", [])
    new_count = 0

    for ch in channels:
        name = ch["name"]
        channel_id = ch["channel_id"]
        lang = ch.get("lang", "en")
        print(f"YouTube: {name}")

        entries = fetch_youtube_rss(channel_id)
        for entry in entries[:3]:  # latest 3 videos per channel
            aid = article_id(entry["link"], entry["title"])
            if aid in existing_ids:
                continue

            date = entry["published"][:10] if entry["published"] else datetime.now(timezone.utc).strftime("%Y-%m-%d")

            # Fetch subtitles
            print(f"  Fetching subtitles: {entry['title'][:50]}...")
            subtitles = fetch_subtitles(entry["video_id"])
            transcript_url = ""

            if subtitles:
                summary = summarize_text(subtitles)
                transcript_url = generate_transcript_page(
                    entry["video_id"], entry["title"], name,
                    summary, subtitles, date
                )
                description = summary
            else:
                print(f"  No subtitles available")
                description = entry["description"][:300]

            # Detect platform from video title and description
            detected = detect_platform(
                entry["title"], description, name
            )

            article = {
                "id": aid,
                "platform": detected["platform"],
                "platform_label": detected["label"],
                "color": detected["color"],
                "source": name,
                "title": entry["title"],
                "link": entry["link"],
                "description": description,
                "date": date,
                "lang": lang,
                "type": "youtube",
                "category": "unclassified",
                "transcript_url": transcript_url,
            }
            cal["articles"].append(article)
            existing_ids.add(aid)
            new_count += 1

    cal["articles"].sort(key=lambda a: a["date"], reverse=True)
    save_calendar(cal)
    print(f"\nYouTube: {new_count} new videos added.")


if __name__ == "__main__":
    collect_youtube()
