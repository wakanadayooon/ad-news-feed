"""Generate RSS feed.xml and calendar page data from calendar.json."""

import json
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
CALENDAR_PATH = ROOT / "data" / "calendar.json"
FEED_PATH = ROOT / "docs" / "feed.xml"
CALENDAR_JS_PATH = ROOT / "docs" / "calendar-data.js"
GITHUB_PAGES_BASE = ""  # set via env var or default


def load_calendar():
    with open(CALENDAR_PATH) as f:
        return json.load(f)


def generate_rss(cal, base_url=""):
    """Generate RSS 2.0 feed.xml."""
    articles = cal["articles"][:100]  # latest 100

    items = []
    for a in articles:
        link = a.get("link", "")
        if a.get("transcript_url") and base_url:
            link = f"{base_url}/{a['transcript_url']}"
        items.append(f"""    <item>
      <title>[{escape(a.get('platform_label', ''))}] {escape(a.get('title', ''))}</title>
      <link>{escape(link)}</link>
      <description>{escape(a.get('description', '')[:500])}</description>
      <pubDate>{a.get('date', '')}T00:00:00Z</pubDate>
      <guid isPermaLink="false">{a.get('id', '')}</guid>
      <category>{escape(a.get('source', ''))}</category>
    </item>""")

    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Ad News Feed</title>
    <link>{escape(base_url)}</link>
    <description>広告プラットフォーム最新情報の自動収集フィード</description>
    <language>en</language>
    <lastBuildDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>
    <atom:link href="{escape(base_url)}/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>"""

    FEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    FEED_PATH.write_text(feed, encoding="utf-8")
    print(f"Generated feed.xml with {len(items)} items")


def generate_calendar_data(cal):
    """Generate calendar-data.js for ad-knowledge site to consume."""
    # Group articles by date
    by_date = {}
    for a in cal["articles"]:
        date = a["date"]
        if date not in by_date:
            by_date[date] = []
        by_date[date].append({
            "id": a["id"],
            "platform": a.get("platform", ""),
            "platform_label": a.get("platform_label", ""),
            "color": a.get("color", "#6B7280"),
            "title": a.get("title", ""),
            "link": a.get("link", ""),
            "source": a.get("source", ""),
            "type": a.get("type", "article"),
            "category": a.get("category", "unclassified"),
            "transcript_url": a.get("transcript_url", ""),
        })

    # Also include classification data
    classifications = cal.get("classifications", {})

    data = {
        "by_date": by_date,
        "classifications": classifications,
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    CALENDAR_JS_PATH.parent.mkdir(parents=True, exist_ok=True)
    js_content = f"const CALENDAR_DATA = {json.dumps(data, ensure_ascii=False)};"
    CALENDAR_JS_PATH.write_text(js_content, encoding="utf-8")
    print(f"Generated calendar-data.js ({len(by_date)} dates)")


def main():
    import os
    base_url = os.environ.get("GITHUB_PAGES_URL", "https://wakana-official.github.io/ad-news-feed")
    cal = load_calendar()
    generate_rss(cal, base_url)
    generate_calendar_data(cal)


if __name__ == "__main__":
    main()
