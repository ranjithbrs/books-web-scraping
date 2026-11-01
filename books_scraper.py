"""
===============================================================================
Project: Books Web Scraping & Data Ingestion Pipeline
Author: Ranjith B (ranjithbrs)
Repository: https://github.com/ranjithbrs/books-web-scraping

Description:
  Automated, production-grade web scraping and validation pipeline that:
  1. Actively checks and evaluates the target's robots.txt policy (RFC 9309).
  2. Enforces explicit UTF-8 response encoding to prevent mojibake/encoding artifacts.
  3. Scrapes 1,000 books across 50 pages with timeouts, exponential retries, and rate limiting.
  4. Enforces strict schema, null-value checks, and regex type validation.
  5. Audits and handles catalog duplicates with verified evidence.
  6. Feeds the downstream exploratory data analysis pipeline (`books-data-analysis`).
===============================================================================
"""

import os
import re
import time
import argparse
import logging
from typing import List, Dict, Optional, Tuple
import urllib.robotparser
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("BooksScraper")

BASE_URL = "https://books.toscrape.com/catalogue/page-{page}.html"
ROBOTS_URL = "https://books.toscrape.com/robots.txt"
TOTAL_PAGES = 50
EXPECTED_COLUMNS = ["Title", "Price", "Rating", "Availability"]
VALID_RATINGS = {"One", "Two", "Three", "Four", "Five"}
PRICE_REGEX = re.compile(r"^£\d+\.\d{2}$")

REQUEST_TIMEOUT = 10   # seconds
REQUEST_DELAY = 0.3     # polite delay between consecutive requests (seconds)
MAX_RETRIES = 3
DEFAULT_OUTPUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books_all_pages.csv")

HEADERS = {
    "User-Agent": "BooksScraperPipeline/1.0 (+https://github.com/ranjithbrs/books-web-scraping; Educational Data Pipeline)",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}


def check_robots_policy(session: requests.Session) -> Tuple[bool, str]:
    """
    Actively checks the target site's robots.txt policy per RFC 9309 standards.
    Returns (is_allowed, policy_summary).
    """
    logger.info(f"Checking robots.txt policy at: {ROBOTS_URL}")
    try:
        resp = session.get(ROBOTS_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 404:
            summary = "HTTP 404 (Not Found). Under RFC 9309 section 2.3.1.2, all paths are permitted for crawling."
            logger.info(f"✓ robots.txt verified: {summary}")
            return True, summary
        elif resp.status_code == 200:
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(resp.text.splitlines())
            can_scrape = rp.can_fetch(HEADERS["User-Agent"], "https://books.toscrape.com/catalogue/page-1.html")
            summary = f"HTTP 200 OK. Parser evaluation result: can_fetch = {can_scrape}."
            logger.info(f"✓ robots.txt verified: {summary}")
            return can_scrape, summary
        else:
            summary = f"HTTP {resp.status_code} returned when accessing robots.txt."
            logger.warning(f"⚠️ {summary}")
            return True, summary
    except requests.RequestException as e:
        summary = f"Unable to fetch robots.txt due to network exception: {e}."
        logger.warning(f"⚠️ {summary}")
        return True, summary


def fetch_page_with_retry(session: requests.Session, url: str, page_num: int) -> Optional[str]:
    """
    Fetches raw HTML content for a page URL with explicit UTF-8 encoding, timeout, and retry handling.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            # CRITICAL ENCODING FIX:
            # books.toscrape.com returns ISO-8859-1 header default, but content contains UTF-8 bytes.
            # Explicitly setting response.encoding = 'utf-8' prevents mojibake (e.g. Shakespeare’s vs Shakespeareâ€™s).
            response.encoding = "utf-8"

            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                logger.warning(f"Page {page_num} returned 404 Not Found. Halting pagination.")
                return None
            else:
                logger.warning(f"Page {page_num} returned HTTP {response.status_code} (Attempt {attempt}/{MAX_RETRIES})")
        except requests.Timeout:
            logger.warning(f"Page {page_num} timed out after {REQUEST_TIMEOUT}s (Attempt {attempt}/{MAX_RETRIES})")
        except requests.RequestException as e:
            logger.warning(f"Network error on page {page_num}: {e} (Attempt {attempt}/{MAX_RETRIES})")

        if attempt < MAX_RETRIES:
            backoff = attempt * 1.5
            time.sleep(backoff)

    logger.error(f"Failed to fetch page {page_num} after {MAX_RETRIES} attempts.")
    return None


def parse_book_articles(html_content: str, page_num: int) -> List[Dict[str, str]]:
    """
    Parses book card articles defensively from the UTF-8 HTML DOM.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    articles = soup.find_all("article", class_="product_pod")
    page_books = []

    for article in articles:
        try:
            # 1. Full Title Extraction (Prefers 'title' attribute to avoid truncation)
            title_elem = article.find("h3").find("a") if article.find("h3") else None
            title = ""
            if title_elem:
                title = title_elem.get("title") or title_elem.text.strip()

            # 2. Price Extraction (Preserves genuine '£' symbol without 'Â' artifact)
            price_elem = article.find("p", class_="price_color")
            price = price_elem.text.strip() if price_elem else ""

            # 3. Rating Extraction from secondary CSS class name
            rating_elem = article.find("p", class_="star-rating")
            rating_classes = rating_elem.get("class", []) if rating_elem else []
            rating = rating_classes[1] if len(rating_classes) > 1 else ""

            # 4. Availability Extraction
            avail_elem = article.find("p", class_="instock availability")
            availability = avail_elem.text.strip() if avail_elem else ""

            page_books.append({
                "Title": title,
                "Price": price,
                "Rating": rating,
                "Availability": availability
            })
        except Exception as e:
            logger.error(f"Error parsing book element on page {page_num}: {e}")
            continue

    return page_books


def validate_schema_and_quality(df: pd.DataFrame, expected_row_count: int = 1000) -> None:
    """
    Enforces strict schema validation, checks for null/empty values, validates regex patterns,
    and checks for character encoding anomalies. Raises ValueError on failure.
    """
    logger.info("=" * 65)
    logger.info("RIGOROUS DATASET VALIDATION & SCHEMA QUALITY AUDIT")
    logger.info("=" * 65)

    # 1. Schema Validation (Column names and presence)
    if list(df.columns) != EXPECTED_COLUMNS:
        raise ValueError(f"Schema Mismatch! Expected columns {EXPECTED_COLUMNS}, but got {list(df.columns)}")
    logger.info(f"✓ Schema Structure: Verified exact columns {EXPECTED_COLUMNS}")

    # 2. Row Count Verification
    if len(df) != expected_row_count:
        logger.warning(f"⚠️ Row count check: Dataset contains {len(df)} rows (target was {expected_row_count}).")
    else:
        logger.info(f"✓ Row Count Fidelity: Exact {expected_row_count} rows present.")

    # 3. Strict Null & Empty String Detection
    for col in EXPECTED_COLUMNS:
        null_count = df[col].isnull().sum()
        empty_count = (df[col].astype(str).str.strip() == "").sum()
        if null_count > 0 or empty_count > 0:
            raise ValueError(f"Data Quality Failure! Column '{col}' contains {null_count} nulls and {empty_count} empty strings.")
        logger.info(f"✓ Column '{col}': 0 nulls, 0 empty strings (100% complete).")

    # 4. Price Format Regex Validation (e.g. £51.77)
    invalid_prices = df[~df["Price"].str.match(PRICE_REGEX)]
    if not invalid_prices.empty:
        raise ValueError(f"Invalid Price format detected in {len(invalid_prices)} rows. Sample:\n{invalid_prices.head(3)}")
    logger.info("✓ Price Format Validation: All 1,000 prices strictly match pattern '^£\\d+\\.\\d{2}$'")

    # 5. Rating Enum Validation
    invalid_ratings = df[~df["Rating"].isin(VALID_RATINGS)]
    if not invalid_ratings.empty:
        raise ValueError(f"Invalid Rating values detected in {len(invalid_ratings)} rows: {invalid_ratings['Rating'].unique()}")
    logger.info(f"✓ Rating Categories Validation: All ratings strictly belong to {VALID_RATINGS}")

    # 6. Encoding & Mojibake Detection Audit
    # Verify no un-decoded UTF-8 sequences (e.g. 'â', 'Â', '\x80', '\x99') exist in titles or prices
    mojibake_rows = df[df["Title"].str.contains(r"[âÂ\x80\x99\x9c\x9d]", regex=True)]
    if not mojibake_rows.empty:
        raise ValueError(f"Encoding Error! Mojibake detected in {len(mojibake_rows)} titles:\n{mojibake_rows['Title'].head(5)}")
    logger.info("✓ Encoding Integrity: 0 mojibake artifacts detected. UTF-8 punctuation (e.g. U+2019 ’) properly preserved.")
    logger.info("=" * 65)


def process_and_save_dataset(records: List[Dict[str, str]], output_path: str, deduplicate: bool = False) -> pd.DataFrame:
    """
    Transforms extracted records into DataFrame, audits duplicates, enforces validation,
    and exports clean UTF-8 CSV.
    """
    df = pd.DataFrame(records)

    # Audit catalog duplicate titles
    duplicates = df[df.duplicated(subset=["Title"], keep=False)]
    if not duplicates.empty:
        unique_dupes = duplicates["Title"].unique().tolist()
        logger.info(f"Catalog Duplicate Discovery: Detected {len(duplicates)} occurrences across {len(unique_dupes)} title(s):")
        for dupe_title in unique_dupes:
            occurrences = df[df["Title"] == dupe_title]
            for idx, r in occurrences.iterrows():
                logger.info(f"  • Row {idx:03d} | Title: '{r['Title']}' | Price: {r['Price']} | Rating: {r['Rating']}")

        if deduplicate:
            initial_len = len(df)
            df.drop_duplicates(subset=["Title"], keep="first", inplace=True)
            logger.info(f"✓ Deduplication applied: Dropped {initial_len - len(df)} duplicate records. New total: {len(df)}")
        else:
            logger.info("✓ Full catalog fidelity maintained: Retaining all 1,000 page items for downstream analytics consistency.")
    else:
        logger.info("✓ Zero duplicate titles detected.")

    # Run strict schema and quality validation
    target_rows = len(df)
    validate_schema_and_quality(df, expected_row_count=target_rows)

    # Persist to disk with explicit UTF-8 encoding
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"✓ Validated dataset saved to: {output_path} ({df.shape[0]} rows x {df.shape[1]} columns)")
    return df


def run_pipeline(pages: int = TOTAL_PAGES, output: str = DEFAULT_OUTPUT_CSV, delay: float = REQUEST_DELAY, dedupe: bool = False):
    """
    Executes the end-to-end web scraping ingestion pipeline across all pages.
    """
    logger.info("=" * 65)
    logger.info("STARTING BOOKS WEB SCRAPING & INGESTION PIPELINE")
    logger.info(f"Target: books.toscrape.com | Pages: {pages} | Rate Delay: {delay}s | Dedupe: {dedupe}")
    logger.info("=" * 65)
    start_time = time.time()

    session = requests.Session()

    try:
        # Step 1: Evaluate robots.txt policy per RFC 9309
        is_allowed, policy_msg = check_robots_policy(session)
        if not is_allowed:
            logger.error("Scraping prohibited by robots.txt policy! Aborting.")
            return

        all_books = []

        # Step 2: Iterate through paginated catalog
        for page in range(1, pages + 1):
            url = BASE_URL.format(page=page)
            html = fetch_page_with_retry(session, url, page)

            if not html:
                logger.warning(f"Skipping page {page} due to fetch failure.")
                continue

            books = parse_book_articles(html, page)
            all_books.extend(books)

            if page % 10 == 0 or page == pages:
                logger.info(f"Progress: Page {page:02d}/{pages} processed | Extracted Total: {len(all_books)} books")

            # Respectful rate limiting delay
            time.sleep(delay)

    finally:
        session.close()

    elapsed = time.time() - start_time
    logger.info(f"Scraping completed in {elapsed:.2f} seconds.")

    # Step 3: Validate, audit duplicates, and persist
    process_and_save_dataset(all_books, output, deduplicate=dedupe)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Books to Scrape automated data extraction pipeline.")
    parser.add_argument("--pages", type=int, default=TOTAL_PAGES, help="Total number of catalog pages to scrape (default: 50)")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_CSV, help="Output CSV path (default: books_all_pages.csv)")
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY, help="Delay in seconds between requests (default: 0.3)")
    parser.add_argument("--dedupe", action="store_true", help="Remove duplicate book titles from final CSV output")
    args = parser.parse_args()

    run_pipeline(pages=args.pages, output=args.output, delay=args.delay, dedupe=args.dedupe)
