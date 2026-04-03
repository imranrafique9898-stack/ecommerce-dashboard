from bs4 import BeautifulSoup
import re

with open("ebay_page.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

items = soup.select("div.brwrvr__item-card")
print(f"Found {len(items)} items\n")

if items:
    print("=" * 80)
    print("FIRST ITEM STRUCTURE:")
    print("=" * 80)
    item = items[0]
    print(item.prettify()[:2000])
    print("\n" + "=" * 80)
    
    # Try to extract data
    print("EXTRACTION TEST:")
    print("-" * 80)
    
    link_el = item.select_one("a[href*='/itm/']")
    print(f"Link element: {link_el.get('href')[:100] if link_el else 'NOT FOUND'}")
    
    title_el = item.select_one("span[role='heading'], .s-item__title, h2")
    print(f"Title element found: {title_el is not None}")
    if title_el:
        print(f"  Text: {title_el.get_text()[:60]}")
    
    img_el = item.select_one("img")
    print(f"Image element found: {img_el is not None}")
    if img_el:
        print(f"  Src: {img_el.get('src', img_el.get('data-src', 'N/A'))[:60]}")
    
    # Find all text content
    print(f"\nAll text in first item:")
    print(item.get_text()[:300])
