from bs4 import BeautifulSoup
import re

with open("ebay_page.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

items = soup.select("div.brw-product-card")

if items:
    item = items[0]
    print("First item HTML (first 1000 chars):")
    print(item.prettify()[:1000])
    print("\n" + "="*50)
    
    # Find all links
    links = item.find_all("a")
    print(f"Found {len(links)} links:")
    for i, link in enumerate(links[:5], 1):
        href = link.get("href", "")
        text = link.get_text(strip=True)[:50]
        print(f"  {i}. {href[:80]} -> '{text}'")
    
    # Check for item links specifically
    item_links = item.select("a[href*='/itm/']")
    print(f"\nItem links (a[href*='/itm/']): {len(item_links)}")
    if item_links:
        href = item_links[0].get("href", "")
        print(f"  First: {href}")
        
        # Extract item ID
        match = re.search(r'/itm/(\d+)', href)
        if match:
            print(f"  Item ID: {match.group(1)}")
        else:
            print("  No item ID found")
    
    # Check all hrefs containing 'itm'
    all_itm_links = item.find_all("a", href=re.compile(r'/itm/'))
    print(f"\nAll links with '/itm/': {len(all_itm_links)}")
    for link in all_itm_links[:3]:
        print(f"  {link.get('href')}")