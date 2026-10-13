import asyncio
import websockets

async def test():
    async with websockets.connect("ws://127.0.0.1:8765") as ws:
        print("Connected to WebSocket server")
        message = await asyncio.wait_for(ws.recv(), timeout=15)
        print("Received:", message)

asyncio.run(test())