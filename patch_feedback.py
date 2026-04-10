"""
Patch script — adds seller_feedback_percent to items missing it.
Saves progress so it can be resumed if interrupted.
"""
import json, re, time, random, os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PATCH_PROGRESS = "patch_progress.json"

def build_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation","enable-logging"])
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver

def get_feedback_percent(driver, url):
    """Load item page and extract positive feedback percentage."""
    for attempt in range(1, 3):
        try:
            driver.get(url)
            # Wait for seller section to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR,
                        "div[data-testid='x-sellercard-atf'], span.ux-textspans--PSEUDOLINK, span.mbg-l"))
                )
            except Exception:
                pass
            time.sleep(random.uniform(1.5, 2.5))

            src = driver.page_source
            soup = BeautifulSoup(src, "html.parser")

            # Method 1: PSEUDOLINK span with % positive
            for el in soup.select("span.ux-textspans--PSEUDOLINK"):
                txt = el.get_text(strip=True)
                if "%" in txt and "positive" in txt.lower():
                    return txt

            # Method 2: store highlights paragraph
            for el in soup.select("p.x-store-information__highlights span.ux-textspans"):
                txt = el.get_text(strip=True)
                if "%" in txt and "positive" in txt.lower():
                    return txt

            # Method 3: sellercard data items
            for el in soup.select("div.x-sellercard-atf__data-item span.ux-textspans"):
                txt = el.get_text(strip=True)
                if "%" in txt and "positive" in txt.lower():
                    return txt

            # Method 4: regex fallback
            m = re.search(r'([\d.]+%\s*positive(?:\s*feedback)?)', src, re.IGNORECASE)
            if m:
                return m.group(1).strip()

        except Exception as e:
            print(f"      [attempt {attempt}] error: {str(e)[:50]}")
            time.sleep(8)

    return ""

def load_patch_progress():
    if os.path.exists(PATCH_PROGRESS):
        with open(PATCH_PROGRESS, encoding="utf-8") as f:
            return json.load(f)
    return {"patched_ids": []}

def save_patch_progress(p):
    with open(PATCH_PROGRESS, "w", encoding="utf-8") as f:
        json.dump(p, f, indent=2)

def main():
    with open("ebay_items_full.json", encoding="utf-8") as f:
        data = json.load(f)

    patch_prog = load_patch_progress()
    already_patched = set(patch_prog.get("patched_ids", []))

    # Find items missing feedback percent and not yet patched
    to_patch = [
        (i, item) for i, item in enumerate(data)
        if not item.get("seller_feedback_percent")
        and item.get("item_id") not in already_patched
        and item.get("product_url", "").startswith("http")
    ]

    print(f"Total items        : {len(data)}")
    print(f"Already patched    : {len(already_patched)}")
    print(f"Need patching now  : {len(to_patch)}")

    if not to_patch:
        print("All items have feedback percent!")
        return

    driver = build_driver()
    patched = 0
    failed  = 0

    try:
        for count, (idx, item) in enumerate(to_patch, 1):
            url     = item.get("product_url", "")
            item_id = item.get("item_id", "")
            name    = item.get("product_name", "")[:45]

            print(f"  [{count}/{len(to_patch)}] {name}")

            pct = get_feedback_percent(driver, url)

            if pct:
                data[idx]["seller_feedback_percent"] = pct
                already_patched.add(item_id)
                patched += 1
                print(f"    ✓ {pct}")
            else:
                failed += 1
                print(f"    - not found")

            # Save every 25 items
            if count % 25 == 0:
                with open("ebay_items_full.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                patch_prog["patched_ids"] = list(already_patched)
                save_patch_progress(patch_prog)
                print(f"\n  Saved — {patched} patched, {failed} failed so far\n")

            time.sleep(random.uniform(1.5, 3.0))

    except KeyboardInterrupt:
        print("\n  Stopped by user.")

    finally:
        try:
            driver.quit()
        except Exception:
            pass

        # Final save
        with open("ebay_items_full.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        patch_prog["patched_ids"] = list(already_patched)
        save_patch_progress(patch_prog)

    print(f"\n  Done! Patched: {patched} | Failed: {failed}")
    print(f"  Run again to retry failed items.")

if __name__ == "__main__":
    main()
