"""
eBay Item Detail Scraper
Scrapes full product data from individual eBay item pages:
- Product name, price, condition, category
- Item specifics (size, color, brand, material, etc.)
- Seller description
- Seller info (name, feedback, location)
- All product image URLs
- Product URL
"""

import json
import os
import random
import re
import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── CONFIG ────────────────────────────────────────────────────────────────────
CONFIG = {
    "base_url"      : "https://www.ebay.com/sch/i.html",
    "items_per_page": 60,
    "max_pages"     : 999,        # effectively unlimited — stops when no next page
    "delay_min"     : 3.0,
    "delay_max"     : 6.0,
    "item_delay_min": 2.0,
    "item_delay_max": 4.0,
    "output_json"   : "ebay_items_full.json",
    "progress_file" : "item_scraper_progress.json",
    "page_timeout"  : 25,
    "headless"      : True,
}

# Each entry: "Display Name" -> (category_id, [search keywords])
# The scraper will run each keyword search separately, giving fresh unique items each time
SUBCATEGORIES = {
    "Womens Clothing": ("15724", [
        "womens dress", "womens jeans", "womens top", "womens jacket", "womens blouse",
        "womens skirt", "womens pants", "womens sweater", "womens coat", "womens hoodie",
        "womens shorts", "womens leggings", "womens cardigan", "womens shirt", "womens suit",
    ]),
    "Mens Clothing": ("1059", [
        "mens shirt", "mens jeans", "mens jacket", "mens suit", "mens hoodie",
        "mens pants", "mens sweater", "mens coat", "mens shorts", "mens polo",
        "mens blazer", "mens vest", "mens joggers", "mens tshirt", "mens chinos",
    ]),
    "Womens Shoes": ("3034", [
        "womens sneakers", "womens heels", "womens boots", "womens sandals", "womens flats",
        "womens loafers", "womens pumps", "womens wedges", "womens mules", "womens slip on",
        "womens ankle boots", "womens running shoes", "womens ballet flats", "womens platforms",
    ]),
    "Mens Shoes": ("93427", [
        "mens sneakers", "mens boots", "mens loafers", "mens dress shoes", "mens sandals",
        "mens running shoes", "mens oxford shoes", "mens slip on", "mens chelsea boots",
        "mens trainers", "mens moccasins", "mens boat shoes",
    ]),
    "Womens Accessories": ("4251", [
        "womens scarf", "womens belt", "womens hat", "womens gloves", "womens sunglasses",
        "womens wallet", "womens hair accessories", "womens headband",
    ]),
    "Mens Accessories": ("4250", [
        "mens belt", "mens wallet", "mens tie", "mens scarf", "mens hat",
        "mens sunglasses", "mens watch strap", "mens cufflinks",
    ]),
    "Womens Bags & Handbags": ("169291", [
        "womens handbag", "womens tote bag", "womens shoulder bag", "womens clutch",
        "womens crossbody bag", "womens backpack", "womens purse", "womens satchel",
    ]),
    "Kids Clothing": ("171146", [
        "kids dress", "boys jeans", "girls top", "kids jacket", "boys shirt",
        "girls dress", "kids hoodie", "boys shorts", "girls skirt", "kids coat",
    ]),
    "Baby Clothing": ("260018", [
        "baby onesie", "baby dress", "baby romper", "baby jacket", "baby sleepsuit",
        "baby bodysuit", "baby outfit", "newborn clothes",
    ]),
    "Vintage Clothing": ("175759", [
        "vintage dress", "vintage jacket", "vintage jeans", "vintage shirt", "vintage coat",
        "vintage blouse", "vintage skirt", "retro clothing", "vintage sweater",
    ]),
    "Jewelry": ("281", [
        "gold necklace", "silver ring", "diamond earrings", "pearl bracelet", "gold bracelet",
        "silver necklace", "gemstone ring", "gold earrings", "charm bracelet", "pendant necklace",
    ]),
    "Watches": ("31387", [
        "mens watch", "womens watch", "luxury watch", "automatic watch", "smartwatch",
        "vintage watch", "gold watch", "silver watch", "chronograph watch",
    ]),
}

# Custom browse URLs — add any specific eBay URL here
CUSTOM_URLS = {
    "Johnny Was Tops & Blouses": "https://www.ebay.com/b/Johnny-Was-Tops-Blouses-for-Women/53159/bn_637599",
}
# ─────────────────────────────────────────────────────────────────────────────


def build_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-extensions")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(CONFIG["page_timeout"])
    return driver


def safe_get(driver, url, wait_css=None, retries=2):
    """Load a URL, optionally wait for a CSS selector, return page source or None."""
    for attempt in range(1, retries + 1):
        try:
            driver.get(url)
            time.sleep(random.uniform(1.5, 3.0))
            if wait_css:
                try:
                    WebDriverWait(driver, 12).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_css))
                    )
                except Exception:
                    pass
            src = driver.page_source
            if len(src) > 5000:
                return src
        except Exception as e:
            err = str(e)
            if "invalid session id" in err or "no such window" in err or "disconnected" in err:
                # Signal caller that driver needs rebuild
                raise RuntimeError(f"DRIVER_DEAD:{err}")
            print(f"    [attempt {attempt}] load error: {err[:80]}")
            time.sleep(8 * attempt)
    return None


# ── LISTING PAGE PARSER ───────────────────────────────────────────────────────

def get_item_urls_from_listing(html):
    """Extract individual item URLs from a search/category listing page."""
    soup = BeautifulSoup(html, "html.parser")
    urls = []

    # eBay uses both /itm/ and /p/ style URLs on listing pages
    for a in soup.select("a[href*='/itm/'], a[href*='ebay.com/itm/']"):
        href = a.get("href", "")
        # Clean tracking params — keep only the base item URL
        match = re.search(r'(https?://www\.ebay\.com/itm/\d+)', href)
        if match:
            clean = match.group(1)
            if clean not in urls:
                urls.append(clean)

    # Also handle /p/ product group pages that embed an iid param
    for a in soup.select("a[href*='/p/']"):
        href = a.get("href", "")
        iid = re.search(r'iid=(\d+)', href)
        if iid:
            clean = f"https://www.ebay.com/itm/{iid.group(1)}"
            if clean not in urls:
                urls.append(clean)

    return urls


def has_next_page(html):
    soup = BeautifulSoup(html, "html.parser")
    return bool(soup.select_one("a.pagination__next, a[aria-label='Go to next search page']"))


# ── ITEM PAGE PARSER ──────────────────────────────────────────────────────────

def parse_item_page(html, url, category_name):
    """
    Parse a single eBay item page and return a structured dict with:
    product_name, price, condition, category, item_specifics,
    seller_description, seller_name, seller_feedback, seller_location,
    image_urls, product_url, item_id, scraped_at
    """
    soup = BeautifulSoup(html, "html.parser")
    data = {
        "item_id"                 : "",
        "product_name"            : "",
        "category"                : category_name,
        "price"                   : "",
        "original_price"          : "",
        "condition"               : "",
        "item_specifics"          : {},
        "seller_description"      : "",
        "seller_name"             : "",
        "seller_feedback"         : "",
        "seller_feedback_percent" : "",
        "seller_location"         : "",
        "image_urls"              : [],
        "product_url"             : url,
        "scraped_at"              : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # ── JSON-LD structured data (reliable fallback for price/condition/name) ──
    ld_data = {}
    ld_offers = {}
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            d = json.loads(script.string or "")
            if not isinstance(d, dict):
                continue
            offers = d.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            # Accumulate — keep the block with the most useful data
            if offers.get("price") and not ld_offers.get("price"):
                ld_offers["price"] = offers["price"]
                ld_offers["priceCurrency"] = offers.get("priceCurrency", "USD")
            if offers.get("itemCondition") and not ld_offers.get("itemCondition"):
                ld_offers["itemCondition"] = offers["itemCondition"]
        except Exception:
            pass

    # ── Item ID ──────────────────────────────────────────────────────────────
    m = re.search(r'/itm/(\d+)', url)
    if m:
        data["item_id"] = m.group(1)

    # ── Product Name ─────────────────────────────────────────────────────────
    for sel in [
        "h1.x-item-title__mainTitle span.ux-textspans",
        "h1[itemprop='name']",
        "h1.it-ttl",
        "h1",
    ]:
        el = soup.select_one(sel)
        if el:
            data["product_name"] = el.get_text(strip=True)
            break

    # ── Price ────────────────────────────────────────────────────────────────
    for sel in [
        "div.x-price-primary span.ux-textspans",
        "span[itemprop='price']",
        "span#prcIsum",
        "span#mm-saleDscPrc",
        "div[data-testid='x-price-primary'] span",
        "span.x-price-approx__price",
        "div.x-price-section span.ux-textspans",
    ]:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(strip=True)
            if re.search(r'\$[\d,]+', txt):
                m = re.search(r'(US\s*)?\$[\d,]+\.?\d*(/ea)?', txt)
                data["price"] = m.group(0).replace("US ", "").replace("/ea", "").strip() if m else txt
                break

    # Fallback: grab price from JSON-LD offers
    if not data["price"]:
        p = ld_offers.get("price") or ld_data.get("price")
        cur = ld_offers.get("priceCurrency", "")
        if p:
            data["price"] = f"${p}" if cur in ("USD", "") else f"{cur} {p}"

    # Original / was price
    for sel in [
        "span.ux-textspans--STRIKETHROUGH",
        "span#orgPrc",
        "span.vi-originalPrice",
    ]:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(strip=True)
            m = re.search(r'(US\s*)?\$[\d,]+\.?\d*', txt)
            data["original_price"] = m.group(0).replace("US ", "").strip() if m else txt
            break

    # ── Condition ────────────────────────────────────────────────────────────
    for sel in [
        "div.x-item-condition-text span.ux-textspans",
        "span[itemprop='itemCondition']",
        "span#vi-itm-cond",
        "div[data-testid='x-item-condition'] span",
        "span.condText",
        "div.x-item-condition-text",
        "span.ux-textspans[data-testid*='condition']",
    ]:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(strip=True)
            if txt:
                data["condition"] = txt
                break

    # Fallback: check item_specifics for Condition key
    if not data["condition"] and "Condition" in data.get("item_specifics", {}):
        data["condition"] = data["item_specifics"]["Condition"]

    # Fallback: parse condition from JSON-LD
    if not data["condition"]:
        raw_cond = ld_offers.get("itemCondition", "")
        cond_map = {
            "NewCondition"         : "New",
            "UsedCondition"        : "Used",
            "RefurbishedCondition" : "Refurbished",
            "ForPartsNotWorking"   : "For parts or not working",
        }
        for key, label in cond_map.items():
            if key.lower() in raw_cond.lower():
                data["condition"] = label
                break

    # ── Item Specifics ───────────────────────────────────────────────────────
    specifics = {}

    # Modern eBay layout: dl/dt/dd pairs inside .ux-layout-section
    for dl in soup.select("div.ux-layout-section--item-specifics dl, dl.itemAttr"):
        dts = dl.select("dt")
        dds = dl.select("dd")
        for dt, dd in zip(dts, dds):
            key = dt.get_text(strip=True).rstrip(":")
            val = dd.get_text(strip=True)
            if key and val:
                specifics[key] = val

    # Fallback: table-based specifics (older layout)
    if not specifics:
        for table in soup.select("table.itemAttr, div#viTabs_0_is table"):
            for row in table.select("tr"):
                cells = row.select("td")
                for i in range(0, len(cells) - 1, 2):
                    key = cells[i].get_text(strip=True).rstrip(":")
                    val = cells[i + 1].get_text(strip=True)
                    if key and val:
                        specifics[key] = val

    # Another modern pattern: .ux-labels-values
    if not specifics:
        for row in soup.select(".ux-labels-values__labels-content, .ux-labels-values"):
            labels = row.select(".ux-labels-values__labels span.ux-textspans")
            values = row.select(".ux-labels-values__values span.ux-textspans")
            for lbl, val in zip(labels, values):
                k = lbl.get_text(strip=True).rstrip(":")
                v = val.get_text(strip=True)
                if k and v:
                    specifics[k] = v

    data["item_specifics"] = specifics

    # ── Seller Description ───────────────────────────────────────────────────
    desc_text = ""

    # eBay loads description in an iframe — try to get it from the page source
    # The iframe src is usually in a script or data attribute
    iframe = soup.select_one("iframe#desc_ifr, iframe[id*='desc']")
    if iframe:
        desc_text = "[Description in iframe — use scrape_item_description() for full text]"

    # Try inline description containers
    for sel in [
        "div#ds_div",
        "div.d-item-description",
        "div[data-testid='ux-layout-section-evo__item--description']",
        "div.itemDescContainer",
        "div#viTabs_0_is",
    ]:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(separator="\n", strip=True)
            if len(txt) > len(desc_text):
                desc_text = txt
                break

    data["seller_description"] = desc_text[:3000] if desc_text else ""

    # ── Seller Info ──────────────────────────────────────────────────────────
    # Seller name
    for sel in [
        "span.ux-textspans[data-testid='ux-seller-section__item--seller-name']",
        "a[data-testid='str-title']",
        "span.mbg-nw",
        "a#mbgLink",
        "div[data-testid='x-sellercard-atf'] a span",
    ]:
        el = soup.select_one(sel)
        if el:
            data["seller_name"] = el.get_text(strip=True)
            break

    # Seller feedback score (total count)
    for sel in [
        "span[data-testid='ux-seller-section__item--seller-feedback']",
        "span.mbg-l",
        "span#si-fb",
        "div[data-testid='x-sellercard-atf'] span.ux-textspans--SECONDARY",
    ]:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(strip=True)
            # Clean brackets — store as plain number e.g. 1089956
            clean = re.sub(r'[(),\s]', '', txt)
            data["seller_feedback"] = clean if clean.isdigit() else txt
            break

    # Seller positive feedback percentage
    # Primary: span.ux-textspans--PSEUDOLINK containing "% positive"
    for el in soup.select("span.ux-textspans--PSEUDOLINK"):
        txt = el.get_text(strip=True)
        if "%" in txt and "positive" in txt.lower():
            data["seller_feedback_percent"] = txt
            break

    # Fallback: x-store-information highlights
    if not data["seller_feedback_percent"]:
        for el in soup.select("p.x-store-information__highlights span.ux-textspans"):
            txt = el.get_text(strip=True)
            if "%" in txt and "positive" in txt.lower():
                data["seller_feedback_percent"] = txt
                break

    # Fallback: regex from raw HTML
    if not data["seller_feedback_percent"]:
        m = re.search(r'([\d.]+%\s*positive(?:\s*feedback)?)', html, re.IGNORECASE)
        if m:
            data["seller_feedback_percent"] = m.group(1).strip()

    # Seller location / item location
    # Primary: look for "Located in:" text in SECONDARY spans
    for span in soup.select("span.ux-textspans--SECONDARY"):
        txt = span.get_text(strip=True)
        if txt.lower().startswith("located in:"):
            data["seller_location"] = txt.replace("Located in:", "").strip()
            break

    if not data["seller_location"]:
        for sel in [
            "span[data-testid='ux-seller-section__item--seller-location']",
            "span.ux-textspans[itemprop='availableAtOrFrom']",
            "span[itemprop='availableAtOrFrom']",
            "div.ux-labels-values--itemLocation span.ux-textspans",
        ]:
            el = soup.select_one(sel)
            if el:
                data["seller_location"] = el.get_text(strip=True)
                break

    # ── Images ───────────────────────────────────────────────────────────────
    images = []

    # Primary image gallery — eBay stores full-res URLs in data attributes
    for img in soup.select("div.ux-image-carousel-item img, div.vi-image-gallery img"):
        for attr in ("data-zoom-src", "data-src", "src"):
            src = img.get(attr, "")
            if src and src.startswith("http") and "ebayimg" in src:
                # Upgrade to full resolution: replace s-l[size] with s-l1600
                src = re.sub(r's-l\d+', 's-l1600', src)
                if src not in images:
                    images.append(src)
                break

    # Fallback: any ebayimg thumbnail in the page
    if not images:
        for img in soup.select("img[src*='ebayimg']"):
            src = img.get("src", "")
            src = re.sub(r's-l\d+', 's-l1600', src)
            if src not in images:
                images.append(src)

    # Also check JSON-LD for image list
    for script in soup.select("script[type='application/ld+json']"):
        try:
            ld = json.loads(script.string or "")
            if isinstance(ld, dict):
                imgs = ld.get("image", [])
                if isinstance(imgs, str):
                    imgs = [imgs]
                for img in imgs:
                    if img not in images:
                        images.append(img)
        except Exception:
            pass

    data["image_urls"] = images

    return data


# ── DESCRIPTION IFRAME SCRAPER ────────────────────────────────────────────────

def scrape_description_iframe(driver, item_url):
    """
    eBay loads seller description inside an iframe.
    This function finds the iframe src and fetches its content.
    """
    try:
        # The description iframe URL pattern
        item_id_match = re.search(r'/itm/(\d+)', item_url)
        if not item_id_match:
            return ""
        item_id = item_id_match.group(1)

        # Try to find iframe src in current page
        try:
            iframe = driver.find_element(By.CSS_SELECTOR, "iframe#desc_ifr, iframe[id*='desc']")
            iframe_src = iframe.get_attribute("src")
        except Exception:
            iframe_src = None

        # Fallback: construct the known eBay description endpoint
        if not iframe_src:
            iframe_src = f"https://itm.ebaydesc.com/itmdesc/{item_id}"

        if not iframe_src or not iframe_src.startswith("http"):
            return ""

        html = safe_get(driver, iframe_src)
        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")
        # Remove scripts and styles
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:3000]

    except Exception as e:
        return ""


# ── MAIN SCRAPE FLOW ──────────────────────────────────────────────────────────

REQUIRED_FIELDS = ["price", "condition", "seller_name", "seller_location", "item_specifics", "image_urls"]

def is_complete(item):
    """Return True only if all required fields have data."""
    for f in REQUIRED_FIELDS:
        val = item.get(f)
        if not val or (isinstance(val, (dict, list)) and len(val) == 0):
            return False
    return True


def load_progress():
    if os.path.exists(CONFIG["progress_file"]):
        with open(CONFIG["progress_file"], encoding="utf-8") as f:
            return json.load(f)
    return {"scraped_ids": [], "total": 0}


def save_progress(p):
    with open(CONFIG["progress_file"], "w", encoding="utf-8") as f:
        json.dump(p, f, indent=2)


JSONL_FILE = CONFIG["output_json"].replace(".json", ".jsonl")


def load_existing():
    """Load all items from JSONL file into a list."""
    path = JSONL_FILE
    if not os.path.exists(path):
        return []
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except Exception:
                    pass
    return items


def save_item(item):
    """
    Instantly append item as a single JSON line.
    If item already exists (same item_id), rewrite the file to update it.
    """
    path = JSONL_FILE
    item_id = item.get("item_id", "")

    # Check if item already exists — if so, rewrite to update
    if item_id and os.path.exists(path):
        data = load_existing()
        idx = next((i for i, x in enumerate(data) if x.get("item_id") == item_id), None)
        if idx is not None:
            data[idx] = item
            with open(path, "w", encoding="utf-8") as f:
                for row in data:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            return

    # New item — just append one line instantly
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def scrape_category(driver, cat_name, cat_id_or_url, scraped_ids, progress, start_page=1):
    print(f"\n{'─'*60}")
    print(f"  Category: {cat_name}")
    print(f"{'─'*60}")

    is_custom_url = isinstance(cat_id_or_url, str) and cat_id_or_url.startswith("http")

    # Build list of (label, base_url) to iterate
    if is_custom_url:
        search_targets = [(cat_name, cat_id_or_url)]
    elif isinstance(cat_id_or_url, tuple):
        cat_id, keywords = cat_id_or_url
        search_targets = [
            (kw, f"{CONFIG['base_url']}?_sacat={cat_id}&_nkw={kw.replace(' ', '+')}&_sop=10")
            for kw in keywords
        ]
    else:
        search_targets = [(cat_name, f"{CONFIG['base_url']}?_sacat={cat_id_or_url}&_sop=10")]

    new_count = 0

    for kw_label, base_url in search_targets:
        kw_key = f"{cat_name}::{kw_label}"
        completed_kws = progress.get("completed_keywords", [])
        if kw_key in completed_kws:
            print(f"\n  ⊘ Skip keyword (done): {kw_label}")
            continue

        print(f"\n  Keyword: '{kw_label}'")

        # Resume page for this keyword if interrupted
        resume_kw  = progress.get("current_keyword", "")
        resume_pg  = progress.get("current_page", 1)
        kw_start   = resume_pg if kw_key == resume_kw else 1

        for page_num in range(kw_start, CONFIG["max_pages"] + 1):
            if is_custom_url:
                sep = "&" if "?" in base_url else "?"
                url = f"{base_url}{sep}_pgn={page_num}"
            else:
                url = f"{base_url}&_pgn={page_num}&_ipg={CONFIG['items_per_page']}"

            print(f"\n    Page {page_num}: {url}")
            html = safe_get(driver, url, wait_css="div.brwrvr__item-card, li.s-item")
            if not html:
                print("    ✗ Failed to load listing page")
                break

            item_urls = get_item_urls_from_listing(html)
            print(f"    Found {len(item_urls)} item URLs")

            if not item_urls:
                print("    No items found — stopping this keyword")
                break

            new_on_page = 0
            for idx, item_url in enumerate(item_urls, 1):
                item_id_m = re.search(r'/itm/(\d+)', item_url)
                item_id = item_id_m.group(1) if item_id_m else ""

                if item_id and item_id in scraped_ids:
                    existing = next((x for x in load_existing() if x.get("item_id") == item_id), None)
                    if existing and is_complete(existing):
                        print(f"      [{idx}/{len(item_urls)}] Skip (complete): {item_id}")
                        continue
                    else:
                        print(f"      [{idx}/{len(item_urls)}] Re-scraping (incomplete): {item_id}")
                        scraped_ids.discard(item_id)

                print(f"      [{idx}/{len(item_urls)}] Scraping: {item_url}")
                time.sleep(random.uniform(CONFIG["item_delay_min"], CONFIG["item_delay_max"]))

                item_html = safe_get(
                    driver, item_url,
                    wait_css="h1.x-item-title__mainTitle, h1[itemprop='name'], h1.it-ttl"
                )
                if not item_html:
                    print("        ✗ Failed to load item page")
                    continue

                item_data = parse_item_page(item_html, item_url, cat_name)

                if not item_data["seller_description"] or "iframe" in item_data["seller_description"]:
                    desc = scrape_description_iframe(driver, item_url)
                    if desc:
                        item_data["seller_description"] = desc

                print(f"        ✓ {item_data['product_name'][:55]}")
                print(f"          Price: {item_data['price']}  |  Condition: {item_data['condition']}")
                print(f"          Seller: {item_data['seller_name']}  |  Feedback: {item_data['seller_feedback']}  {item_data['seller_feedback_percent']}")
                print(f"          Location: {item_data['seller_location']}")
                print(f"          Specifics: {len(item_data['item_specifics'])} fields  |  Images: {len(item_data['image_urls'])}")

                save_item(item_data)
                if item_id:
                    scraped_ids.add(item_id)
                new_count += 1
                new_on_page += 1

            # Save progress after each page
            progress["scraped_ids"]      = list(scraped_ids)
            progress["current_keyword"]  = kw_key
            progress["current_page"]     = page_num + 1
            save_progress(progress)

            if not has_next_page(html):
                print(f"\n    ✓ No more pages for '{kw_label}'")
                break

            cool = random.uniform(CONFIG["delay_min"], CONFIG["delay_max"])
            print(f"\n    ⏸  Cooling {cool:.1f}s...")
            time.sleep(cool)

        # Mark keyword done
        completed_kws = progress.get("completed_keywords", [])
        completed_kws.append(kw_key)
        progress["completed_keywords"] = completed_kws
        progress["current_page"] = 1
        save_progress(progress)

    return new_count


def main():
    print("=" * 60)
    print("  eBay Full Item Detail Scraper")
    print(f"  Output: {CONFIG['output_json']}")
    print("=" * 60)

    # Init output file
    if not os.path.exists(CONFIG["output_json"]):
        with open(CONFIG["output_json"], "w", encoding="utf-8") as f:
            json.dump([], f)

    progress = load_progress()
    scraped_ids = set(progress.get("scraped_ids", []))
    grand_total = progress.get("total", 0)
    completed_cats = set(progress.get("completed_categories", []))
    resume_cat = progress.get("current_category", None)
    resume_page = progress.get("current_page", 1)

    driver = build_driver(headless=CONFIG["headless"])

    try:
        all_targets = {**SUBCATEGORIES, **CUSTOM_URLS}

        for cat_name, cat_val in all_targets.items():

            if cat_name in completed_cats:
                print(f"\n  ⊘ Skip (done): {cat_name}")
                continue

            count = scrape_category(driver, cat_name, cat_val, scraped_ids, progress)
            grand_total += count

            completed_cats.add(cat_name)
            progress["completed_categories"] = list(completed_cats)
            progress["current_category"] = cat_name
            progress["current_page"] = 1
            progress["scraped_ids"] = list(scraped_ids)
            progress["total"] = grand_total
            save_progress(progress)

            if count > 0:
                cool = random.uniform(8, 14)
                print(f"\n  ⏸  Cooling {cool:.0f}s between categories...")
                time.sleep(cool)

    except KeyboardInterrupt:
        print("\n\n  ⚠  Stopped by user.")

    except Exception as e:
        import traceback
        print(f"\n\n  ✗ Error: {e}")
        traceback.print_exc()

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    progress["scraped_ids"] = list(scraped_ids)
    progress["total"] = grand_total
    save_progress(progress)

    print(f"\n  ✓ Done! Total items scraped: {grand_total}")
    print(f"  📁 {CONFIG['output_json']}")


if __name__ == "__main__":
    main()
