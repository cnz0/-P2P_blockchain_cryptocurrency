from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import JSONResponse
import httpx
import asyncio
from models import PeerAddReq, PeerList, WsMsg, BlockModel, ChainHeight, BlockList
from settings import MINING_INTERVAL, NODE_HOST, STATE_FILE, WS_PATH, MINER, TOPOLOGY, NODE_NAME
from utils import PeerStore
from p2p import P2P
from chain import ChainStore, Block
from tx import Transaction, TransactionModel
import random

app = FastAPI(title="Stage3-Node")
peers = PeerStore(STATE_FILE)
p2p = P2P()
chain = ChainStore()

@app.on_event("startup")
async def startup():
    for peer_name in TOPOLOGY.get(NODE_NAME, []):
        peers.add(f"http://{peer_name}:8000")
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
        if MINER:
            asyncio.create_task(miner_loop())

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

@app.get("/chain/height", response_model=ChainHeight)
async def get_chain_height():
    tip = chain.tip()
    return ChainHeight(height=tip.height, tip=tip.hash)


@app.get("/chain/block/{height}", response_model=BlockModel)
async def get_block(height: int):
    b = chain.get_block(height)
    if not b:
        raise HTTPException(status_code=404, detail="block not found")
    return BlockModel(**b.to_dict())


@app.get("/chain/range", response_model=BlockList)
async def get_range(from_height: int = Query(0, ge=0)):
    blocks = [BlockModel(**b.to_dict()) for b in chain.all_from(from_height)]
    return BlockList(blocks=blocks)

@app.post("/gossip")
async def gossip(payload: dict):

    await p2p.broadcast({
        "type": "GOSSIP",
        "data": payload,
    })
    return {"ok": True, "relayed": payload}

@app.post("/blocks/new")
async def new_block(b: BlockModel):
    block = Block.from_dict(b.dict())

    # 1. Już mamy ten blok → ignorujemy
    if chain.has_hash(block.hash):
        return {"status": "duplicate"}

    local_height = chain.height()

    # 2. Idealny przypadek: następny blok w łańcuchu
    if not chain.validate_block(block):
        raise HTTPException(status_code=400, detail="invalid block")

    chain.add_block(block)
    # GOSSIP dalej (losowo)
    await gossip_block(block)
    return {"status": "accepted"}

    # 3. Stary blok
    if block.height <= local_height:
        return {"status": "stale"}

    # 4. Jesteśmy w tyle → synchronizacja
    synced = await sync_from_peers()
    if not synced:
        raise HTTPException(status_code=400, detail="too_far_ahead")

    local_height = chain.height()

    # 5. Po synchronizacji już mamy ten blok
    if chain.has_hash(block.hash) or block.height <= local_height:
        return {"status": "synced"}

    # 6. Możemy go teraz podpiąć
    if block.height == local_height + 1 and chain.tip().hash == block.prev_hash:
        if not chain.validate_block(block):
            raise HTTPException(status_code=400, detail="invalid block_after_sync")

        chain.add_block(block)

        # GOSSIP dalej
        await gossip_block(block)
        return {"status": "accepted_after_sync"}

    raise HTTPException(status_code=400, detail="cannot_connect_block")

GOSSIP_FANOUT = 2   # ilu peerów losowo wybieramy

async def gossip_block(block):
    peer_list = peers.list()
    if not peer_list:
        return

    # losowo wybieramy kilku sąsiadów
    k = min(GOSSIP_FANOUT, len(peer_list))
    targets = random.sample(peer_list, k)

    async with httpx.AsyncClient(timeout=5.0) as client:
        for p in targets:
            try:
                await client.post(f"{p}/blocks/new", json=block.to_dict())
            except Exception:
                pass
    
async def miner_loop():
    while True:
        txs = chain.mempool.copy()
        block = chain.make_next_block(txs=txs)

        if chain.validate_block(block):
            chain.add_block(block)
            chain.mempool.clear()

            print(f"[MINER] new block height={block.height}, hash={block.hash[:8]}")

            # GOSSIP zamiast broadcastu
            await gossip_block(block)

        await asyncio.sleep(MINING_INTERVAL)

async def sync_from_peers() -> bool:
    local_h = chain.height()
    best_peer = None
    best_height = local_h

    async with httpx.AsyncClient(timeout=5.0) as client:
        for p in peers.list():
            try:
                r = await client.get(f"{p}/chain/height")
                if r.status_code == 200:
                    h = r.json().get("height", 0)
                    if h > best_height:
                        best_height = h
                        best_peer = p
            except Exception:
                pass

        if best_peer is None or best_height <= local_h:
            return False

        try:
            r = await client.get(
                f"{best_peer}/chain/range",
                params={"from_height": local_h + 1},
            )
        except Exception:
            return False

        if r.status_code != 200:
            return False

        data = r.json()
        blocks = data.get("blocks", [])

        for b in blocks:
            blk = Block.from_dict(b)
            if chain.has_hash(blk.hash):
                continue
            if not chain.validate_block(blk):
                break
            chain.add_block(blk)

        return chain.height() > local_h

@app.post("/tx/new")
async def new_tx(tx_data: dict):
    tx = Transaction.from_dict(tx_data)

    # 1. Sprawdzenie poprawności transakcji względem UTXO
    if not chain.validate_tx(tx):
        raise HTTPException(status_code=400, detail="invalid transaction")

    # 2. Brak duplikatów w mempoolu
    if any(t.txid == tx.txid for t in chain.mempool):
        return {"status": "duplicate"}

    # 3. Dodanie do mempoolu
    chain.mempool.append(tx)

    return {"status": "accepted"}

@app.get("/balance")
def balance(address: str):
    return {
        "address": address,
        "balance": chain.balance_of(address)
    }

@app.get("/utxo")
def get_utxo(address: str):
    utxos = []
    for (txid, idx), o in chain.utxo.items():
        if o.address == address:
            utxos.append({
                "txid": txid,
                "index": idx,
                "amount": o.amount,
                "address": o.address
            })
    return {"utxos": utxos}

@app.post("/tx/new")
def new_tx(tx: TransactionModel):
    tx_obj = Transaction.from_dict(tx.dict())

    # Walidacja
    if not chain.validate_tx(tx_obj):
        raise HTTPException(status_code=400, detail="invalid transaction")

    # Dodaj do mempoola
    chain.mempool.append(tx_obj)

    return {"status": "accepted", "txid": tx_obj.txid}