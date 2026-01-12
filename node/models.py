from pydantic import BaseModel, AnyHttpUrl, Field
from typing import Any, List

class PeerAddReq(BaseModel):
    me: AnyHttpUrl

class PeerList(BaseModel):
    peers: List[AnyHttpUrl] = Field(default_factory=list)

class WsMsg(BaseModel):
    type: str
    data: dict | None = None

class BlockModel(BaseModel):
    height: int
    prev_hash: str
    timestamp: int
    miner: str
    txs: List[Any] = []
    nonce: int
    hash: str

class ChainHeight(BaseModel):
    height: int
    tip: str

class BlockList(BaseModel):
    blocks: List[BlockModel]