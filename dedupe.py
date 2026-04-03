import json

data = json.load(open('ebay_clothing_products.json'))
seen = set()
unique = []
for item in data:
    id = item.get('item_id')
    if id and id not in seen:
        seen.add(id)
        unique.append(item)

print(f'Before: {len(data)}, After: {len(unique)}')
json.dump(unique, open('ebay_clothing_products_deduped.json', 'w'), indent=2)