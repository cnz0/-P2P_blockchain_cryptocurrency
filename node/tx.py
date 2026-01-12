import json
import hashlib
from dataclasses import asdict, dataclass
from typing import List

from pydantic import BaseModel


@dataclass
class TxOut:
    address: str
    amount: int

@dataclass
class TxIn:
    txid: str
    index: int

@dataclass
class Transaction:
    txid: str
    inputs: list[TxIn]
    outputs: list[TxOut]
    signature: str | None = None
    pubkey: str | None = None

    def to_dict(self):
        return asdict(self)
    
    def from_dict(d):
        return Transaction(
            txid=d["txid"],
            inputs=[TxIn(**i) for i in d["inputs"]],
            outputs=[TxOut(**o) for o in d["outputs"]],
            signature=d.get("signature"),
            pubkey=d.get("pubkey"),
        )

class TxInModel(BaseModel):
    txid: str
    index: int

class TxOutModel(BaseModel):
    address: str
    amount: int

class TransactionModel(BaseModel):
    txid: str
    inputs: List[TxInModel]
    outputs: List[TxOutModel]
    
def compute_txid(tx: Transaction) -> str:
    payload = json.dumps({
        "inputs": [asdict(i) for i in tx.inputs],
        "outputs": [asdict(o) for o in tx.outputs],
    }, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()