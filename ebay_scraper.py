import csv
import json
import os
import random
import re
import time
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CONFIG = {
    "base_url"      : "https://www.ebay.com/sch/i.html",
    "items_per_page": 60,
    "max_pages"     : 100,
    "delay_min"     : 4.0,
    "delay_max"     : 8.0,
    "output_csv"    : "ebay_clothing_products.csv",
    "output_json"   : "ebay_clothing_products.json",
    "progress_file" : "scraper_progress.json",
    "captcha_wait"  : 60,
    "page_timeout"  : 20,
}

SUBCATEGORIES = {
    "Womens Clothing"        : "15724",
    "Mens Clothing"          : "1059",
    "Womens Shoes"           : "3034",
    "Mens Shoes"             : "93427",
    "Womens Accessories"     : "4251",
    "Mens Accessories"       : "4250",
    "Womens Bags & Handbags" : "169291",
    "Kids Clothing"          : "171146",
    "Baby Clothing"          : "260018",
    "Vintage Clothing"       : "175759",
    "Jewelry"                : "281",
    "Watches"                : "31387",
}

CSV_FIELDS = [
    "item_id", "product_name", "category", "description",
    "condition", "price", "shipping", "seller", "location",
    "product_url", "add_to_cart_url", "image_url", "scraped_at",
]


def build_driver(headless=False):
    """Build Chrome driver with anti-crash options"""
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    # Anti-crash options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-crash-reporter")
    options.add_argument("--disable-sync")
    options.add_argument("--dns-prefetch-disable")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    )

    # Try to prevent crashes
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2,  # Block images
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.media_stream": 2,
    })

    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(CONFIG["page_timeout"])
        driver.implicitly_wait(5)  # Reduced
        return driver
    except Exception as e:
        print(f"  ❌ Chrome driver failed: {e}")
        print("  💡 Try updating Chrome browser or use headless mode")
        raise


def get_headers():
    """Return rotating user agents"""
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    ]
    return {
        "User-Agent": random.choice(agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def fetch_page_requests(url):
    """Try fetching with requests first (faster, less detection)"""
    for attempt in range(1, 4):
        try:
            print(f"Req Attempt {attempt}...", end=" ", flush=True)
            response = requests.get(url, headers=get_headers(), timeout=15)
            response.raise_for_status()
            
            # Check if we got blocked
            if "captcha" in response.text.lower() or response.status_code == 429:
                print(f"Blocked (status {response.status_code})")
                time.sleep(20 * attempt)
                continue
            
            if "ebay" in response.text.lower() and len(response.text) > 5000:
                print("✓ OK", flush=True)
                return response.text
            else:
                print("No content")
                time.sleep(10 * attempt)
                
        except Exception as e:
            print(f"Error: {str(e)[:40]}")
            time.sleep(10 * attempt)
    
    return None


def is_blocked(driver):
    signals = [
        "captcha", "robot", "unusual traffic",
        "verify you are human", "access denied",
        "security check", "g-recaptcha", "hcaptcha",
    ]
    return any(s in driver.page_source.lower() for s in signals)


def scrape_description(driver, url):
    """Scrape full item description from eBay item page"""
    if not url or url == "N/A":
        return ""
    
    try:
        driver.get(url)
        time.sleep(random.uniform(2, 4))
        
        # Wait for description to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#viTabs_0_is, #desc_div, .u-flL"))
            )
        except:
            pass
        
        # Try multiple selectors for description
        desc_selectors = [
            "#viTabs_0_is",  # Item specifics
            "#desc_div",     # Description div
            ".u-flL",        # Description content
            "[data-testid='item-description']",
            ".notranslate"   # Often used for descriptions
        ]
        
        for selector in desc_selectors:
            try:
                desc_el = driver.find_element(By.CSS_SELECTOR, selector)
                desc_text = desc_el.text.strip()
                if desc_text and len(desc_text) > 20:  # Minimum length
                    return desc_text[:2000]  # Limit length
            except:
                continue
        
        # Fallback: get all text from body and clean
        body_text = driver.find_element(By.TAG_NAME, "body").text
        # Remove common eBay elements
        lines = body_text.split('\n')
        desc_lines = []
        in_desc = False
        for line in lines:
            if 'description' in line.lower() and not in_desc:
                in_desc = True
                continue
            if in_desc and len(line.strip()) > 10:
                desc_lines.append(line.strip())
                if len(desc_lines) > 10:  # Limit
                    break
        if desc_lines:
            return ' '.join(desc_lines)[:2000]
        
    except Exception as e:
        print(f"  Description error: {str(e)[:50]}")
    
    return ""


def fetch_page(driver, url):
    """Use Selenium directly (requests get blocked by eBay with 500 errors)"""
    print("Loading...", end=" ", flush=True)
    
    for attempt in range(1, 3):
        try:
            driver.get(url)
            time.sleep(random.uniform(3, 5))
            
            # Wait for items to load
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.s-item-container, li.s-item, div[data-component-type='s-search-result']"))
                )
            except:
                pass

            # Scroll to trigger lazy loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)

            page_source = driver.page_source
            
            # Check if we got real content
            if len(page_source) > 10000:
                print("✓ OK", flush=True)
                return page_source
            else:
                print(f"Incomplete ({len(page_source)} bytes)")
                time.sleep(10 * attempt)
                continue

        except Exception as e:
            print(f"Error: {str(e)[:40]}", flush=True)
            time.sleep(15 * attempt)

    print("FAILED", flush=True)
    return None


def parse_page(html, category_name):
    soup     = BeautifulSoup(html, "html.parser")
    products = []

    # eBay now uses brwrvr__item-card and brw-product-card classes (changed from s-item)
    items = soup.select("div.brwrvr__item-card") or soup.select("div.brw-product-card")
    
    print(f" [{len(items)} items found]", end=" ", flush=True)

    for item in items:
        try:
            # Find the main link with item ID - eBay now uses /p/ URLs
            link_el = item.select_one("a[href*='/p/']") or item.select_one("a[href*='/itm/']")
            product_url = ""
            item_id = ""

            if link_el and link_el.get("href"):
                product_url = link_el["href"]
                # Extract item ID from URL - try both patterns
                # Old pattern: /itm/306830742556
                match = re.search(r'/itm/(\d+)', product_url)
                if match:
                    item_id = match.group(1)
                else:
                    # New pattern: ?iid=135823344757
                    match = re.search(r'iid=(\d+)', product_url)
                    if match:
                        item_id = match.group(1)

            # Title - get all text and clean it up
            title = item.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            # Extract price from text (usually at the end)
            price = "N/A"
            price_match = re.search(r'\$[\d,]+\.\d{2}', title)
            if price_match:
                price = price_match.group(0)

            # Extract title (everything before price)
            if price != "N/A":
                title = title.replace(price, "").strip()

            # Clean up title - remove common suffixes
            title = re.sub(r'\s*\([^)]*\)\s*$', '', title)  # Remove (size) at end
            title = re.sub(r'\s*New\s*$', '', title, flags=re.IGNORECASE).strip()
            title = re.sub(r'\s*Used\s*$', '', title, flags=re.IGNORECASE).strip()

            # Image - try multiple selectors and ensure full URL
            image_url = ""
            img_el = item.select_one("img") or item.select_one("img[data-src]")
            if img_el:
                image_url = img_el.get("data-src") or img_el.get("src", "")
                # Ensure it's a full URL
                if image_url and not image_url.startswith("http"):
                    image_url = "https:" + image_url if image_url.startswith("//") else ""

            # Shipping - look for shipping info in full text
            shipping = ""
            ship_text = item.get_text()
            if "free shipping" in ship_text.lower():
                shipping = "Free shipping"
                title = title.replace("Free shipping", "").strip()
            elif "shipping" in ship_text.lower():
                ship_match = re.search(r'[\$]\d+\.\d{2}\s*shipping', ship_text, re.IGNORECASE)
                if ship_match:
                    shipping = ship_match.group(0)

            # Condition - look for new/used/refurbished
            condition = ""
            if "new" in title.lower():
                condition = "New"
            elif "used" in title.lower():
                condition = "Used"
            elif "refurbished" in title.lower():
                condition = "Refurbished"

            # Seller - try to find seller info
            seller = "Unknown"
            seller_el = item.select_one("span.s-item__seller-info-text") or item.find(string=re.compile(r'Seller:\s*', re.IGNORECASE))
            if seller_el:
                seller_text = seller_el.get_text() if hasattr(seller_el, 'get_text') else str(seller_el)
                seller_match = re.search(r'Seller:\s*(.+)', seller_text, re.IGNORECASE)
                if seller_match:
                    seller = seller_match.group(1).strip()

            # Location - try to find location
            location = ""
            loc_el = item.select_one("span.s-item__location") or item.find(string=re.compile(r'from\s+', re.IGNORECASE))
            if loc_el:
                loc_text = loc_el.get_text() if hasattr(loc_el, 'get_text') else str(loc_el)
                loc_match = re.search(r'from\s+(.+)', loc_text, re.IGNORECASE)
                if loc_match:
                    location = loc_match.group(1).strip()

            # Description - try to get more detailed description
            description = condition
            desc_el = (item.select_one("span.s-item__subtitle") or 
                      item.select_one("div.s-item__detail") or 
                      item.select_one("span.SECONDARY_INFO") or
                      item.select_one("div.brw-product-card__subtitle") or
                      item.select_one("span.brw-product-card__detail") or
                      item.select_one("div[data-testid='item-description']") or
                      item.select_one("span[data-testid='item-subtitle']"))
            if desc_el:
                desc_text = desc_el.get_text(strip=True)
                if desc_text and len(desc_text) > len(description):
                    description = desc_text
            
            # If no detailed description, add note that full description is on item page
            if not description or description == condition:
                description = f"{condition} - Full description available on item page".strip(" - ")

            add_to_cart = (
                f"https://www.ebay.com/cart/toCart?item={item_id}&qty=1&action=add"
                if item_id else "N/A"
            )

            products.append({
                "item_id"        : item_id,
                "product_name"   : title,
                "category"       : category_name,
                "description"    : description,
                "condition"      : condition,
                "price"          : price,
                "shipping"       : shipping,
                "seller"         : seller,
                "location"       : location,
                "product_url"    : product_url,
                "add_to_cart_url": add_to_cart,
                "image_url"      : image_url,
                "scraped_at"     : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

        except Exception as e:
            continue

    return products


def has_next_page(html):
    soup = BeautifulSoup(html, "html.parser")
    return bool(soup.select_one(
        "a.pagination__next, a[aria-label='Go to next search page']"
    ))


def init_csv(path):
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()
        print(f"  Created: {path}")


def append_csv(path, rows):
    with open(path, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(
            f, fieldnames=CSV_FIELDS, extrasaction="ignore"
        ).writerows(rows)


def init_json(path):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)
        print(f"  Created: {path}")


def append_json(path, rows):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    data.extend(rows)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)



def load_progress():
    if os.path.exists(CONFIG["progress_file"]):
        with open(CONFIG["progress_file"]) as f:
            return json.load(f)
    return {"completed": [], "total": 0}


def save_progress(p):
    with open(CONFIG["progress_file"], "w") as f:
        json.dump(p, f, indent=2)


def scrape_category(driver, cat_name, cat_id, output_csv, output_json):
    total = 0
    print(f"\n{'─'*60}")
    print(f"  Category: {cat_name}  (ID: {cat_id})")
    print(f"{'─'*60}")
    
    # Load existing item IDs to avoid duplicates
    existing_ids = set()
    if os.path.exists(output_json):
        try:
            with open(output_json) as f:
                existing = json.load(f)
            existing_ids = {item.get('item_id') for item in existing if item.get('item_id')}
            print(f"  Loaded {len(existing_ids)} existing items")
        except:
            pass

    # Get total results count from first page
    url = f"{CONFIG['base_url']}?_sacat={cat_id}&_pgn=1&_ipg={CONFIG['items_per_page']}"
    html = fetch_page(driver, url)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        # Try to find total results
        total_el = soup.select_one(".s-pagination__count, .ebayui-pagination__count, .srp-pagination__count")
        if total_el:
            total_text = total_el.get_text()
            print(f"  Total results shown: {total_text}")
        else:
            print(f"  Note: eBay shows thousands of results, scraper limited to {CONFIG['max_pages']} pages (~{CONFIG['max_pages']*17} items) to avoid detection")

    for page_num in range(1, CONFIG["max_pages"] + 1):
        if page_num == 1 and html:  # Already have page 1
            pass
        else:
            url = f"{CONFIG['base_url']}?_sacat={cat_id}&_pgn={page_num}&_ipg={CONFIG['items_per_page']}"
            html = fetch_page(driver, url)

        if html is None:
            print(" SKIP")
            continue

        products = parse_page(html, cat_name)

        if not products:
            print(" 0 items")
            continue

        new_products = [p for p in products if p['item_id'] not in existing_ids]
        for p in new_products:
            existing_ids.add(p['item_id'])
        
        if not new_products:
            print(f" {len(products)} items found, 0 new")
            continue

        append_csv(output_csv, new_products)
        append_json(output_json, new_products)
        total += len(new_products)
        print(f" {len(products)} items found, {len(new_products)} new  |  total: {total}")
        
        # Print each product to console (first 3 only)
        for idx, product in enumerate(products[:3], 1):
            print(f"      {idx}. {product['product_name'][:65]}")
            print(f"         💰 {product['price']} | 👤 {product['seller'][:30]}")

        if len(products) > 3:
            print(f"      ... and {len(products) - 3} more items")

        if not has_next_page(html):
            print(f"   ✓ Done: {cat_name} ({total} items)")
            break

    return total


def main():
    print("=" * 60)
    print("  eBay Scraper — Selenium Edition")
    print(f"  CSV: {CONFIG['output_csv']}")
    print(f"  JSON: {CONFIG['output_json']}")
    print("=" * 60)

    init_csv(CONFIG["output_csv"])
    init_json(CONFIG["output_json"])
    progress    = load_progress()
    grand_total = progress.get("total", 0)

    driver = build_driver(headless=True)  # Use headless to avoid crashes

    try:
        for cat_name, cat_id in SUBCATEGORIES.items():

            if cat_name in progress["completed"]:
                print(f"  ⊘ Skipping: {cat_name}")
                continue

            count = scrape_category(driver, cat_name, cat_id, CONFIG["output_csv"], CONFIG["output_json"])
            grand_total += count

            progress["completed"].append(cat_name)
            progress["total"] = grand_total
            save_progress(progress)

            if count > 0:
                cool = random.uniform(10, 15)
                print(f"\n  ⏸️  Cooling {cool:.0f}s...\n")
                time.sleep(cool)

    except KeyboardInterrupt:
        print("\n\n  ⚠️  Stopped by user.")

    except Exception as e:
        print(f"\n\n  ❌ Error: {str(e)[:100]}")
        import traceback
        traceback.print_exc()
        
    finally:
        try:
            driver.quit()
        except:
            pass

    print(f"\n  ✓ Done! Total items: {grand_total}")
    print(f"  📁 CSV: {CONFIG['output_csv']}")
    print(f"  📁 JSON: {CONFIG['output_json']}")
    print(f"  📊 Note: Limited to {CONFIG['max_pages']} pages per category to avoid blocks")


if __name__ == "__main__":
    main()