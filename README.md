# 📚 Books Web Scraping & Data Extraction Pipeline

[![Python: 3.8+](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Library: BeautifulSoup4](https://img.shields.io/badge/Parser-BeautifulSoup%204-green?style=for-the-badge&logo=python&logoColor=white)](https://www.crummy.com/software/BeautifulSoup/)
[![Library: Requests](https://img.shields.io/badge/HTTP-Requests-blue?style=for-the-badge&logo=python&logoColor=white)](https://requests.readthedocs.io/)
[![Data: Pandas](https://img.shields.io/badge/Analysis-Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Dataset: 1000 Books](https://img.shields.io/badge/Dataset-1000%20Books%20%7C%2050%20Pages-orange?style=for-the-badge)](books_all_pages.csv)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)](LICENSE)

> An end-to-end Python web scraping and data processing pipeline that systematically extracts, cleans, normalizes, and validates catalog data across all 50 pages of [Books to Scrape](https://books.toscrape.com/), yielding a structured 1,000-record dataset in CSV format.

---

## 📑 Table of Contents
- [Data Extraction Architecture](#-data-extraction-architecture)
- [Project Overview](#-project-overview)
- [Collected Features & Schema](#-collected-features--schema)
- [Scraping & Data Cleaning Pipeline](#-scraping--data-cleaning-pipeline)
- [Repository Structure](#-repository-structure)
- [How to Run Locally](#-how-to-run-locally)
- [Key Engineering Takeaways](#-key-engineering-takeaways)
- [Author & Connect](#-author)
- [License](#-license)

---

## 📐 Data Extraction Architecture

```mermaid
flowchart TD
    subgraph Target["🌐 Target Source: books.toscrape.com"]
        A[Catalog Pagination Engine: Pages 1 to 50]
    end

    subgraph Network["📡 HTTP Acquisition Layer"]
        A -->|Iterate range 1, 51| B[requests.get dynamic URL]
        B --> C{HTTP 200 OK?}
        C -->|Yes| D[Raw HTML Document Response]
        C -->|No / Timeout| E[Error Handler & Retry]
    end

    subgraph Parsing["⚙️ DOM Parsing (BeautifulSoup 4)"]
        D --> F[Parse with html.parser]
        F --> G[Extract Book Cards: article.product_pod]
    end

    subgraph Cleaning["🧹 Data Normalization & Transformation"]
        G --> H[Full Title: article.h3.a title attribute]
        G --> I[Clean Price: Strip Non-ASCII Encoding Artifacts]
        G --> J[Rating: Parse Secondary Class name: One, Two, Three]
        G --> K[Availability: Strip Whitespace & In-Stock Status]
    end

    subgraph Persistence["🗄️ Tabular Aggregation & Export"]
        H --> L[Pandas DataFrame Builder]
        I --> L
        J --> L
        K --> L
        L --> M[Export: books_all_pages.csv - 1000 Rows x 4 Cols]
        L --> N[Data Shape & Duplication Validation]
    end
```

---

## 🌟 Project Overview

This project was built to master robust web scraping principles, handling dynamic pagination, resolving character encoding inconsistencies, traversing nested HTML DOM trees with **BeautifulSoup**, and assembling clean analytical datasets using **Pandas**.

### Dataset Summary:
- **Target Site**: [Books to Scrape](https://books.toscrape.com/)
- **Total Pages Scraped**: 50 pages
- **Books per Page**: 20 items
- **Total Records Extracted**: 1,000 unique titles
- **Storage Output**: `books_all_pages.csv`

---

## 📊 Collected Features & Schema

| Column Name | Data Type | Description | Example Value |
| :--- | :--- | :--- | :--- |
| `Title` | String | Complete unabbreviated book title extracted from `<a>` attribute | `A Light in the Attic` |
| `Price` | String / Float | Product price in British Pounds (£) stripped of encoding noise | `£51.77` |
| `Rating` | String (Categorical) | Star rating converted from CSS class names | `Three` |
| `Availability` | String | Inventory stock status cleaned of trailing whitespace | `In stock` |

---

## ⚙️ Scraping & Data Cleaning Pipeline

1. **Deterministic Pagination**:
   ```python
   for page in range(1, 51):
       url = f"https://books.toscrape.com/catalogue/page-{page}.html"
   ```
2. **Title Attribute Selection**: Visible inner text on the card is truncated with ellipsis (`...`). The full title is programmatically extracted from the HTML `title` tag attribute:
   ```python
   title = article.h3.a["title"]
   ```
3. **Encoding & Non-ASCII Artifact Removal**: Removes legacy Windows-1252 byte misinterpretations (such as `"Â"`) from currency strings:
   ```python
   price = article.find("p", class_="price_color").text.replace("Â", "")
   ```
4. **CSS Class-Based Rating Extraction**: Ratings are encoded in the second CSS class attribute (e.g. `class="star-rating Three"`):
   ```python
   rating = article.find("p", class_="star-rating").get("class")[1]
   ```

---

## 📁 Repository Structure

```text
books-web-scraping/
├── books_scraper.py            # Primary web scraping & Pandas export script
├── books_all_pages.csv         # Generated 1,000-row tabular dataset
├── requirements.txt            # Python dependencies (requests, bs4, pandas)
├── LICENSE                     # MIT open source license
└── README.md                   # Project documentation
```

---

## 🚀 How to Run Locally

### 1. Clone the Repository
```bash
git clone https://github.com/ranjithbrs/books-web-scraping.git
cd books-web-scraping
```

### 2. Install Dependencies
```bash
pip install requests beautifulsoup4 pandas
```

### 3. Execute the Scraper
```bash
python books_scraper.py
```

### Output:
```text
Data saved to books_all_pages.csv
Total books: 1000
(1000, 4)
```

---

## 💡 Key Engineering Takeaways

- **HTTP Status Validation**: Verified consistent HTTP 200 OK responses across all 50 paginated requests.
- **Defensive Parsing**: Handled truncated text vs DOM attributes to guarantee zero loss of book title data.
- **Tabular Data Quality**: Validated dataset dimensions using `df.shape` to confirm complete $50 \times 20 = 1,000$ row fidelity.
- **Export Formats**: Standardized output as UTF-8 compliant CSV for downstream exploratory data analysis (EDA) in Jupyter or Excel.

---

## 👨‍💻 Author

**Ranjith B**  
🎓 *B.Tech Computer Science & Business Systems (CSBS)*  
🏛️ *Nehru Institute of Engineering and Technology, Coimbatore*  

- 💼 **LinkedIn**: [linkedin.com/in/ranjith-b-csbs23](https://linkedin.com/in/ranjith-b-csbs23)  
- 🐙 **GitHub**: [github.com/ranjithbrs](https://github.com/ranjithbrs)  
- 🌐 **Portfolio**: [ranjithbrs.github.io/portfolio](https://ranjithbrs.github.io/portfolio/)  
- 📧 **Email**: ranjithb2k06@gmail.com  

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
