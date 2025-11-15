import json
import os
import requests
from bs4 import BeautifulSoup
from common.llm import summarize_article
from common.config import DATA_DIR


def fetch_article_content(url):
    """Fetch article content from URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        # Try to find main content - this is heuristic
        content = ""
        # Look for common content selectors
        selectors = ["article", ".post-content", ".entry-content", ".content", "main"]
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                content = element.get_text(separator="\n", strip=True)
                break
        if not content:
            # Fallback to body text
            content = (
                soup.body.get_text(separator="\n", strip=True) if soup.body else ""
            )
        return content[:5000]  # Limit to 5000 chars
    except Exception as e:
        print(f"Error fetching content from {url}: {e}")
        return ""


def generate_markdown_article(article, date_str):
    """Generate markdown content for a single article."""
    title = article["title"]
    link = article["link"]
    published = article.get("published", "")
    summary = article.get("summary", "")
    source = article.get("source", "")

    # Get content from file if path exists, else fetch from URL
    content = ""
    content_path = article.get("content_path")
    if content_path and os.path.exists(content_path):
        with open(content_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        if html_content:
            soup = BeautifulSoup(html_content, "html.parser")
            content = soup.get_text(separator="\n", strip=True)
    if not content:
        # Fetch from URL
        content = fetch_article_content(link)

    # Create a safe filename from title
    safe_title = "".join(
        c for c in title if c.isalnum() or c in (" ", "-", "_")
    ).rstrip()
    safe_title = safe_title.replace(" ", "_").replace("-", "_")
    filename = f"{safe_title}.md"

    markdown_content = f"""# {title}

**Published:** {published}  
**Source:** {source}  
**Link:** [{link}]({link})

## Summary

{summary}

## Content

{content}
"""

    return filename, markdown_content


def generate_markdown_articles_for_date(date_str):
    """Generate markdown files for all articles for a given date."""
    date_dir = os.path.join(DATA_DIR, date_str)
    articles_file = os.path.join(date_dir, "articles.json")
    summaries_file = os.path.join(date_dir, "summaries.json")
    articles_dir = os.path.join(date_dir, "articles")

    if os.path.exists(articles_dir):
        print(f"Markdown articles already exist for {date_str}, skipping.")
        return

    if not os.path.exists(articles_file) or not os.path.exists(summaries_file):
        print(f"No articles or summaries found for {date_str}")
        return

    with open(articles_file, "r") as f:
        articles = json.load(f)

    with open(summaries_file, "r") as f:
        summaries = json.load(f)

    # Create a dict of summaries by link for quick lookup
    summaries_by_link = {s["link"]: s["summary"] for s in summaries}

    os.makedirs(articles_dir, exist_ok=True)

    for article in articles:
        try:
            # Use generated summary if available, else RSS summary
            summary = summaries_by_link.get(article["link"], article.get("summary", ""))
            article_with_summary = article.copy()
            article_with_summary["summary"] = summary
            filename, content = generate_markdown_article(
                article_with_summary, date_str
            )
            filepath = os.path.join(articles_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Generated markdown: {filename}")
        except Exception as e:
            print(f"Error generating markdown for {article['title']}: {e}")


def summarize_articles_for_date(date_str, provider="gemini"):
    """Summarize all articles for a given date."""
    date_dir = os.path.join(DATA_DIR, date_str)
    articles_file = os.path.join(date_dir, "articles.json")
    summaries_file = os.path.join(date_dir, "summaries.json")
    articles_dir = os.path.join(date_dir, "articles")

    if not os.path.exists(articles_file):
        print(f"No articles found for {date_str}")
        return []

    with open(articles_file, "r") as f:
        articles = json.load(f)

    # Load existing summaries
    summaries = []
    if os.path.exists(summaries_file):
        with open(summaries_file, "r") as f:
            summaries = json.load(f)

    # Create dict of existing summaries by link
    summaries_by_link = {s["link"]: s for s in summaries}

    os.makedirs(articles_dir, exist_ok=True)
    new_summaries = False
    for article in articles:
        # Check if markdown file already exists
        safe_title = "".join(
            c for c in article["title"] if c.isalnum() or c in (" ", "-", "_")
        ).rstrip()
        safe_title = safe_title.replace(" ", "_").replace("-", "_")
        filename = f"{safe_title}.md"
        filepath = os.path.join(articles_dir, filename)
        if os.path.exists(filepath):
            # Already generated, load summary if available
            if article["link"] not in summaries_by_link:
                # Try to extract summary from existing markdown
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    # Extract summary from markdown
                    if "## Summary\n\n" in content:
                        summary_start = content.find("## Summary\n\n") + len(
                            "## Summary\n\n"
                        )
                        summary_end = content.find("\n\n## Content", summary_start)
                        if summary_end == -1:
                            summary_end = len(content)
                        summary = content[summary_start:summary_end].strip()
                        article_summary = {
                            "title": article["title"],
                            "link": article["link"],
                            "summary": summary,
                        }
                        summaries.append(article_summary)
                        summaries_by_link[article["link"]] = article_summary
                except Exception:
                    pass  # Skip if can't extract
            continue
        try:
            print(f"Starting to summarize: {article['title']}")
            summary = summarize_article(article, provider)
            print(f"Finished summarizing: {article['title']}")
            article_summary = {
                "title": article["title"],
                "link": article["link"],
                "summary": summary,
            }
            summaries.append(article_summary)
            summaries_by_link[article["link"]] = article_summary
            new_summaries = True

            # Save summaries immediately after generating summary
            with open(summaries_file, "w") as f:
                json.dump(summaries, f, indent=2)

            # Generate markdown immediately
            article_with_summary = article.copy()
            article_with_summary["summary"] = summary
            filename, content = generate_markdown_article(
                article_with_summary, date_str
            )
            filepath = os.path.join(articles_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Summarized and generated markdown: {article['title']}")
        except Exception as e:
            print(f"Error summarizing {article['title']}: {e}")
            raise  # Re-raise to stop processing

    if new_summaries:
        print(f"Updated summaries for {date_str}")
    else:
        print(f"All articles already summarized for {date_str}, skipping.")

    return summaries


def generate_combined_articles_markdown(date_str):
    """Generate combined markdown file for all articles."""
    date_dir = os.path.join(DATA_DIR, date_str)
    articles_dir = os.path.join(date_dir, "articles")

    if not os.path.exists(articles_dir):
        print(f"No articles directory found for {date_str}")
        return

    article_files = sorted([f for f in os.listdir(articles_dir) if f.endswith(".md")])
    combined_content = ""

    for article_file in article_files:
        filepath = os.path.join(articles_dir, article_file)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        combined_content += content + "\n\n"

    # Save combined file
    combined_path = os.path.join(DATA_DIR, "articles", f"{date_str}.md")
    os.makedirs(os.path.dirname(combined_path), exist_ok=True)
    with open(combined_path, "w", encoding="utf-8") as f:
        f.write(combined_content)
    print(f"Generated combined articles markdown: {combined_path}")
