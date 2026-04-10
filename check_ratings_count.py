import json
with open('ebay_items_full.json', encoding='utf-8') as f:
    data = json.load(f)

total = len(data)
has_feedback = sum(1 for i in data if i.get('seller_feedback'))
has_percent  = sum(1 for i in data if i.get('seller_feedback_percent'))

print('Total items          :', total)
print('Has feedback count   :', has_feedback, '| Missing:', total - has_feedback)
print('Has feedback percent :', has_percent,  '| Missing:', total - has_percent)
print()
print('Sample values (last 5):')
for item in data[-5:]:
    name = item.get('seller_name', '')[:25]
    fb   = item.get('seller_feedback', 'N/A')
    pct  = item.get('seller_feedback_percent', 'N/A')
    print(f'  {name:<25}  count: {fb:<12}  percent: {pct}')
