"""Re-classify existing calendar.json articles by content platform.

One-time migration script. Run from scripts/ directory.
"""

import json
from pathlib import Path
from detect_platform import detect_platform

ROOT = Path(__file__).resolve().parent.parent
CALENDAR_PATH = ROOT / "data" / "calendar.json"

# Official source platforms (these keep their original classification)
OFFICIAL_PLATFORMS = {
    "google-ads", "meta-ads", "yahoo-ads",
    "linkedin-ads", "line-ads", "microsoft-ads",
}

# Updated labels for official platforms
LABEL_MAP = {
    "google-ads": ("Google Ads", "#4285F4"),
    "meta-ads": ("Meta Ads", "#1877F2"),
    "yahoo-ads": ("Yahoo Ads", "#FF0033"),
    "linkedin-ads": ("LinkedIn Ads", "#0A66C2"),
    "line-ads": ("LINE Ads", "#06C755"),
    "microsoft-ads": ("Microsoft Ads", "#00A4EF"),
}


def reclassify():
    with open(CALENDAR_PATH) as f:
        cal = json.load(f)

    stats = {"updated": 0, "label_updated": 0, "total": len(cal["articles"])}

    for article in cal["articles"]:
        old_platform = article.get("platform", "")
        old_label = article.get("platform_label", "")

        # Update labels for official platforms
        if old_platform in LABEL_MAP:
            new_label, new_color = LABEL_MAP[old_platform]
            if article["platform_label"] != new_label:
                article["platform_label"] = new_label
                article["color"] = new_color
                stats["label_updated"] += 1
            continue

        # Re-classify industry-media and youtube articles
        if old_platform in ("industry-media", "youtube"):
            detected = detect_platform(
                article.get("title", ""),
                article.get("description", ""),
                article.get("source", ""),
            )
            article["platform"] = detected["platform"]
            article["platform_label"] = detected["label"]
            article["color"] = detected["color"]

            if detected["platform"] != old_platform or detected["label"] != old_label:
                stats["updated"] += 1
                print(f"  [{old_label}] → [{detected['label']}] {article['title'][:60]}")

    with open(CALENDAR_PATH, "w", encoding="utf-8") as f:
        json.dump(cal, f, ensure_ascii=False, indent=2)

    print(f"\nDone: {stats['updated']} reclassified, "
          f"{stats['label_updated']} labels updated, "
          f"{stats['total']} total articles")


if __name__ == "__main__":
    reclassify()
