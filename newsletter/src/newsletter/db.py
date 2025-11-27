import sqlite3
import os
from datetime import datetime
from common.config import DATA_DIR

DB_PATH = os.path.join(DATA_DIR, "newsletter.db")


def get_db_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create articles table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT UNIQUE NOT NULL,
            published TEXT,
            content TEXT,
            source TEXT,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
            content_fetched BOOLEAN DEFAULT FALSE,
            is_summarized BOOLEAN DEFAULT FALSE,
            telegram_sent BOOLEAN DEFAULT FALSE,
            audio_generated BOOLEAN DEFAULT FALSE,
            linkedin_posted BOOLEAN DEFAULT FALSE,
            processed_at TEXT
        )
    """
    )

    # Create summaries table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER,
            summary TEXT NOT NULL,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            provider TEXT,
            FOREIGN KEY (article_id) REFERENCES articles (id)
        )
    """
    )

    # Create processing_log table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS processing_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER,
            action TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (article_id) REFERENCES articles (id)
        )
    """
    )

    conn.commit()
    conn.close()


def insert_article(title, link, published, content, source):
    """Insert new article if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT OR IGNORE INTO articles (title, link, published, content, source)
            VALUES (?, ?, ?, ?, ?)
        """,
            (title, link, published, content, source),
        )

        article_id = cursor.lastrowid
        conn.commit()
        return article_id if cursor.rowcount > 0 else None
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        conn.close()


def get_unsummarized_articles():
    """Get articles that haven't been summarized yet."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM articles WHERE is_summarized = FALSE ORDER BY published DESC"
    )
    articles = cursor.fetchall()

    conn.close()
    return [dict(article) for article in articles]


def mark_article_summarized(article_id, summary, provider):
    """Mark article as summarized and store summary."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Update article status
        cursor.execute(
            """
            UPDATE articles
            SET is_summarized = TRUE, processed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (article_id,),
        )

        # Insert summary
        cursor.execute(
            """
            INSERT INTO summaries (article_id, summary, provider)
            VALUES (?, ?, ?)
        """,
            (article_id, summary, provider),
        )

        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()


def article_exists(link):
    """Check if article already exists by link."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM articles WHERE link = ?", (link,))
    result = cursor.fetchone()

    conn.close()
    return result is not None


def log_processing_action(article_id, action):
    """Log processing action for article."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO processing_log (article_id, action)
            VALUES (?, ?)
        """,
            (article_id, action),
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


def get_article_by_id(article_id):
    """Get article by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
    article = cursor.fetchone()

    conn.close()
    return dict(article) if article else None


def get_summary_by_article_id(article_id):
    """Get latest summary for article."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM summaries
        WHERE article_id = ?
        ORDER BY generated_at DESC
        LIMIT 1
    """,
        (article_id,),
    )

    summary = cursor.fetchone()
    conn.close()
    return dict(summary) if summary else None


def update_article_status(article_id, status_field, value=True):
    """Update specific status field for article."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"UPDATE articles SET {status_field} = ? WHERE id = ?",
            (value, article_id),
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error updating {status_field}: {e}")
        return False
    finally:
        conn.close()


def update_article_content(article_id, content):
    """Update article content and mark as content_fetched."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE articles SET content = ?, content_fetched = TRUE WHERE id = ?",
            (content, article_id),
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error updating content: {e}")
        return False
    finally:
        conn.close()


def get_all_article_urls():
    """Get all article URLs to avoid duplicates."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT link FROM articles")
    urls = cursor.fetchall()

    conn.close()
    return [url[0] for url in urls]
