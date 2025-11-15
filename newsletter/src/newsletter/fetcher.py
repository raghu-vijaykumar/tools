import feedparser
import json
import os
import requests
import ssl
import certifi
from datetime import datetime
from .config import SOURCES, DATA_DIR, get_date_str, get_days_ago, get_start_of_day


def fetch_feed(url):
    """Fetch and parse RSS feed with proper error handling."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(
            url, headers=headers, verify=certifi.where(), timeout=10
        )
        response.raise_for_status()
        return feedparser.parse(response.content)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from {url}: {e}")
        return None


def fetch_articles(days=7):
    """Fetch articles from RSS feeds for the last 'days' days."""
    since_date = get_start_of_day(days)
    to_date = get_start_of_day(0)
    all_articles = []

    for source_url in SOURCES:
        print(f"Fetching rss from {source_url}")
        feed = fetch_feed(source_url)
        if feed is None:
            continue  # Skip this source if fetch failed

        for entry in feed.entries:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6])
            else:
                continue  # Skip if no date

            if since_date <= published < to_date:
                article = {
                    "title": entry.title,
                    "link": entry.link,
                    "published": published.isoformat(),
                    "content": (
                        getattr(entry, "content", [{}])[0].get("value", "")
                        if hasattr(entry, "content")
                        else ""
                    ),
                    "source": source_url,
                }
                all_articles.append(article)

    # Group by date
    articles_by_date = {}
    for article in all_articles:
        date_str = get_date_str(datetime.fromisoformat(article["published"]))
        if date_str not in articles_by_date:
            articles_by_date[date_str] = []
        articles_by_date[date_str].append(article)

    # Save to files
    for date_str, articles in articles_by_date.items():
        date_dir = os.path.join(DATA_DIR, date_str)
        os.makedirs(date_dir, exist_ok=True)
        content_dir = os.path.join(date_dir, "content")
        os.makedirs(content_dir, exist_ok=True)

        for article in articles:
            content = article.pop("content", "")
            if content:
                # Create safe filename
                safe_title = "".join(
                    c for c in article["title"] if c.isalnum() or c in (" ", "-", "_")
                ).rstrip()
                safe_title = safe_title.replace(" ", "_").replace("-", "_")
                content_file = os.path.join(content_dir, f"{safe_title}.txt")
                with open(content_file, "w", encoding="utf-8") as f:
                    f.write(content)
                article["content_path"] = content_file

        articles_file = os.path.join(date_dir, "articles.json")
        with open(articles_file, "w") as f:
            json.dump(articles, f, indent=2)

    return articles_by_date
