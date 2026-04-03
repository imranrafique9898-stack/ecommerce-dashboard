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
driver.set_page_load_timeout(25)

# Check pages 1-15 of Womens Shoes and track unique vs repeated items
seen = set()
for page in range(1, 16):
    url = f"https://www.ebay.com/sch/i.html?_sacat=3034&_pgn={page}&_ipg=60"
    driver.get(url)
    time.sleep(4)
    ids = set(re.findall(r'ebay\.com/itm/(\d+)', driver.page_source))
    new = ids - seen
    seen |= ids
    print(f"Page {page:2d}: {len(ids):3d} items | {len(new):3d} NEW | {len(ids)-len(new):3d} repeated | total unique so far: {len(seen)}")

driver.quit()
