#!/usr/bin/env python3
import requests
import json

resp = requests.post(
    'http://127.0.0.1:8000/api/parse',
    json={'command': '打开画图，画一个红色的圆'},
    timeout=30
)

data = resp.json()
print(f"Actions count: {len(data['actions'])}")
print(f"Intent: {data['intent']}")
print("\nFirst 5 actions:")
for i, a in enumerate(data['actions'][:5], 1):
    print(f"{i}. {a['type']}: {a['description'][:40]}")
