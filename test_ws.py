#!/usr/bin/env python3
import asyncio
import websockets
import json

async def test():
    uri = "ws://127.0.0.1:8000/ws/test123"
    async with websockets.connect(uri) as ws:
        # 接收会话创建消息
        msg = await ws.recv()
        print(f"Session: {json.loads(msg)}")
        
        # 发送指令
        await ws.send(json.dumps({"message": "打开画图然后画一个圆", "mode": "auto"}))
        
        # 接收所有消息
        for _ in range(10):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(msg)
                print(f"Type: {data.get('type')}")
                if data.get('actions'):
                    print(f"Actions count: {len(data['actions'])}")
                    for i, a in enumerate(data['actions'][:3], 1):
                        print(f"  {i}. {a.get('type')}: {a.get('description', '')[:30]}")
                if data.get('type') == 'done':
                    break
            except asyncio.TimeoutError:
                break

asyncio.run(test())
