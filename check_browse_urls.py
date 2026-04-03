from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time, re

options = Options()
# NON-headless to test real browser behavior
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--log-level=3")
options.add_argument("--window-size=1920,1080")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
options.add_experimental_option("excludeSwitches", ["enable-automation","enable-logging"])
options.add_experimental_option("useAutomationExtension", False)
driver = webdriver.Chrome(options=options)
driver.set_page_load_timeout(30)

# First visit eBay homepage to get cookies
driver.get("https://www.ebay.com")
time.sleep(3)

urls = [
    ("p1", "https://www.ebay.com/sch/i.html?_sacat=3034&_sop=10&_pgn=1&_ipg=60"),
    ("p2", "https://www.ebay.com/sch/i.html?_sacat=3034&_sop=10&_pgn=2&_ipg=60"),
    ("p3", "https://www.ebay.com/sch/i.html?_sacat=3034&_sop=10&_pgn=3&_ipg=60"),
    ("p4", "https://www.ebay.com/sch/i.html?_sacat=3034&_sop=10&_pgn=4&_ipg=60"),
]

seen = set()
for label, url in urls:
    driver.get(url)
    time.sleep(5)
    ids = set(re.findall(r'/itm/(\d+)', driver.page_source))
    new = ids - seen
    seen |= ids
    print(f"{label}: {len(ids)} items | NEW: {len(new)} | repeated: {len(ids)-len(new)}")

driver.quit()
print("done")
