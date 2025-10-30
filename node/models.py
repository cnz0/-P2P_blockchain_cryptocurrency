from pydantic import BaseModel, AnyHttpUrl, Field
from typing import List

class PeerAddReq(BaseModel):
    me: AnyHttpUrl

class PeerList(BaseModel):
    peers: List[AnyHttpUrl] = Field(default_factory=list)

class WsMsg(BaseModel):
    type: str
    data: dict | None = None