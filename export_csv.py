import json, csv

with open('ebay_items_full.json', encoding='utf-8') as f:
    data = json.load(f)

fields = [
    'item_id', 'product_name', 'category', 'price', 'original_price',
    'condition', 'seller_name', 'seller_feedback', 'seller_feedback_percent',
    'seller_location', 'image_urls', 'product_url', 'seller_description', 'scraped_at'
]

with open('ebay_items_backup.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
    w.writeheader()
    for item in data:
        row = dict(item)
        row['image_urls'] = ' | '.join(item.get('image_urls', []))
        specs = ' | '.join(f'{k}: {v}' for k,v in item.get('item_specifics', {}).items())
        row['seller_description'] = specs + ('\n' + item.get('seller_description','') if item.get('seller_description') else '')
        w.writerow(row)

print(f'Saved {len(data)} items to ebay_items_backup.csv')
