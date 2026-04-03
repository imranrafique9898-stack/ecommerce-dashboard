from bs4 import BeautifulSoup
import re

with open("ebay_page.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Find all divs that might contain item info
all_divs = soup.find_all("div")
print(f"Total divs: {len(all_divs)}")

# Search for price patterns
price_pattern = re.compile(r"\$[\d,]+\.\d{2}")
prices = price_pattern.findall(html[:100000])  # Check first 100k chars
print(f"Found {len(prices)} prices: {prices[:5]}")

# Search for common item-related classes
classes = set()
for tag in soup.find_all(class_=True):
    for class_name in tag.get("class", []):
        if any(word in class_name.lower() for word in ["item", "result", "product", "listing", "s-rec"]):
            classes.add(class_name)

print(f"\nClasses containing 'item', 'result', 'product', etc:")
for cls in sorted(classes)[:30]:
    print(f"  {cls}")

# Try finding elements with href containing item ID
links = soup.find_all("a", href=re.compile(r"/itm/"))
print(f"\nFound {len(links)} item links")
print(f"First few links:")
for link in links[:5]:
    print(f"  {link.get('href')[:80]}")

# Search for price elements
price_elements = soup.find_all(text=price_pattern)
print(f"\nFound {len(price_elements)} price elements")

# Check for specific structured data
scripts = soup.find_all("script", type="application/ld+json")
print(f"\nJSON-LD scripts: {len(scripts)}")
