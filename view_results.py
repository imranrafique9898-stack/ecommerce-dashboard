"""
Live results viewer for ebay_items_full.json
Run: python view_results.py
"""
import json, os, time, sys

FILE = "ebay_items_full.json"
REFRESH = 5  # seconds between refreshes

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def load():
    try:
        with open(FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def display(data):
    clear()
    cats = {}
    for item in data:
        cats[item["category"]] = cats.get(item["category"], 0) + 1

    print("=" * 70)
    print(f"  eBay Scraper — Live Results   ({FILE})")
    print(f"  Total items collected: {len(data)}")
    print("=" * 70)

    print("\n  By Category:")
    for cat, count in cats.items():
        bar = "█" * min(count, 40)
        print(f"    {cat:<28} {bar} {count}")

    print(f"\n  Last 10 items scraped:")
    print("  " + "─" * 66)
    for item in data[-10:]:
        name  = item.get("product_name", "")[:45]
        price = item.get("price", "N/A")
        cond  = item.get("condition", "")[:20]
        seller= item.get("seller_name", "")[:22]
        loc   = item.get("seller_location", "")[:30]
        imgs  = len(item.get("image_urls", []))
        specs = len(item.get("item_specifics", {}))
        print(f"  {name:<46} {price:>8}")
        print(f"    Condition: {cond:<22} Seller: {seller}")
        print(f"    Location:  {loc:<30} Images: {imgs}  Specifics: {specs}")
        print()

    print(f"  Refreshing every {REFRESH}s — Ctrl+C to quit")

# one-shot mode: python view_results.py once
if len(sys.argv) > 1 and sys.argv[1] == "once":
    display(load())
else:
    try:
        while True:
            display(load())
            time.sleep(REFRESH)
    except KeyboardInterrupt:
        print("\n  Viewer stopped.")
