import asyncio
import json
from typing import Set
from starlette.websockets import WebSocket


class P2P:
    def __init__(self):
        self.connections: Set[WebSocket] = set()

    async def register(self, ws: WebSocket):
        self.connections.add(ws)

    async def unregister(self, ws: WebSocket):
        self.connections.discard(ws)

    async def broadcast(self, msg: dict):
        if not self.connections:
            return
        data = json.dumps(msg)
        dead = []
        for ws in list(self.connections):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.connections.discard(ws)