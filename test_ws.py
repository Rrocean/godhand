#!/usr/bin/env python3
import asyncio
import websockets
import json

async def test():
    uri = "ws://127.0.0.1:8000/ws/test123"
    async with websockets.connect(uri) as ws:
        # 接收会话创建消息
        msg = await ws.recv()
        data = json.loads(msg)
        print(f"Session type: {data.get('type')}")
        
        # 发送指令
        await ws.send(json.dumps({"message": "打开画图然后画一个圆", "mode": "auto"}))
        
        # 接收所有消息
        for _ in range(10):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(msg)
                msg_type = data.get('type')
                print(f"\n[Type: {msg_type}]")
                
                if msg_type == 'parsed':
                    actions = data.get('actions', [])
                    print(f"Actions count: {len(actions)}")
                    for i, a in enumerate(actions[:5], 1):
                        desc = a.get('description', '')
                        print(f"  {i}. {a.get('type')}: {desc[:40] if desc else 'no desc'}")
                
                elif msg_type == 'executing':
                    print(f"Executing: {data.get('content', '')}")
                
                elif msg_type == 'done':
                    print("Done!")
                    break
                    
            except asyncio.TimeoutError:
                print("Timeout")
                break

asyncio.run(test())
