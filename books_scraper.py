"""
===============================================================================
Project: Books Web Scraping & Data Ingestion Pipeline
Author: Ranjith B (ranjithbrs)
Repository: https://github.com/ranjithbrs/books-web-scraping

Description:
  Automated, robust web scraping pipeline that extracts book catalog data
  from books.toscrape.com across 50 paginated index pages.

Features & Best Practices:
  - Robust error handling with retry logic and network timeouts.
  - Ethical rate-limiting and custom User-Agent headers.
  - Defensive DOM traversal to prevent AttributeError crashes.
  - Automated duplicate validation, null checking, and UTF-8 CSV persistence.
  - Feeds downstream exploratory data analysis in `books-data-analysis`.
===============================================================================
"""

import time
import argparse
import logging
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Configure logging for pipeline observability
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("BooksScraper")

BASE_URL = "https://books.toscrape.com/catalogue/page-{page}.html"
TOTAL_PAGES = 50
REQUEST_TIMEOUT = 10  # seconds
REQUEST_DELAY = 0.3    # polite rate-limiting delay between requests (seconds)
MAX_RETRIES = 3
DEFAULT_OUTPUT_CSV = "books_all_pages.csv"

HEADERS = {
    "User-Agent": "BooksScraperPipeline/1.0 (+https://github.com/ranjithbrs/books-web-scraping; Educational Data Pipeline)",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}


def fetch_page_with_retry(session: requests.Session, url: str, page_num: int) -> Optional[str]:
    """
    Fetches raw HTML content for a given page URL with timeout and retry handling.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                logger.warning(f"Page {page_num} returned 404 Not Found. Ending pagination.")
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
    Parses book card articles defensively from HTML DOM.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    articles = soup.find_all("article", class_="product_pod")
    page_books = []

    for article in articles:
        try:
            # 1. Title Extraction (Use full 'title' attribute if present, fallback to inner text)
            title_elem = article.find("h3").find("a") if article.find("h3") else None
            title = title_elem.get("title") or title_elem.text.strip() if title_elem else "Unknown Title"

            # 2. Price Extraction & Non-ASCII encoding cleanup
            price_elem = article.find("p", class_="price_color")
            price = price_elem.text.replace("Â", "").strip() if price_elem else "£0.00"

            # 3. Rating Extraction from star-rating class
            rating_elem = article.find("p", class_="star-rating")
            rating_classes = rating_elem.get("class", []) if rating_elem else []
            rating = rating_classes[1] if len(rating_classes) > 1 else "Unknown"

            # 4. Availability Extraction
            avail_elem = article.find("p", class_="instock availability")
            availability = avail_elem.text.strip() if avail_elem else "Unknown"

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


def validate_and_save_dataset(records: List[Dict[str, str]], output_path: str, deduplicate: bool = False) -> pd.DataFrame:
    """
    Validates extracted records, performs duplicate checking, and exports to UTF-8 CSV.
    """
    df = pd.DataFrame(records)

    logger.info("=" * 60)
    logger.info("DATASET VALIDATION & QUALITY AUDIT")
    logger.info("=" * 60)
    logger.info(f"Raw Extracted Rows: {len(df)}")

    # Check and handle duplicates based on Title
    duplicates_count = df.duplicated(subset=["Title"]).sum()
    if duplicates_count > 0:
        dupe_titles = df[df.duplicated(subset=["Title"], keep=False)]["Title"].unique().tolist()
        logger.info(f"Duplicate Detection: Found {duplicates_count} repeated title(s) across catalog pages: {dupe_titles}")
        if deduplicate:
            df.drop_duplicates(subset=["Title"], keep="first", inplace=True)
            logger.info("✓ Deduplication applied: Removed repeated entries.")
        else:
            logger.info("✓ Catalog fidelity preserved (retaining all page occurrences for downstream EDA alignment).")
    else:
        logger.info("✓ Zero duplicate titles detected. 100% unique catalog records.")

    # Check for null / missing values
    null_counts = df.isnull().sum()
    logger.info(f"Missing Values per Column:\n{null_counts.to_string()}")

    # Save to CSV with explicit UTF-8 encoding
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"✓ Validated dataset saved successfully to: {output_path}")
    logger.info(f"Final Dataset Dimensions: {df.shape[0]} rows x {df.shape[1]} columns")
    logger.info("=" * 60)
    return df


def run_pipeline(pages: int = TOTAL_PAGES, output: str = DEFAULT_OUTPUT_CSV, delay: float = REQUEST_DELAY, dedupe: bool = False):
    """
    Executes the end-to-end web scraping ingestion pipeline across all pages.
    """
    logger.info("Starting Books Web Scraping & Ingestion Pipeline...")
    logger.info(f"Target: books.toscrape.com | Total Planned Pages: {pages} | Rate Delay: {delay}s")
    start_time = time.time()

    all_books = []
    session = requests.Session()

    try:
        for page in range(1, pages + 1):
            url = BASE_URL.format(page=page)
            html = fetch_page_with_retry(session, url, page)

            if not html:
                logger.warning(f"Skipping page {page} due to fetch failure.")
                continue

            books = parse_book_articles(html, page)
            all_books.extend(books)

            if page % 10 == 0 or page == pages:
                logger.info(f"Progress: Page {page:02d}/{pages} processed | Running Total: {len(all_books)} books")

            # Respectful rate limiting delay between consecutive requests
            time.sleep(delay)

    finally:
        session.close()

    elapsed = time.time() - start_time
    logger.info(f"Scraping completed in {elapsed:.2f} seconds.")

    # Validate and persist to CSV
    validate_and_save_dataset(all_books, output, deduplicate=dedupe)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Books to Scrape automated data extraction pipeline.")
    parser.add_argument("--pages", type=int, default=TOTAL_PAGES, help="Total number of catalog pages to scrape (default: 50)")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_CSV, help="Output CSV path (default: books_all_pages.csv)")
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY, help="Delay in seconds between requests (default: 0.3)")
    parser.add_argument("--dedupe", action="store_true", help="Remove duplicate book titles from final CSV output")
    args = parser.parse_args()

    run_pipeline(pages=args.pages, output=args.output, delay=args.delay, dedupe=args.dedupe)
