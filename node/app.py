from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import httpx
from models import PeerAddReq, PeerList
from settings import NODE_HOST, KNOWN_PEERS, STATE_FILE, WS_PATH
from utils import PeerStore
from p2p import P2P

app = FastAPI(title="Stage1-Node")
peers = PeerStore(STATE_FILE)
p2p = P2P()

@app.on_event("startup")
async def startup():
    for p in KNOWN_PEERS:
        peers.add(p)
    async with httpx.AsyncClient(timeout=5.0) as client:
        for p in peers.list():
            try:
                r = await client.post(f"{p}/peers/add", json={"me": NODE_HOST})
                if r.status_code == 200:
                    their = r.json().get("peers", [])
                    for tp in their:
                        if tp != NODE_HOST:
                            peers.add(tp)
            except Exception:
                pass

@app.get("/health")
async def health():
    return {"status": "ok", "host": NODE_HOST}  

@app.get("/peers", response_model=PeerList)
async def get_peers():
    return PeerList(peers=peers.list())

@app.post("/peers/add", response_model=PeerList)
async def add_peer(req: PeerAddReq):
    if req.me and req.me != NODE_HOST:
        peers.add(str(req.me))
    return PeerList(peers=peers.list())

@app.websocket(WS_PATH)
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    await p2p.register(ws)
    try:
        while True:
            _ = await ws.receive_text()
    except WebSocketDisconnect:
        await p2p.unregister(ws)

@app.post("/gossip")
async def gossip(payload: dict):

    await p2p.broadcast({
        "type": "GOSSIP",
        "data": payload,
    })
    return {"ok": True, "relayed": payload}