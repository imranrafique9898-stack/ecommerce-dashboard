import json
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def build_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

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
        print(f"  Description error for {url}: {str(e)[:50]}")
    
    return ""

def main():
    json_file = "ebay_clothing_products.json"
    
    with open(json_file) as f:
        data = json.load(f)
    
    driver = build_driver()
    
    updated = 0
    for i, item in enumerate(data):
        if not item.get('description') or len(item['description']) < 10:
            print(f"Scraping description for item {i+1}/{len(data)}: {item['item_id']}")
            desc = scrape_description(driver, item['product_url'])
            if desc:
                item['description'] = desc
                updated += 1
            time.sleep(random.uniform(3, 6))  # Delay to avoid blocks
    
    driver.quit()
    
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Updated {updated} descriptions")

if __name__ == "__main__":
    main()