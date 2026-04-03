from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

options = Options()
options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(options=options)

url = "https://www.ebay.com/sch/i.html?_sacat=15724&_pgn=1&_ipg=60"

print("Fetching...")
driver.get(url)
time.sleep(5)

# Save HTML for inspection
with open("ebay_page.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)

print("HTML saved to ebay_page.html")
print(f"Page length: {len(driver.page_source)} bytes")

# Try to find items
from bs4 import BeautifulSoup
soup = BeautifulSoup(driver.page_source, "html.parser")

# Try various selectors
selectors = [
    "li.s-item",
    "div.s-item-container",
    "div[data-component-type='s-search-result']",
    "div.s-result-item",
    "article.s-result-item",
]

for sel in selectors:
    items = soup.select(sel)
    print(f"{sel}: {len(items)} items")

driver.quit()
print("\nDone. Inspect ebay_page.html to see the structure.")
