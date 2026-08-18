# Books Web Scraping

## Project Overview

A Python web scraping project that collects book information from [Books to Scrape](https://books.toscrape.com/).

The scraper collects data from all 50 pages of the website and stores information about 1,000 books in a CSV file.

This project was built to learn and practice web scraping, pagination, HTML parsing, data cleaning, Pandas, CSV data handling, and basic data validation.

## Technologies Used

- Python
- Requests
- BeautifulSoup
- Pandas

## Data Collected

For each book, the following information is collected:

- Title
- Price
- Rating
- Availability

## Scraping Process

```text
Website
   ↓
Requests
   ↓
HTML Response
   ↓
BeautifulSoup
   ↓
Find book containers
   ↓
Extract book data
   ↓
Pagination (50 pages)
   ↓
Data Validation
   ↓
Pandas DataFrame
   ↓
CSV
```

## Pagination

The website contains 50 pages with 20 books per page.

The scraper generates page URLs dynamically:

```python
for page in range(1, 51):
    url = f"https://books.toscrape.com/catalogue/page-{page}.html"
```

Python's `range()` excludes the ending value, so `range(1, 51)` processes pages 1 through 50.

The `books` list is initialized outside the pagination loop so that data from all pages can be stored together.

## HTML Parsing

BeautifulSoup is used to parse the HTML response:

```python
soup = BeautifulSoup(response.text, "html.parser")
```

Each book is contained inside an `article` element with the class `product_pod`.

```python
articles = soup.find_all("article", class_="product_pod")
```

`find_all()` is used because each page contains multiple books.

## Data Extraction

### Title

The visible title on the webpage is shortened, so the full title is extracted from the `title` attribute of the `<a>` tag:

```python
title = article.h3.a["title"]
```

### Price

The price is extracted from the `price_color` class:

```python
price = article.find(
    "p",
    class_="price_color"
).text.replace("Â", "")
```

The `replace()` method removes the unwanted `Â` character from the scraped price.

### Rating

The rating is stored in the HTML class attribute:

```python
rating = article.find(
    "p",
    class_="star-rating"
).get("class")
```

For example:

```python
["star-rating", "Three"]
```

The second item contains the actual rating:

```python
rating[1]
```

### Availability

Availability is extracted using:

```python
availability = article.find(
    "p",
    class_="instock availability"
).text.strip()
```

The `strip()` method removes unwanted spaces and newlines from the beginning and end of the text.

## Data Storage

Each book is added to the `books` list:

```python
books.append((title, price, rating[1], availability))
```

After all 50 pages are scraped, the list contains 1,000 records.

The data is then converted into a Pandas DataFrame:

```python
df = pd.DataFrame(
    books,
    columns=["Title", "Price", "Rating", "Availability"]
)
```

The DataFrame is exported to CSV using:

```python
df.to_csv("books_all_pages.csv", index=False)
```

`index=False` prevents the DataFrame index from being added as an extra column in the CSV.

## Data Validation

The total number of scraped books was checked using:

```python
len(books)
```

Result:

```text
1000
```

The DataFrame dimensions were checked using:

```python
df.shape
```

Result:

```text
(1000, 4)
```

Duplicate titles can also be checked using:

```python
df["Title"].duplicated().sum()
```

## Dataset

- Pages scraped: **50**
- Books collected: **1,000**
- Books per page: **20**
- Columns: **4**
- Output format: **CSV**
- Output file: `books_all_pages.csv`

## Project Structure

```text
books-web-scraping/
│
├── books_scraper.py
├── books_all_pages.csv
├── README.md
├── LICENSE
└── .gitignore
```

## How to Run

### 1. Clone the repository

```bash
git clone https://github.com/ranjithbrs/books-web-scraping.git
```

### 2. Install the required libraries

```bash
pip install requests beautifulsoup4 pandas
```

### 3. Run the scraper

```bash
python books_scraper.py
```

The scraper will collect book information from all 50 pages and create:

```text
books_all_pages.csv
```

## What I Learned

Through this project, I practiced:

- Sending HTTP requests using Requests
- Understanding HTTP status codes
- Getting HTML using `response.text`
- Parsing HTML with BeautifulSoup
- Using `find()` and `find_all()`
- Understanding HTML nesting and attributes
- Extracting text and HTML attributes
- Using `.strip()` for whitespace cleaning
- Using `.replace()` for basic data cleaning
- Working with Python lists and indexing
- Using nested `for` loops
- Implementing pagination
- Collecting data from multiple pages
- Creating Pandas DataFrames
- Exporting data to CSV
- Validating scraped data using `len()` and `shape`
- Checking for duplicate records
- Using Git and GitHub to manage the project

## License

This project is licensed under the MIT License.
