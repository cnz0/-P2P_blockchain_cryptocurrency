from dataclasses import asdict, dataclass
import hashlib
import json
from typing import List

@dataclass
class TxIn:
    txid: str
    index: int

@dataclass
class TxOut:
    address: str
    amount: int

@dataclass
class Transaction:
    txid: str
    inputs: List[TxIn]
    outputs: List[TxOut]

    def to_dict(self):
        return {
            "txid": self.txid,
            "inputs": [i.__dict__ for i in self.inputs],
            "outputs": [o.__dict__ for o in self.outputs],
        }
    
def compute_txid(tx: Transaction) -> str:
    payload = json.dumps({
        "inputs": [asdict(i) for i in tx.inputs],
        "outputs": [asdict(o) for o in tx.outputs],
    }, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()