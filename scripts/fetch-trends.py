#!/usr/bin/env python3
"""
Fetch trending articles from multiple platforms and select one for review.
"""

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

JST = timezone(timedelta(hours=9))
URL_LIST_PATH = Path("url_list.md")
OUTPUT_PATH = Path(".selected_article.json")


def load_reviewed_urls() -> set[str]:
    """Load already reviewed URLs from url_list.md."""
    urls = set()
    if URL_LIST_PATH.exists():
        content = URL_LIST_PATH.read_text()
        # Extract URLs from markdown
        urls = set(re.findall(r'https?://[^\s\)]+', content))

    # Also check archive directory
    archive_dir = Path("archive")
    if archive_dir.exists():
        for f in archive_dir.glob("*.md"):
            content = f.read_text()
            urls.update(re.findall(r'https?://[^\s\)]+', content))

    return urls


def parse_datetime(dt_str: str) -> datetime:
    """Parse various datetime formats."""
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%a, %d %b %Y %H:%M:%S %z",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return datetime.now(JST)


def is_within_48h(dt: datetime) -> bool:
    """Check if datetime is within last 48 hours."""
    now = datetime.now(JST)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    return (now - dt) < timedelta(hours=48)


def fetch_zenn() -> list[dict]:
    """Fetch trending articles from Zenn."""
    print("Fetching Zenn trends...")
    try:
        resp = requests.get(
            "https://zenn.dev/api/articles",
            params={"order": "trend", "count": 20},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("articles", []):
            articles.append({
                "platform": "zenn",
                "title": item.get("title", ""),
                "url": f"https://zenn.dev{item.get('path', '')}",
                "published": parse_datetime(item.get("published_at", "")),
                "likes": item.get("liked_count", 0),
            })
        return articles
    except Exception as e:
        print(f"Error fetching Zenn: {e}")
        return []


def fetch_qiita() -> list[dict]:
    """Fetch recent articles from Qiita (sorted by likes)."""
    print("Fetching Qiita articles...")
    try:
        resp = requests.get(
            "https://qiita.com/api/v2/items",
            params={"per_page": 30},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data:
            articles.append({
                "platform": "qiita",
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "published": parse_datetime(item.get("created_at", "")),
                "likes": item.get("likes_count", 0),
            })
        # Sort by likes
        articles.sort(key=lambda x: x["likes"], reverse=True)
        return articles[:20]
    except Exception as e:
        print(f"Error fetching Qiita: {e}")
        return []


def fetch_note() -> list[dict]:
    """Fetch recommended articles from note via RSS."""
    print("Fetching note recommendations...")
    try:
        feed = feedparser.parse("https://note.com/recommend/rss")

        articles = []
        for entry in feed.entries[:20]:
            pub_date = datetime.now(JST)
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6], tzinfo=JST)

            articles.append({
                "platform": "note",
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "published": pub_date,
                "likes": 0,  # RSS doesn't include this
            })
        return articles
    except Exception as e:
        print(f"Error fetching note: {e}")
        return []


def fetch_devto() -> list[dict]:
    """Fetch top articles from Dev.to."""
    print("Fetching Dev.to top articles...")
    try:
        resp = requests.get(
            "https://dev.to/api/articles",
            params={"top": 1, "per_page": 20},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data:
            articles.append({
                "platform": "devto",
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "published": parse_datetime(item.get("published_at", "")),
                "likes": item.get("public_reactions_count", 0),
            })
        return articles
    except Exception as e:
        print(f"Error fetching Dev.to: {e}")
        return []


def fetch_hackernews() -> list[dict]:
    """Fetch top stories from Hacker News."""
    print("Fetching Hacker News top stories...")
    try:
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=10
        )
        resp.raise_for_status()
        story_ids = resp.json()[:20]

        def fetch_item(sid: int) -> dict | None:
            try:
                item_resp = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    timeout=5
                )
                item = item_resp.json()
                if item.get("url"):  # Skip text-only posts
                    return {
                        "platform": "hn",
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "published": datetime.fromtimestamp(item.get("time", 0), tz=JST),
                        "likes": item.get("score", 0),
                    }
            except requests.RequestException as e:
                print(f"Warning: Failed to fetch HN item {sid}: {e}")
            return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = executor.map(fetch_item, story_ids)
            articles = [r for r in results if r is not None]
        return articles
    except requests.RequestException as e:
        print(f"Error fetching HN: {e}")
        return []


def select_article(articles: list[dict], reviewed_urls: set[str]) -> dict | None:
    """Select the best article for review."""
    # Filter out already reviewed
    candidates = [a for a in articles if a["url"] not in reviewed_urls]

    if not candidates:
        print("No new articles found")
        return None

    # Prioritize 48h articles
    recent = [a for a in candidates if is_within_48h(a["published"])]

    if recent:
        # Sort by likes
        recent.sort(key=lambda x: x["likes"], reverse=True)
        selected = recent[0]
        print(f"Selected (48h): {selected['title']}")
    else:
        # Fall back to most popular
        candidates.sort(key=lambda x: x["likes"], reverse=True)
        selected = candidates[0]
        print(f"Selected (popular): {selected['title']}")

    return selected


def main():
    platform = os.environ.get("PLATFORM", "all")
    print(f"Target platform: {platform}")

    reviewed_urls = load_reviewed_urls()
    print(f"Found {len(reviewed_urls)} reviewed URLs")

    all_articles = []

    fetchers = {
        "zenn": fetch_zenn,
        "qiita": fetch_qiita,
        "note": fetch_note,
        "devto": fetch_devto,
        "hn": fetch_hackernews,
    }

    if platform == "all":
        for fetcher in fetchers.values():
            all_articles.extend(fetcher())
    elif platform in fetchers:
        all_articles = fetchers[platform]()
    else:
        print(f"Unknown platform: {platform}")
        sys.exit(1)

    print(f"Fetched {len(all_articles)} articles total")

    selected = select_article(all_articles, reviewed_urls)

    if selected:
        # Convert datetime to string for JSON
        output = {
            "platform": selected["platform"],
            "title": selected["title"],
            "url": selected["url"],
            "published": selected["published"].isoformat(),
            "likes": selected["likes"],
        }
        OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2))
        print(f"Saved selection to {OUTPUT_PATH}")
    else:
        print("No article selected")


if __name__ == "__main__":
    main()
