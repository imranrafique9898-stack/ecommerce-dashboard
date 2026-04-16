"""
scraper.py — Complete eBay scraper with all functionality:
  - Scraping product pages (name, price, condition, specifics, images, seller info)
  - Seller feedback count + positive percentage
  - Progress saving/resuming
  - Patch missing feedback % on existing items
  - Export to CSV
  - Live results viewer
  - Stats display
"""

import csv, json, os, random, re, sys, time
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import CONFIG, SUBCATEGORIES, CUSTOM_URLS, REQUIRED_FIELDS


# ═══════════════════════════════════════════════════════════════
#  BROWSER
# ═══════════════════════════════════════════════════════════════

def build_driver():
    options = Options()
    if CONFIG["headless"]:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
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
            if len(driver.page_source) > 5000:
                return driver.page_source
        except Exception as e:
            print(f"    [attempt {attempt}] {str(e)[:60]}")
            time.sleep(8 * attempt)
    return None


# ═══════════════════════════════════════════════════════════════
#  LISTING PAGE
# ═══════════════════════════════════════════════════════════════

def get_item_urls(html):
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for a in soup.select("a[href*='/itm/']"):
        m = re.search(r'(https?://www\.ebay\.com/itm/\d+)', a.get("href", ""))
        if m and m.group(1) not in urls:
            urls.append(m.group(1))
    for a in soup.select("a[href*='/p/']"):
        iid = re.search(r'iid=(\d+)', a.get("href", ""))
        if iid:
            clean = f"https://www.ebay.com/itm/{iid.group(1)}"
            if clean not in urls:
                urls.append(clean)
    return urls


def has_next_page(html):
    return bool(BeautifulSoup(html, "html.parser").select_one("a.pagination__next"))


# ═══════════════════════════════════════════════════════════════
#  ITEM PAGE PARSER
# ═══════════════════════════════════════════════════════════════

def parse_item(html, url, category):
    soup = BeautifulSoup(html, "html.parser")
    data = {
        "item_id": "", "product_name": "", "category": category,
        "price": "", "original_price": "", "condition": "",
        "item_specifics": {}, "seller_description": "",
        "seller_name": "", "seller_feedback": "",
        "seller_feedback_percent": "", "seller_location": "",
        "image_urls": [], "product_url": url,
        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Item ID
    m = re.search(r'/itm/(\d+)', url)
    if m:
        data["item_id"] = m.group(1)

    # JSON-LD — scan all blocks for price/condition
    ld_offers = {}
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            d = json.loads(script.string or "")
            if not isinstance(d, dict):
                continue
            offers = d.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if offers.get("price") and not ld_offers.get("price"):
                ld_offers["price"] = offers["price"]
                ld_offers["priceCurrency"] = offers.get("priceCurrency", "USD")
            if offers.get("itemCondition") and not ld_offers.get("itemCondition"):
                ld_offers["itemCondition"] = offers["itemCondition"]
        except Exception:
            pass

    # Product name
    for sel in ["h1.x-item-title__mainTitle span.ux-textspans", "h1[itemprop='name']", "h1"]:
        el = soup.select_one(sel)
        if el:
            data["product_name"] = el.get_text(strip=True)
            break

    # Price
    for sel in ["div.x-price-primary span.ux-textspans", "span[itemprop='price']",
                "span#prcIsum", "div[data-testid='x-price-primary'] span"]:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(strip=True)
            if re.search(r'\$[\d,]+', txt):
                m2 = re.search(r'(US\s*)?\$[\d,]+\.?\d*(/ea)?', txt)
                data["price"] = m2.group(0).replace("US ", "").replace("/ea", "").strip() if m2 else txt
                break
    if not data["price"] and ld_offers.get("price"):
        data["price"] = f"${ld_offers['price']}"

    # Original price
    for sel in ["span.ux-textspans--STRIKETHROUGH", "span#orgPrc"]:
        el = soup.select_one(sel)
        if el:
            m3 = re.search(r'(US\s*)?\$[\d,]+\.?\d*', el.get_text(strip=True))
            data["original_price"] = m3.group(0).replace("US ", "").strip() if m3 else ""
            break

    # Condition
    for sel in ["div.x-item-condition-text span.ux-textspans",
                "span[itemprop='itemCondition']", "span#vi-itm-cond",
                "div.x-item-condition-text"]:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(strip=True)
            if txt:
                data["condition"] = txt
                break
    if not data["condition"] and ld_offers.get("itemCondition"):
        cond_map = {"NewCondition": "New", "UsedCondition": "Used",
                    "RefurbishedCondition": "Refurbished", "ForPartsNotWorking": "For parts"}
        for k, v in cond_map.items():
            if k.lower() in ld_offers["itemCondition"].lower():
                data["condition"] = v
                break

    # Item specifics
    specifics = {}
    for dl in soup.select("div.ux-layout-section--item-specifics dl, dl.itemAttr"):
        for dt, dd in zip(dl.select("dt"), dl.select("dd")):
            k = dt.get_text(strip=True).rstrip(":")
            v = dd.get_text(strip=True)
            if k and v:
                specifics[k] = v
    if not specifics:
        for row in soup.select(".ux-labels-values"):
            labels = row.select(".ux-labels-values__labels span.ux-textspans")
            values = row.select(".ux-labels-values__values span.ux-textspans")
            for lbl, val in zip(labels, values):
                k = lbl.get_text(strip=True).rstrip(":")
                v = val.get_text(strip=True)
                if k and v:
                    specifics[k] = v
    data["item_specifics"] = specifics

    # Seller description
    for sel in ["div#ds_div", "div.d-item-description", "div.itemDescContainer"]:
        el = soup.select_one(sel)
        if el:
            data["seller_description"] = el.get_text(separator="\n", strip=True)[:3000]
            break

    # Seller name
    for sel in ["a[data-testid='str-title']", "span.mbg-nw", "a#mbgLink",
                "div[data-testid='x-sellercard-atf'] a span"]:
        el = soup.select_one(sel)
        if el:
            data["seller_name"] = el.get_text(strip=True)
            break

    # Seller feedback count
    for sel in ["span[data-testid='ux-seller-section__item--seller-feedback']",
                "span.mbg-l", "span#si-fb"]:
        el = soup.select_one(sel)
        if el:
            txt = re.sub(r'[(),\s]', '', el.get_text(strip=True))
            data["seller_feedback"] = txt if txt.isdigit() else el.get_text(strip=True)
            break

    # Seller feedback percent
    for el in soup.select("span.ux-textspans--PSEUDOLINK"):
        txt = el.get_text(strip=True)
        if "%" in txt and "positive" in txt.lower():
            data["seller_feedback_percent"] = txt
            break
    if not data["seller_feedback_percent"]:
        for el in soup.select("p.x-store-information__highlights span.ux-textspans"):
            txt = el.get_text(strip=True)
            if "%" in txt and "positive" in txt.lower():
                data["seller_feedback_percent"] = txt
                break
    if not data["seller_feedback_percent"]:
        m4 = re.search(r'([\d.]+%\s*positive(?:\s*feedback)?)', html, re.IGNORECASE)
        if m4:
            data["seller_feedback_percent"] = m4.group(1).strip()

    # Seller location
    for span in soup.select("span.ux-textspans--SECONDARY"):
        txt = span.get_text(strip=True)
        if txt.lower().startswith("located in:"):
            data["seller_location"] = txt.replace("Located in:", "").strip()
            break

    # Images — full resolution
    images = []
    for img in soup.select("div.ux-image-carousel-item img, div.vi-image-gallery img"):
        for attr in ("data-zoom-src", "data-src", "src"):
            src = img.get(attr, "")
            if src and "ebayimg" in src:
                src = re.sub(r's-l\d+', 's-l1600', src)
                if src not in images:
                    images.append(src)
                break
    if not images:
        for img in soup.select("img[src*='ebayimg']"):
            src = re.sub(r's-l\d+', 's-l1600', img.get("src", ""))
            if src not in images:
                images.append(src)
    data["image_urls"] = images

    return data


def scrape_description_iframe(driver, item_url):
    try:
        item_id = re.search(r'/itm/(\d+)', item_url)
        if not item_id:
            return ""
        html = safe_get(driver, f"https://itm.ebaydesc.com/itmdesc/{item_id.group(1)}")
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)[:3000]
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════
#  PROGRESS & STORAGE
# ═══════════════════════════════════════════════════════════════

def is_complete(item):
    for f in REQUIRED_FIELDS:
        val = item.get(f)
        if not val or (isinstance(val, (dict, list)) and len(val) == 0):
            return False
    return True


def load_progress():
    if os.path.exists(CONFIG["progress_file"]):
        with open(CONFIG["progress_file"], encoding="utf-8") as f:
            return json.load(f)
    return {"scraped_ids": [], "completed_categories": [], "completed_keywords": [],
            "current_keyword": "", "current_page": 1, "total": 0}


def save_progress(p):
    with open(CONFIG["progress_file"], "w", encoding="utf-8") as f:
        json.dump(p, f, indent=2)


def load_data():
    if os.path.exists(CONFIG["output_json"]):
        with open(CONFIG["output_json"], encoding="utf-8") as f:
            return json.load(f)
    return []


def save_item(item):
    data = load_data()
    idx = next((i for i, x in enumerate(data) if x.get("item_id") == item.get("item_id")), None)
    if idx is not None:
        data[idx] = item
    else:
        data.append(item)
    # Write to temp file first then rename — prevents corruption on crash
    tmp = CONFIG["output_json"] + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG["output_json"])


# ═══════════════════════════════════════════════════════════════
#  CATEGORY SCRAPER
# ═══════════════════════════════════════════════════════════════

def scrape_category(driver, cat_name, cat_val, scraped_ids, progress):
    print(f"\n{'─'*60}\n  Category: {cat_name}\n{'─'*60}")

    is_custom = isinstance(cat_val, str) and cat_val.startswith("http")
    if is_custom:
        targets = [(cat_name, cat_val)]
    else:
        cat_id, keywords = cat_val
        targets = [
            (kw, f"{CONFIG['base_url']}?_sacat={cat_id}&_nkw={kw.replace(' ', '+')}&_sop=10")
            for kw in keywords
        ]

    new_count = 0
    completed_kws = progress.get("completed_keywords", [])

    for kw_label, base_url in targets:
        kw_key = f"{cat_name}::{kw_label}"
        if kw_key in completed_kws:
            print(f"\n  ⊘ Skip keyword (done): {kw_label}")
            continue

        print(f"\n  Keyword: '{kw_label}'")
        resume_pg = progress.get("current_page", 1) if kw_key == progress.get("current_keyword") else 1

        for page_num in range(resume_pg, CONFIG["max_pages"] + 1):
            sep = "&" if "?" in base_url else "?"
            url = (f"{base_url}{sep}_pgn={page_num}" if is_custom
                   else f"{base_url}&_pgn={page_num}&_ipg={CONFIG['items_per_page']}")

            print(f"\n    Page {page_num}: {url}")
            html = safe_get(driver, url, wait_css="div.brwrvr__item-card, li.s-item")
            if not html:
                print("    ✗ Failed to load")
                break

            item_urls = get_item_urls(html)
            print(f"    Found {len(item_urls)} items")
            if not item_urls:
                break

            for idx, item_url in enumerate(item_urls, 1):
                m = re.search(r'/itm/(\d+)', item_url)
                item_id = m.group(1) if m else ""

                if item_id and item_id in scraped_ids:
                    existing = next((x for x in load_data() if x.get("item_id") == item_id), None)
                    if existing and is_complete(existing):
                        print(f"      [{idx}/{len(item_urls)}] Skip: {item_id}")
                        continue
                    scraped_ids.discard(item_id)

                print(f"      [{idx}/{len(item_urls)}] Scraping: {item_url}")
                time.sleep(random.uniform(CONFIG["item_delay_min"], CONFIG["item_delay_max"]))

                item_html = safe_get(driver, item_url,
                                     wait_css="h1.x-item-title__mainTitle, h1[itemprop='name']")
                if not item_html:
                    print("        ✗ Failed")
                    continue

                item_data = parse_item(item_html, item_url, cat_name)
                if not item_data["seller_description"]:
                    desc = scrape_description_iframe(driver, item_url)
                    if desc:
                        item_data["seller_description"] = desc

                print(f"        ✓ {item_data['product_name'][:55]}")
                print(f"          Price: {item_data['price']}  |  Condition: {item_data['condition']}")
                print(f"          Seller: {item_data['seller_name']}  "
                      f"Feedback: {item_data['seller_feedback']}  {item_data['seller_feedback_percent']}")
                print(f"          Location: {item_data['seller_location']}")
                print(f"          Specifics: {len(item_data['item_specifics'])}  "
                      f"Images: {len(item_data['image_urls'])}")

                save_item(item_data)
                if item_id:
                    scraped_ids.add(item_id)
                new_count += 1

            progress.update({"scraped_ids": list(scraped_ids),
                             "current_keyword": kw_key, "current_page": page_num + 1})
            save_progress(progress)

            if not has_next_page(html):
                print(f"\n    ✓ No more pages for '{kw_label}'")
                break
            time.sleep(random.uniform(CONFIG["delay_min"], CONFIG["delay_max"]))

        completed_kws.append(kw_key)
        progress.update({"completed_keywords": completed_kws, "current_page": 1})
        save_progress(progress)

    return new_count


# ═══════════════════════════════════════════════════════════════
#  PATCH FEEDBACK PERCENT
# ═══════════════════════════════════════════════════════════════

def get_feedback_percent(driver, url):
    for attempt in range(1, 3):
        try:
            driver.get(url)
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR,
                        "span.ux-textspans--PSEUDOLINK, div[data-testid='x-sellercard-atf']"))
                )
            except Exception:
                pass
            time.sleep(random.uniform(1.5, 2.5))
            src = driver.page_source
            soup = BeautifulSoup(src, "html.parser")
            for el in soup.select("span.ux-textspans--PSEUDOLINK"):
                txt = el.get_text(strip=True)
                if "%" in txt and "positive" in txt.lower():
                    return txt
            for el in soup.select("p.x-store-information__highlights span.ux-textspans"):
                txt = el.get_text(strip=True)
                if "%" in txt and "positive" in txt.lower():
                    return txt
            m = re.search(r'([\d.]+%\s*positive(?:\s*feedback)?)', src, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        except Exception as e:
            print(f"      [attempt {attempt}] {str(e)[:50]}")
            time.sleep(8)
    return ""


def patch_feedback():
    data = load_data()
    patched_ids = set()
    if os.path.exists(CONFIG["patch_progress"]):
        with open(CONFIG["patch_progress"], encoding="utf-8") as f:
            patched_ids = set(json.load(f).get("patched_ids", []))

    to_patch = [(i, item) for i, item in enumerate(data)
                if not item.get("seller_feedback_percent")
                and item.get("item_id") not in patched_ids
                and item.get("product_url", "").startswith("http")]

    print(f"Total: {len(data)} | Need patching: {len(to_patch)}")
    if not to_patch:
        print("All items have feedback percent!")
        return

    driver = build_driver()
    patched = failed = 0
    try:
        for count, (idx, item) in enumerate(to_patch, 1):
            print(f"  [{count}/{len(to_patch)}] {item.get('product_name','')[:45]}")
            pct = get_feedback_percent(driver, item["product_url"])
            if pct:
                data[idx]["seller_feedback_percent"] = pct
                patched_ids.add(item["item_id"])
                patched += 1
                print(f"    ✓ {pct}")
            else:
                failed += 1
                print(f"    - not found")
            if count % 25 == 0:
                with open(CONFIG["output_json"], "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                with open(CONFIG["patch_progress"], "w", encoding="utf-8") as f:
                    json.dump({"patched_ids": list(patched_ids)}, f, indent=2)
                print(f"\n  Saved — {patched} patched\n")
            time.sleep(random.uniform(1.5, 3.0))
    except KeyboardInterrupt:
        print("\n  Stopped.")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
        with open(CONFIG["output_json"], "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        with open(CONFIG["patch_progress"], "w", encoding="utf-8") as f:
            json.dump({"patched_ids": list(patched_ids)}, f, indent=2)
    print(f"\n  Done! Patched: {patched} | Failed: {failed}")


# ═══════════════════════════════════════════════════════════════
#  EXPORT CSV
# ═══════════════════════════════════════════════════════════════

def export_csv():
    data = load_data()
    fields = ["item_id", "product_name", "category", "price", "original_price",
              "condition", "seller_name", "seller_feedback", "seller_feedback_percent",
              "seller_location", "image_urls", "product_url", "seller_description", "scraped_at"]
    with open(CONFIG["output_csv"], "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for item in data:
            row = dict(item)
            row["image_urls"] = " | ".join(item.get("image_urls", []))
            specs = " | ".join(f"{k}: {v}" for k, v in item.get("item_specifics", {}).items())
            row["seller_description"] = specs + ("\n" + item.get("seller_description", "")
                                                  if item.get("seller_description") else "")
            w.writerow(row)
    print(f"Exported {len(data)} items to {CONFIG['output_csv']}")


# ═══════════════════════════════════════════════════════════════
#  VIEW RESULTS & STATS
# ═══════════════════════════════════════════════════════════════

def view_results(once=False):
    def display():
        data = load_data()
        os.system("cls" if os.name == "nt" else "clear")
        cats = {}
        for item in data:
            cats[item["category"]] = cats.get(item["category"], 0) + 1
        print("=" * 70)
        print(f"  eBay Scraper — Live Results   ({CONFIG['output_json']})")
        print(f"  Total items: {len(data)}")
        print("=" * 70)
        print("\n  By Category:")
        for cat, count in cats.items():
            bar = "█" * min(count // 10, 40)
            print(f"    {cat:<28} {bar} {count}")
        print(f"\n  Last 5 items:")
        print("  " + "─" * 66)
        for item in data[-5:]:
            print(f"  {item.get('product_name','')[:55]}")
            print(f"    {item.get('price','')}  |  {item.get('condition','')}  |  "
                  f"{item.get('seller_name','')}  {item.get('seller_feedback_percent','')}")
            print()
        if not once:
            print("  Refreshing every 5s — Ctrl+C to quit")

    if once:
        display()
    else:
        try:
            while True:
                display()
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n  Viewer stopped.")


def show_stats():
    data = load_data()
    total   = len(data)
    has_fb  = sum(1 for i in data if i.get("seller_feedback"))
    has_pct = sum(1 for i in data if i.get("seller_feedback_percent"))
    cats    = {}
    for item in data:
        cats[item["category"]] = cats.get(item["category"], 0) + 1
    print(f"Total items          : {total}")
    print(f"Has feedback count   : {has_fb}  | Missing: {total - has_fb}")
    print(f"Has feedback percent : {has_pct} | Missing: {total - has_pct}")
    print()
    for k, v in cats.items():
        print(f"  {k:<30} {v}")


# ═══════════════════════════════════════════════════════════════
#  MAIN SCRAPE ENTRY
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  eBay Scraper")
    print(f"  Output: {CONFIG['output_json']}")
    print("=" * 60)

    if not os.path.exists(CONFIG["output_json"]):
        with open(CONFIG["output_json"], "w", encoding="utf-8") as f:
            json.dump([], f)

    progress       = load_progress()
    scraped_ids    = set(progress.get("scraped_ids", []))
    grand_total    = progress.get("total", 0)
    completed_cats = set(progress.get("completed_categories", []))

    driver = build_driver()
    try:
        for cat_name, cat_val in {**SUBCATEGORIES, **CUSTOM_URLS}.items():
            if cat_name in completed_cats:
                print(f"\n  ⊘ Skip (done): {cat_name}")
                continue
            count = scrape_category(driver, cat_name, cat_val, scraped_ids, progress)
            grand_total += count
            completed_cats.add(cat_name)
            progress.update({"completed_categories": list(completed_cats),
                             "scraped_ids": list(scraped_ids), "total": grand_total})
            save_progress(progress)
            if count > 0:
                time.sleep(random.uniform(8, 14))
    except KeyboardInterrupt:
        print("\n  ⚠ Stopped by user.")
    except Exception as e:
        import traceback
        print(f"\n  ✗ Error: {e}")
        traceback.print_exc()
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    save_progress(progress)
    print(f"\n  ✓ Done! Total: {grand_total}")
