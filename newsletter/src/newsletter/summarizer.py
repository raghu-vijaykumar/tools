import requests
from bs4 import BeautifulSoup
from common.llm import summarize_article
from .db import mark_article_summarized, log_processing_action, update_article_content


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


def generate_linkedin_post_for_date(date_str, provider="gemini"):
    """Generate a LinkedIn post based on summarized articles for a given date."""
    date_dir = os.path.join(DATA_DIR, date_str)
    summaries_file = os.path.join(date_dir, "summaries.json")
    linkedin_post_file = os.path.join(date_dir, "linkedin_post.txt")

    if os.path.exists(linkedin_post_file):
        print(f"LinkedIn post already exists for {date_str}, skipping.")
        return

    if not os.path.exists(summaries_file):
        print(f"No summaries found for {date_str}")
        return

    with open(summaries_file, "r") as f:
        summaries = json.load(f)

    if not summaries:
        print(f"No summaries to generate LinkedIn post for {date_str}")
        return

    # Combine summaries into one text
    combined_summaries = ""
    for summary in summaries:
        combined_summaries += (
            f"Title: {summary['title']}\nSummary: {summary['summary']}\n\n"
        )

    # Prepare prompts
    system_prompt = """You are a technical writer creating LinkedIn posts about system design, architecture, and engineering insights.
My tone is technical, clear, and high-signal. I focus on system design, architecture, and real engineering insights.
I avoid buzzwords and corporate fluff. I sound like my own interpretation, not a copy.
I emphasize what I learned and why it matters. Posts are suitable for professionals in AI, cloud, data engineering, and software engineering.

When generating the post:
Start with a strong, scroll-stopping insight or observation
Use short paragraphs and lightweight formatting
Use numbered insights or bullets when helpful
Keep it crisp (150-220 words)
Rephrase ideas completely in my own words
No overhyped claims, no emojis unless they reinforce structure
Make it feel like my perspective, not the article's

Core structure:
Hook / observation
2-4 key takeaways
A concise insight on why it matters for practitioners
Optional: a subtle CTA like "worth reading if you work on X"

IMPORTANT:
Do not mention the article source unless I say so
Do not sound promotional
Highlight engineering tradeoffs and system design thinking
Avoid lengthy introductions"""

    user_prompt = f"Based on these summarized articles:\n\n{combined_summaries}\n\nGenerate a concise, engaging LinkedIn post following the guidelines."

    # Call LLM
    llm = get_llm(provider)
    from langchain_core.prompts import PromptTemplate

    prompt = PromptTemplate.from_template(
        "System Instructions: {system}\n\nUser: {user}\n\nLinkedIn Post:"
    )
    chain = prompt | llm
    response = chain.invoke(
        {
            "system": system_prompt,
            "user": user_prompt,
        }
    )
    linkedin_post = response.content.strip()

    # Save to file
    with open(linkedin_post_file, "w", encoding="utf-8") as f:
        f.write(linkedin_post)
    print(f"Generated LinkedIn post: {linkedin_post_file}")


def generate_linkedin_post_for_summary(
    title, summary, link, date_str, provider="gemini"
):
    """Generate a LinkedIn post for a single article summary."""
    # Prepare prompts
    system_prompt = """You are a technical writer creating LinkedIn posts about system design, architecture, and engineering insights.
My tone is technical, clear, and high-signal. I focus on system design, architecture, and real engineering insights.
I avoid buzzwords and corporate fluff. I sound like my own interpretation, not a copy.
I emphasize what I learned and why it matters. Posts are suitable for professionals in AI, cloud, data engineering, and software engineering.

When generating the post:
Start with a strong, scroll-stopping insight or observation
Use short paragraphs and lightweight formatting
Use numbered insights or bullets when helpful
Keep it crisp (150-220 words)
Rephrase ideas completely in my own words
No overhyped claims, no emojis unless they reinforce structure
Make it feel like my perspective, not the article's

Core structure:
Hook / observation
2-4 key takeaways
A concise insight on why it matters for practitioners
Optional: a subtle CTA like "worth reading if you work on X"

IMPORTANT:
Do not mention the article source unless I say so
Do not sound promotional
Highlight engineering tradeoffs and system design thinking
Avoid lengthy introductions"""

    user_prompt = f"Title: {title}\nSummary: {summary}\nLink: {link}\n\nGenerate a concise, engaging LinkedIn post following the guidelines."

    # Call LLM
    llm = get_llm(provider)
    from langchain_core.prompts import PromptTemplate

    prompt = PromptTemplate.from_template(
        "System Instructions: {system}\n\nUser: {user}\n\nLinkedIn Post:"
    )
    chain = prompt | llm
    response = chain.invoke(
        {
            "system": system_prompt,
            "user": user_prompt,
        }
    )
    linkedin_post = response.content.strip()

    return linkedin_post


def process_article(article, provider="gemini"):
    """Process a single article: fetch content, summarize, and return summary."""
    print(f"Processing article: {article['title']}")

    # Fetch full content if RSS content is insufficient
    content = article.get("content", "")
    if not content or len(content) < 200:
        print(f"Fetching full content from URL: {article['link']}")
        content = fetch_article_content(article["link"])
        if content:
            # Update content in database and mark as fetched
            update_article_content(article["id"], content)
            log_processing_action(article["id"], "content_fetched")

    # Prepare article data for summarization
    article_for_summary = {
        "title": article["title"],
        "link": article["link"],
        "content": content,  # Pass content in the content field as expected by LLM
        "published": article.get("published", ""),
        "source": article.get("source", ""),
    }

    try:
        print(f"Summarizing: {article['title']}")
        summary = summarize_article(article_for_summary, provider)
        print(f"Summary generated for: {article['title']}")

        # Mark article as summarized in DB
        success = mark_article_summarized(article["id"], summary, provider)
        if success:
            log_processing_action(article["id"], "summarized")
            print(f"Article processed and stored: {article['title']}")
            return summary
        else:
            print(f"Failed to update database for: {article['title']}")
            return None

    except Exception as e:
        print(f"Error processing article {article['title']}: {e}")
        log_processing_action(article["id"], f"error: {str(e)}")
        return None
