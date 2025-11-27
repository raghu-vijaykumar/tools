import feedparser
import requests
import certifi
from datetime import datetime, timedelta
from .config import SOURCES
from .db import insert_article, article_exists, init_db


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


def fetch_new_articles():
    """Fetch new articles from RSS feeds and store in database."""
    init_db()  # Ensure database is initialized
    new_articles = []

    # Fetch from last 14 days to get recent content
    since_date = datetime.now() - timedelta(days=14)

    for source_url in SOURCES:
        print(f"Fetching RSS from {source_url}")
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

            # Only process recent articles
            if published < since_date:
                continue

            # Check if article already exists
            if article_exists(entry.link):
                continue  # Skip existing articles

            # Extract content from RSS
            content = (
                getattr(entry, "content", [{}])[0].get("value", "")
                if hasattr(entry, "content")
                else ""
            )

            # Insert new article into database
            article_id = insert_article(
                title=entry.title,
                link=entry.link,
                published=published.isoformat(),
                content=content,
                source=source_url,
            )

            if article_id:
                print(f"Added new article: {entry.title}")
                # Get the full article data from DB
                from .db import get_article_by_id

                article_data = get_article_by_id(article_id)
                if article_data:
                    new_articles.append(article_data)

    return new_articles
