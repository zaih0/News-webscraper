"""
Improved scraper.py (GoogleNews + readability-lxml Version)

Upgrades:
    - Global news (no region filter)
    - NO LANGUAGE RESTRICTION
    - Skip paywalled / blocked articles
    - Skip articles with unusable text
    - Better text extraction + summary
"""

import os
import logging
from datetime import datetime
import mysql.connector
from dateutil import parser as dateparser
from GoogleNews import GoogleNews
import requests
from readability import Document
import re

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
NUM_ARTICLES = 20  # fetch more to avoid duplicates / bad articles
MIN_TEXT_LEN = 300  # minimum readable text required

# --------------------------
# Logging
# --------------------------
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# --------------------------
# DB
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
    urls = set(row[0] for row in cur.fetchall())
    cur.close()
    conn.close()
    return urls

def delete_oldest_n(n):
    if n <= 0:
        return
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM articles ORDER BY scraped_at ASC LIMIT %s", (n,))
    ids = [r[0] for r in cur.fetchall()]
    if ids:
        placeholders = ",".join(["%s"] * len(ids))
        sql = f"DELETE FROM articles WHERE id IN ({placeholders})"
        cur.execute(sql, ids)
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
    data = [
        (
            a["url"],
            a["title"],
            a["authors"],
            a["published_at"],
            a["summary"],
            datetime.utcnow()
        )
        for a in articles
    ]

    cur.executemany(sql, data)
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Inserted {len(articles)} new article(s).")

# --------------------------
# TEXT EXTRACTION
# --------------------------
def clean_html(html):
    return re.sub('<[^<]+?>', '', html)

def fetch_article_text(url):
    """
    Extract readable text and skip paywalled/unreadable pages.
    NO language filtering.
    """
    try:
        r = requests.get(url, timeout=10)
        if r.status_code >= 400:
            return None  # blocked

        doc = Document(r.text)
        content_html = doc.summary()
        text = clean_html(content_html).strip()

        # Skip paywalls / empty text
        if "subscribe" in text.lower() or "sign in" in text.lower():
            return None

        if len(text) < MIN_TEXT_LEN:
            return None  # not enough readable content

        summary = text[:600] + "..." if len(text) > 600 else text
        return summary

    except Exception as e:
        logger.error(f"Article extraction failed for {url}: {e}")
        return None

# --------------------------
# MAIN
# --------------------------
def main():
    logger.info("=== Starting Global Scraping Run ===")

    ensure_schema()
    existing = get_existing_urls()

    googlenews = GoogleNews(lang='en')  # language affects GoogleNews UI, not article language
    googlenews.search("Technology")
    googlenews.get_page(1)
    results = googlenews.results()[:NUM_ARTICLES]

    new_articles = []

    for art in results:
        url = art.get("link")
        if not url or url in existing:
            continue

        readable_summary = fetch_article_text(url)
        if not readable_summary:
            continue  # skip unreadable / paywalled / blocked

        title = art.get("title")
        publisher = art.get("media") or "Unknown"
        published = art.get("date")
        try:
            published_dt = dateparser.parse(published) if published else None
        except:
            published_dt = None

        new_articles.append({
            "url": url,
            "title": title,
            "authors": publisher,
            "published_at": published_dt,
            "summary": readable_summary
        })

    logger.info(f"Scraped {len(new_articles)} valid articles.")

    if new_articles:
        delete_oldest_n(len(new_articles))
        insert_articles(new_articles)

        # enforce maximum
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM articles")
        total = cur.fetchone()[0]
        cur.close()
        conn.close()

        if total > MAX_ARTICLES_TO_KEEP:
            delete_oldest_n(total - MAX_ARTICLES_TO_KEEP)

    logger.info("=== Scraping Finished ===")


if __name__ == "__main__":
    main()
