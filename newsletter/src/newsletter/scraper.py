import time
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

DEFAULT_CONFIG = {
    "listing_selector": "a",               # Any anchor tag (override per site)
    "article_title_selector": "h1",        # Common title tag
    "article_body_selector": "article, .post-content, .blog-post",
}


class BlogScraper:
    def __init__(self, root_url, config=None, headless=True):
        self.root_url = root_url
        self.config = DEFAULT_CONFIG | (config or {})
        self.headless = headless

    def _get_html(self, url):
        """Loads dynamic JS content using Playwright."""
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=self.headless)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (compatible; NewsletterBot/1.0)"
            )
            page = context.new_page()

            logging.info(f"Loading page: {url}")
            page.goto(url, timeout=120000)
            page.wait_for_load_state("networkidle")

            html = page.content()
            browser.close()
            return html

    def extract_blog_links(self):
        """Extract article links from the root listing page."""
        html = self._get_html(self.root_url)
        soup = BeautifulSoup(html, "html.parser")
        selector = self.config["listing_selector"]

        links = set()
        for tag in soup.select(selector):
            href = tag.get("href")
            if not href:
                continue

            # Skip non-article links
            if href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
                continue

            # Convert relative → absolute URL properly
            href = urljoin(self.root_url, href)

            # First, check exclude prefixes (process exclusions first)
            exclude_prefixes = self.config.get("exclude_prefixes", [])
            if exclude_prefixes and any(href.startswith(excl_prefix) for excl_prefix in exclude_prefixes):
                continue  # Skip excluded links

            # Then filter links based on url_prefixes if provided, otherwise use old logic
            url_prefixes = self.config.get("url_prefixes", [])
            if url_prefixes:
                # Only include links that start with any of the allowed prefixes and are not the index page
                if any(href.startswith(prefix) for prefix in url_prefixes) and href != self.root_url:
                    links.add(href)
            else:
                # Fallback to old logic: contain blog/engineering and are not the index page
                if ("blog" in href or "engineering" in href) and href != self.root_url:
                    links.add(href)

        logging.info(f"Found {len(links)} article links")
        return list(links)

    def extract_article(self, url):
        """Get full article title + body."""
        html = self._get_html(url)
        soup = BeautifulSoup(html, "html.parser")

        title_sel = self.config["article_title_selector"]
        body_sel = self.config["article_body_selector"]

        title = soup.select_one(title_sel)
        title = title.get_text(strip=True) if title else "Untitled"

        body_tag = soup.select_one(body_sel)
        body = body_tag.get_text(separator="\n", strip=True) if body_tag else ""

        return {
            "url": url,
            "title": title,
            "content": body,
            "timestamp": int(time.time())
        }


# Legacy class name for backward compatibility
GenericBlogScraper = BlogScraper
