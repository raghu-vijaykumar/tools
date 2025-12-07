import feedparser
import requests
import certifi
import time
from datetime import datetime, timedelta
from .config import SOURCES
from .sources import RSS_SOURCES, SCRAPING_SOURCES
from .scraper import GenericBlogScraper
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


def fetch_new_articles(limit_website=None):
    """Fetch new articles from RSS feeds and scraping sources."""
    init_db()  # Ensure database is initialized
    new_articles = []

    # Fetch from last 14 days to get recent content
    since_date = datetime.now() - timedelta(days=30)

    # Get existing URLs to avoid duplicates
    from .db import get_all_article_urls

    seen_urls = set(get_all_article_urls())

    # Get processing status statistics
    from .db import get_db_connection

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN is_summarized = 0 THEN 1 ELSE 0 END) as unsummarized,
            SUM(CASE WHEN is_summarized = 1 AND telegram_sent = 0 THEN 1 ELSE 0 END) as summarized_not_sent,
            SUM(CASE WHEN telegram_sent = 1 AND audio_generated = 0 THEN 1 ELSE 0 END) as sent_no_audio,
            SUM(CASE WHEN audio_generated = 1 AND linkedin_posted = 0 THEN 1 ELSE 0 END) as audio_no_linkedin,
            SUM(CASE WHEN linkedin_posted = 1 THEN 1 ELSE 0 END) as fully_processed
        FROM articles
    """
    )
    status_counts = dict(cursor.fetchone())
    conn.close()

    # Statistics tracking
    stats = {
        "existing_articles": len(seen_urls),
        "processing_status": status_counts,
        "rss": {
            "total_entries": 0,
            "recent_filtered": 0,
            "duplicates": 0,
            "length_filtered": 0,
            "added": 0,
        },
        "scraping": {
            "total_links": 0,
            "duplicates": 0,
            "length_filtered": 0,
            "added": 0,
        },
    }

    # Filter sources based on limit_website
    rss_sources_to_use = RSS_SOURCES
    scraping_sources_to_use = SCRAPING_SOURCES

    if limit_website:
        if limit_website in [s["name"] for s in SCRAPING_SOURCES]:
            # Only scrape the specified website
            scraping_sources_to_use = [
                s for s in SCRAPING_SOURCES if s["name"] == limit_website
            ]
            rss_sources_to_use = []
        elif limit_website in [s["name"] for s in RSS_SOURCES]:
            # Only use RSS sources with matching name
            rss_sources_to_use = [s for s in RSS_SOURCES if s["name"] == limit_website]
            scraping_sources_to_use = []
        else:
            print(f"Website '{limit_website}' not found in sources. Using all sources.")

    # Fetch from RSS sources
    for source in rss_sources_to_use:
        source_url = source["url"]
        print(f"Fetching RSS from {source['name']}: {source_url}")
        feed = fetch_feed(source_url)
        if feed is None:
            continue  # Skip this source if fetch failed

        for entry in feed.entries:
            stats["rss"]["total_entries"] += 1
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6])
            else:
                continue  # Skip if no date

            # Only process recent articles
            if published < since_date:
                stats["rss"]["recent_filtered"] += 1
                continue

            # Check if article already exists
            if article_exists(entry.link):
                stats["rss"]["duplicates"] += 1
                continue  # Skip existing articles

            # Extract content from RSS
            content = (
                getattr(entry, "content", [{}])[0].get("value", "")
                if hasattr(entry, "content")
                else ""
            )

            # Skip articles with insufficient content
            if len(content) < 1000:
                stats["rss"]["length_filtered"] += 1
                continue

            # Insert new article into database
            article_id = insert_article(
                title=entry.title,
                link=entry.link,
                published=published.isoformat(),
                content=content,
                source=source_url,
            )

            if article_id:
                stats["rss"]["added"] += 1
                print(f"Added new article: {entry.title}")
                # Get the full article data from DB
                from .db import get_article_by_id

                article_data = get_article_by_id(article_id)
                if article_data:
                    new_articles.append(article_data)

    # Fetch from scraping sources
    for scraping_config in scraping_sources_to_use:
        print(f"Scraping from {scraping_config['name']}: {scraping_config['base_url']}")
        try:
            scraper = GenericBlogScraper(
                root_url=scraping_config["base_url"],
                config=scraping_config.get("config"),
                headless=True,
            )

            # Extract all blog links from the index page
            all_links = scraper.extract_blog_links()
            stats["scraping"]["total_links"] += len(all_links)

            for link in all_links:
                if link in seen_urls:
                    stats["scraping"]["duplicates"] += 1
                    continue

                # Check if article is already summarized before loading content
                from .db import get_article_by_url
                existing_article = get_article_by_url(link)

                if existing_article and existing_article.get("is_summarized"):
                    stats["scraping"]["duplicates"] += 1  # Count as duplicate since already summarized
                    print(f"Skipping already summarized article: {link}")
                    continue

                # Extract full article content
                article_data = scraper.extract_article(link)

                # Skip articles with insufficient content
                if len(article_data.get("content", "")) < 1000:
                    stats["scraping"]["length_filtered"] += 1
                    continue

                # Insert scraped article into database
                article_id = insert_article(
                    title=article_data["title"],
                    link=article_data["url"],
                    published="",  # Will be parsed later if needed
                    content=article_data.get("content", ""),
                    source=scraping_config["base_url"],
                )

                if article_id:
                    stats["scraping"]["added"] += 1
                    # Get the full article data from DB
                    from .db import get_article_by_id

                    db_article_data = get_article_by_id(article_id)
                    if db_article_data:
                        new_articles.append(db_article_data)

                time.sleep(1.0)  # polite delay

        except Exception as e:
            print(f"Error scraping {scraping_config['name']}: {e}")
            continue

    # Print statistics summary
    print("\n=== FETCHING STATISTICS ===")
    print(f"Existing articles in DB: {stats['existing_articles']}")
    print(f"\nRSS Sources:")
    print(f"  Total entries processed: {stats['rss']['total_entries']}")
    print(f"  Filtered (too old): {stats['rss']['recent_filtered']}")
    print(f"  Filtered (duplicates): {stats['rss']['duplicates']}")
    print(f"  Filtered (insufficient content): {stats['rss']['length_filtered']}")
    print(f"  Articles added: {stats['rss']['added']}")
    print(f"\nScraping Sources:")
    print(f"  Total links found: {stats['scraping']['total_links']}")
    print(f"  Filtered (duplicates): {stats['scraping']['duplicates']}")
    print(f"  Filtered (insufficient content): {stats['scraping']['length_filtered']}")
    print(f"  Articles added: {stats['scraping']['added']}")
    print(f"\nTotal new articles added: {len(new_articles)}")
    print("=" * 30)

    return new_articles
