import pandas as pd
import requests
from bs4 import BeautifulSoup

books=[]
for page in range(1,51):
    url=f"https://books.toscrape.com/catalogue/page-{page}.html"
    response=requests.get(url)
    soup=BeautifulSoup(response.text, "html.parser")
    articles = soup.find_all("article", class_="product_pod")
    #print(page, url, response.status_code)
    #print(page, len(articles))
    for article in articles:
        title=article.h3.a['title']    
        price=article.find('p', class_="price_color").text.replace("Â","")
        rating=article.find('p', class_="star-rating").get('class')
        availability=article.find('p', class_="instock availability").text.strip()
        books.append((title, price, rating[1], availability))
    df=pd.DataFrame(books, columns=['Title', 'Price', 'Rating', 'Availability'])
    df.to_csv('books_all_pages.csv', index=False)
#print("Total books:", len(books))
#print(df.shape)