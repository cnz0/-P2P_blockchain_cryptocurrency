import asyncio
import websockets

async def main():
    uri = "ws://localhost:8002/ws"
    async with websockets.connect(uri) as ws:
        print("Polaczono z node2:", uri)
        while True:
            msg = await ws.recv()
            print(msg)

asyncio.run(main())