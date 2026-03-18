"""Detect ad platform from article title and description."""

import re

# Platform definitions: (platform_key, label, color, keyword_patterns)
# Order matters — first match wins. More specific patterns first.
PLATFORMS = [
    {
        "platform": "google-ads",
        "label": "Google Ads",
        "color": "#4285F4",
        "patterns": [
            r"google\s*ads",
            r"google\s*広告",
            r"p[\-\s]?max",
            r"performance\s*max",
            r"demand\s*gen",
            r"discovery\s*ads",
            r"shopping\s*ads",
            r"shopping\s*campaign",
            r"smart\s*bidding",
            r"responsive\s*search",
            r"\brsa\b",
            r"google\s*merchant",
            r"merchant\s*center",
            r"google\s*tag\s*manager",
            r"\bgtm\b",
            r"ga4",
            r"google\s*analytics",
            r"gclid",
            r"google\s*search\s*console",
            r"google\s*広告\s*エディター",
            r"google\s*ads\s*editor",
            r"google\s*ads\s*api",
            r"adwords",
        ],
    },
    {
        "platform": "meta-ads",
        "label": "Meta Ads",
        "color": "#1877F2",
        "patterns": [
            r"meta\s*ads",
            r"meta\s*広告",
            r"facebook\s*ads",
            r"instagram\s*ads",
            r"advantage\+",
            r"advantage\s*plus",
            r"advantage\s*shopping",
            r"meta\s*pixel",
            r"facebook\s*pixel",
            r"meta\s*capi",
            r"conversions?\s*api",
            r"meta\s*business",
            r"facebook\s*business",
            r"andromeda",
            r"meta\s*ad\s*revenue",
            r"meta\s*advertising",
            r"meta\s*attribution",
            r"meta\s*remarketing",
            r"meta\s*targeting",
            r"meta\s*budget",
            r"meta\s*campaign",
            r"meta\s*creative",
        ],
    },
    {
        "platform": "linkedin-ads",
        "label": "LinkedIn Ads",
        "color": "#0A66C2",
        "patterns": [
            r"linkedin\s*ads?",
            r"linkedin\s*広告",
            r"linkedin\s*ad\s*test",
            r"linkedin\s*campaign",
            r"linkedin\s*lead\s*gen",
            r"linkedin\s*marketing",
        ],
    },
    {
        "platform": "line-ads",
        "label": "LINE Ads",
        "color": "#06C755",
        "patterns": [
            r"line\s*ads?",
            r"line\s*広告",
            r"line\s*公式",
            r"line\s*tag",
        ],
    },
    {
        "platform": "yahoo-ads",
        "label": "Yahoo Ads",
        "color": "#FF0033",
        "patterns": [
            r"yahoo\s*ads?",
            r"yahoo\s*広告",
            r"yahoo!\s*広告",
            r"\byda\b",
            r"yahoo\s*検索広告",
            r"yahoo\s*ディスプレイ",
            r"yahoo\s*scout",
            r"yahoo\s*myscout",
        ],
    },
    {
        "platform": "microsoft-ads",
        "label": "Microsoft Ads",
        "color": "#00A4EF",
        "patterns": [
            r"microsoft\s*ads",
            r"microsoft\s*広告",
            r"microsoft\s*advertising",
            r"bing\s*ads?",
        ],
    },
    {
        "platform": "tiktok-ads",
        "label": "TikTok Ads",
        "color": "#25F4EE",
        "patterns": [
            r"tiktok\s*ads?",
            r"tiktok\s*広告",
            r"tiktok\s*campaign",
        ],
    },
]

# Source-specific default platforms (when keyword detection fails)
SOURCE_DEFAULTS = {
    # Jon Loomer = Meta specialist
    "Jon Loomer": {"platform": "meta-ads", "label": "Meta Ads", "color": "#1877F2"},
    # Ben Heath = Meta/Facebook ads
    "Ben Heath": {"platform": "meta-ads", "label": "Meta Ads", "color": "#1877F2"},
    # Dara Denney = Meta/Facebook ads
    "Dara Denney": {"platform": "meta-ads", "label": "Meta Ads", "color": "#1877F2"},
    # Solutions 8 = Google Ads agency
    "Solutions 8": {"platform": "google-ads", "label": "Google Ads", "color": "#4285F4"},
    # Aaron Young = Google Ads
    "Aaron Young": {"platform": "google-ads", "label": "Google Ads", "color": "#4285F4"},
    # Jyll Saskin Gales = Google Ads
    "Jyll Saskin Gales": {"platform": "google-ads", "label": "Google Ads", "color": "#4285F4"},
    # Loves Data = Google Analytics/Ads
    "Loves Data": {"platform": "google-ads", "label": "Google Ads", "color": "#4285F4"},
}

# Fallback for truly general/unclassifiable articles
GENERAL = {
    "platform": "general",
    "label": "General",
    "color": "#6B7280",
}


def detect_platform(title, description="", source=""):
    """Detect ad platform from article title and description.

    Returns dict with: platform, label, color
    """
    text = f"{title} {description}".lower()

    for pf in PLATFORMS:
        for pattern in pf["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                return {
                    "platform": pf["platform"],
                    "label": pf["label"],
                    "color": pf["color"],
                }

    # Check source-specific defaults
    if source in SOURCE_DEFAULTS:
        return SOURCE_DEFAULTS[source].copy()

    return GENERAL.copy()
