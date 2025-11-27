# Sources configuration for newsletter
# Separate RSS feeds and scraping targets

# RSS Feeds Section
RSS_SOURCES = [
    {"name": "google", "url": "https://developers.googleblog.com/feeds/posts/default"},
    {"name": "meta", "url": "https://engineering.fb.com/feed/"},
    {"name": "airbnb", "url": "https://medium.com/feed/airbnb-engineering"},
    {"name": "linkedin", "url": "https://engineering.linkedin.com/blog.rss.html"},
    {"name": "spotify", "url": "https://engineering.atspotify.com/feed/"},
    {"name": "dropbox", "url": "https://dropbox.tech/feed"},
    {"name": "slack", "url": "https://slack.engineering/feed"},
    {"name": "pinterest_rss", "url": "https://medium.com/feed/pinterest-engineering"},
    {"name": "microsoft", "url": "https://devblogs.microsoft.com/feed/"},
    {"name": "aws", "url": "https://aws.amazon.com/blogs/aws/feed/"},
    {"name": "github", "url": "https://github.blog/category/engineering/feed/"},
    {"name": "cloudflare", "url": "https://blog.cloudflare.com/rss/"},
    {"name": "databricks", "url": "https://www.databricks.com/feed"},
    {"name": "atlassian", "url": "https://www.atlassian.com/blog/artificial-intelligence/feed"},
    {"name": "discord", "url": "https://discord.com/blog/rss.xml"},
    {"name": "canva", "url": "https://www.canva.dev/blog/engineering/feed"},
    {"name": "doordash", "url": "https://doordash.engineering/feed/"},
    {"name": "grab", "url": "https://engineering.grab.com/feed"},
    {"name": "gitlab", "url": "https://about.gitlab.com/atom.xml"},
    {"name": "heroku", "url": "https://www.heroku.com/blog/feed/"},
    {"name": "nvidia", "url": "https://developer.nvidia.com/blog/feed/"},
    {"name": "adobe", "url": "https://medium.com/feed/adobetech"},
    {"name": "salesforce", "url": "https://engineering.salesforce.com/feed/"},
    {"name": "dropbox_security", "url": "https://dropbox.tech/security/feed"},
    {"name": "square", "url": "https://developer.squareup.com/blog/rss.xml"},
]

# Scraping Section
SCRAPING_SOURCES = [
    {
        "name": "uber",
        "base_url": "https://www.uber.com/en-IN/blog/engineering/",
        "config": {
            "article_body_selector": "div.bu.bv.j3.e5.e6.jk.ga",
            "url_prefixes": ["https://www.uber.com/en-IN/blog/"]
        }
    },
    {
        "name": "apple_ml",
        "base_url": "https://machinelearning.apple.com/highlights",
        "config": {
            "article_body_selector": "article, .post-content, .blog-post, main",
            "url_prefixes": ["https://machinelearning.apple.com/research"]
        }
    },
    {
        "name": "alphabet",
        "base_url": "https://alphabetengineering.com/blog",
        "config": {
            "url_prefixes": ["https://alphabetengineering.com/blog/"]
        }
    },
    {
        "name": "pinterest",
        "base_url": "https://medium.com/pinterest-engineering",
        "config": {
            "url_prefixes": ["https://medium.com/pinterest-engineering/"],
            "exclude_prefixes": ["https://medium.com/pinterest-engineering/subpage/"]
        }
    },
    # Add more scraping sources here as needed
    # {
    #     "name": "example",
    #     "base_url": "https://example.com/blog/",
    #     "config": {
    #         "listing_selector": ".post a",
    #         "article_title_selector": "h1.page-title",
    #         "article_body_selector": ".article-body"
    #     },
    #     "max_articles": 30,
    # },
]

# Combined sources for backward compatibility
ALL_SOURCES = [s["url"] for s in RSS_SOURCES] + [source["base_url"] for source in SCRAPING_SOURCES]
