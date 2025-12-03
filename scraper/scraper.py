"""
scraper.py (GoogleNews + readability-lxml + language filtering)

Requires:
    pip install GoogleNews-python readability-lxml requests mysql-connector-python python-dateutil langdetect
"""

import os
import logging
import re
from datetime import datetime

import requests
from readability import Document
from GoogleNews import GoogleNews
from dateutil import parser as dateparser
from langdetect import detect, LangDetectException
import mysql.connector


# --------------------------
# CONFIG
# --------------------------
DB_CONFIG = {
    "host": "localhost",
    "user": "admin",
    "password": "admin",
    "database": "technews"
}

MAX_ARTICLES_TO_KEEP = 50
LOG_FILE = "scraper/logs/scraper.log"

# How many EU tech articles to fetch per run
NUM_ARTICLES = 20

# EU domain whitelist (keeps content relevant to Europe)
EU_DOMAINS = [
    ".ie", ".uk", ".de", ".fr", ".it", ".es", ".nl", ".be", ".se", ".no", ".dk",
    ".pl", ".pt", ".fi", ".cz", ".sk", ".at", ".gr", ".ch", ".lu",
    ".lt", ".lv", ".ee"
]

# --------------------------
# Logging Setup
# --------------------------
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)



# --------------------------
# DB Helpers
# --------------------------
def connect_db():
    return mysql.connector.connect(**DB_CONFIG)


def ensure_schema():
    sql = """
    CREATE TABLE IF NOT EXISTS articles (
        id INT AUTO_INCREMENT PRIMARY KEY,
        url TEXT NOT NULL,
        title TEXT,
        authors TEXT,
        published_at DATETIME,
        summary TEXT,
        scraped_at DATETIME NOT NULL,
        UNIQUE KEY unique_url (url(255))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()


def get_existing_urls():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT url FROM articles")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return set(r[0] for r in rows)


def delete_oldest_n(n):
    if n <= 0:
        return
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM articles ORDER BY scraped_at ASC LIMIT %s", (n,))
    ids = [row[0] for row in cur.fetchall()]
    if ids:
        placeholders = ",".join(["%s"] * len(ids))
        query = f"DELETE FROM articles WHERE id IN ({placeholders})"
        cur.execute(query, ids)
        conn.commit()
        logger.info(f"Deleted {len(ids)} oldest article(s).")
    cur.close()
    conn.close()


def insert_articles(articles):
    if not articles:
        return
    conn = connect_db()
    cur = conn.cursor()
    sql = """
    INSERT INTO articles (url, title, authors, published_at, summary, scraped_at)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    values = []
    for a in articles:
        values.append((
            a["url"],
            a["title"],
            a["authors"],
            a["published_at"],
            a["summary"],
            datetime.utcnow()
        ))
    cur.executemany(sql, values)
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Inserted {len(articles)} new article(s).")



# --------------------------
# ARTICLE SCRAPING HELPERS
# --------------------------
def is_eu_domain(url: str) -> bool:
    """
    Ensures article comes from a European news source.
    """
    return any(url.lower().endswith(domain) for domain in EU_DOMAINS)


def fetch_article_text(url):
    """
    Fetch article main text using readability-lxml and return first ~500 chars.
    Also returns empty string if the content is not English.
    """
    try:
        response = requests.get(url, timeout=10)
        doc = Document(response.text)
        html = doc.summary()

        # Strip tags
        text = re.sub("<[^<]+?>", "", html).strip()

        if not text or len(text) < 100:
            return ""

        # Language detection
        try:
            lang = detect(text[:200])
            if lang != "en":
                logger.info(f"Skipped non-English article: {url} (lang={lang})")
                return ""
        except LangDetectException:
            return ""

        # Summarize (first 500 chars)
        summary = text[:500]
        if len(text) > 500:
            summary += "..."

        return summary.strip()

    except Exception as e:
        logger.exception(f"Error extracting text from {url}: {e}")
        return ""



# --------------------------
# MAIN SCRAPER LOGIC
# --------------------------
def main():
    logger.info("=== Starting EU GoogleNews scraping run ===")

    ensure_schema()

    googlenews = GoogleNews(lang="en", region="EU")
    googlenews.search("Technology Europe")
    googlenews.get_page(1)

    results = googlenews.results()[:NUM_ARTICLES]

    existing = get_existing_urls()
    scraped_articles = []

    for entry in results:
        url = entry.get("link")
        title = entry.get("title")
        publisher = entry.get("media") or "Unknown"
        published_raw = entry.get("date")

        if not url or url in existing:
            continue

        # Only keep articles from EU domains
        if not is_eu_domain(url):
            logger.info(f"Rejected non-EU article: {url}")
            continue

        # Parse date
        published_dt = None
        if published_raw:
            try:
                published_dt = dateparser.parse(published_raw)
            except:
                published_dt = None

        # Extract text & summary
        summary = fetch_article_text(url)
        if not summary:
            continue

        scraped_articles.append({
            "url": url,
            "title": title,
            "authors": publisher,
            "published_at": published_dt,
            "summary": summary
        })

    logger.info(f"Collected {len(scraped_articles)} EU English articles.")

    # Insert & maintain DB
    if scraped_articles:
        delete_oldest_n(len(scraped_articles))
        insert_articles(scraped_articles)

        # Enforce maximum cap
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM articles")
        total = cur.fetchone()[0]
        if total > MAX_ARTICLES_TO_KEEP:
            extra = total - MAX_ARTICLES_TO_KEEP
            logger.info(f"Trimming extra {extra} articles")
            delete_oldest_n(extra)
        cur.close()
        conn.close()

    logger.info("=== EU Scraping run complete ===")


if __name__ == "__main__":
    main()
