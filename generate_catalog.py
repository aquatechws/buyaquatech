import pandas as pd
import json, math

df = pd.read_excel('catalog.xlsx')
rows = df[df['Hidden'].astype(str).str.strip().str.upper() != 'YES']

products = []
for _, r in rows.iterrows():
    raw = r['BoxQty']
    if raw != raw or str(raw).strip() == '':
        box = ''
    else:
        box = int(raw) if isinstance(raw, float) and raw.is_integer() else raw
    products.append({
        'cat':  str(r['Section']).strip(),
        'code': str(r['SKU']).strip(),
        'name': str(r['Name']).strip(),
        'box':  box
    })

with open('catalog.js', 'w', encoding='utf-8') as f:
    f.write('window.CATALOG_DATA = ' + json.dumps(products, ensure_ascii=False) + ';')

print(f'catalog.js written — {len(products)} products')
