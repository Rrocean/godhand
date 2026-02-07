#!/usr/bin/env python3
import sys
sys.path.insert(0, './core')

from smart_parser_v2 import SmartParserV2, HAS_LLM
from ghost_v3 import LLMClient
import json

with open('config.json', 'r') as f:
    config = json.load(f)

llm = LLMClient(config=config)
parser = SmartParserV2(llm_client=llm)

cmd = '打开画图，画一个红色的圆'
print(f'Testing: {cmd}')
print('=' * 50)

actions, intent = parser.parse(cmd)
print(f'\nIntent: {intent.category.value}, Confidence: {intent.confidence:.2f}')
print(f'Actions count: {len(actions)}')

for i, a in enumerate(actions, 1):
    print(f'\n{i}. Type: {a.type.value}')
    print(f'   Desc: {a.description}')
    print(f'   Params: {a.params}')
