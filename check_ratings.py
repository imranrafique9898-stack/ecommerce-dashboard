from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time, re

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--log-level=3")
options.add_experimental_option("excludeSwitches", ["enable-automation","enable-logging"])
driver = webdriver.Chrome(options=options)
driver.set_page_load_timeout(20)
driver.get("https://www.ebay.com/itm/206122572264")
time.sleep(4)
src = driver.page_source[:80000]
soup = BeautifulSoup(src, "html.parser")

# sellercard
card = soup.select_one("div[data-testid='x-sellercard-atf']")
if card:
    print("SELLERCARD:", card.get_text(separator=" | ", strip=True)[:300])

# feedback count clean
m = re.search(r'\((\d[\d,]+)\)', src)
if m: print("Feedback count:", m.group(1))

# positive %
m2 = re.search(r'([\d.]+%\s*positive)', src, re.IGNORECASE)
if m2: print("Positive %:", m2.group(1))

driver.quit()
print("done")
