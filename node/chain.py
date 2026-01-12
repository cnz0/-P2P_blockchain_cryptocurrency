import json
import time
import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional
from settings import CHAIN_FILE, MINER_ADDRESS, NODE_HOST, POW_DIFFICULTY
from tx import compute_txid, Transaction, TxOut

@dataclass
class Block:
    height: int
    prev_hash: str
    timestamp: int
    miner: str
    txs: list
    nonce: int
    hash: str

    @staticmethod
    def compute_hash(height: int, prev_hash: str, timestamp: int, miner: str, txs: list, nonce: int) -> str:
        header = json.dumps(
            {
                "height": height,
                "prev_hash": prev_hash,
                "timestamp": timestamp,
                "miner": miner,
                "txs": [asdict(tx) for tx in txs],
                "nonce": nonce,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(header).hexdigest()
    
    @classmethod
    def genesis(cls) -> "Block":
        height = 0
        prev_hash = ""
        timestamp = 0
        miner = "GENESIS"
        txs: list = []
        nonce = 0
        h = cls.compute_hash(height, prev_hash, timestamp, miner, txs, nonce)
        return cls(
            height=height,
            prev_hash=prev_hash,
            timestamp=timestamp,
            miner=miner,
            txs=txs,
            nonce=nonce,
            hash=h,
        )
    
    @classmethod
    def from_dict(cls, data: dict) -> "Block":
        return cls(
            height=data["height"],
            prev_hash=data["prev_hash"],
            timestamp=data["timestamp"],
            miner=data["miner"],
            txs=[Transaction.from_dict(tx) for tx in data["txs"]],
            nonce=data.get("nonce", 0),
            hash=data["hash"],
        )
    
    def to_dict(self) -> dict:
        return asdict(self)
    
class ChainStore:
    def __init__(self, path: str = CHAIN_FILE):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._chain: List[Block] = []
        self._by_hash: dict[str, Block] = {}
        self.utxo = {}
        self.mempool = []
        self.load()
        self._rebuild_utxo()

    def load(self):
        if self.path.exists():
            raw = json.loads(self.path.read_text())
            self._chain = [Block.from_dict(b) for b in raw]
        else:
            g = Block.genesis()
            self._chain = [g]
            self.save()

        self._by_hash = {b.hash: b for b in self._chain}

    def save(self):
        raw = [b.to_dict() for b in self._chain]
        self.path.write_text(json.dumps(raw, indent=2))

    def tip(self) -> Block:
        return self._chain[-1]
    
    def height(self) -> int:
        return self._chain[-1].height
    
    def has_hash(self, h: str) -> bool:
        return h in self._by_hash
    
    def get_block(self, height: int) -> Optional[Block]:
        if 0 <= height < len(self._chain):
            return self._chain[height]
        return None
    
    def all_from(self, start_height: int) -> List[Block]:
        return self._chain[start_height:]
    
    def append(self, block: Block):
        self._chain.append(block)
        self._by_hash[block.hash] = block
        for tx in block.txs:
            self._apply_tx_to_utxo(tx, self.utxo)
        self.save()

    def make_next_block(self, txs: Optional[list] = None) -> Block:
        if txs is None:
            txs = []

        tip = self.tip()
        height = tip.height + 1
        prev_hash = tip.hash
        timestamp = int(time.time())
        miner = NODE_HOST

        # Coinbase
        coinbase = Transaction(
            txid="",
            inputs=[],
            outputs=[TxOut(address=MINER_ADDRESS, amount=50)]
        )
        coinbase.txid = hashlib.sha256(f"{height}{miner}{timestamp}".encode()).hexdigest()

        txs = [coinbase] + txs

        prefix = "0" * POW_DIFFICULTY
        nonce = 0

        while True:
            h = Block.compute_hash(height, prev_hash, timestamp, miner, txs, nonce)
            if h.startswith(prefix):
                break
            nonce += 1

        return Block(height, prev_hash, timestamp, miner, txs, nonce, h)
    
    def validate_next(self, block: Block) -> bool:
        tip = self.tip()

        # 1. PoW
        if not block.hash.startswith("0" * POW_DIFFICULTY):
            return False

        # 2. Wysokość i powiązanie
        if block.height != tip.height + 1:
            return False
        if block.prev_hash != tip.hash:
            return False

        # 3. Hash poprawny
        expected_hash = Block.compute_hash(
            block.height,
            block.prev_hash,
            block.timestamp,
            block.miner,
            block.txs,
            block.nonce,
        )
        if block.hash != expected_hash:
            return False

        # 4. Czas
        if block.timestamp < tip.timestamp:
            return False

        # 5. Coinbase jako pierwsza
        if len(block.txs) == 0 or len(block.txs[0].inputs) != 0:
            return False

        # 6. Walidacja transakcji na kopii UTXO
        temp_utxo = self.utxo.copy()
        for tx in block.txs:
            if not self.validate_tx_against_utxo(tx, temp_utxo):
                return False
            self._apply_tx_to_utxo(tx, temp_utxo)

        return True
    
    def _rebuild_utxo(self):
        self.utxo = {}
        for block in self._chain:
            for tx in block.txs:
                self._apply_tx_to_utxo(tx, self.utxo)

    def _apply_tx(self, tx):
        # usuń wydane UTXO
        for i in tx.inputs:
            key = (i.txid, i.index)
            if key in self.utxo:
                del self.utxo[key]

        # dodaj nowe UTXO
        for idx, o in enumerate(tx.outputs):
            self.utxo[(tx.txid, idx)] = o

    def balance_of(self, address: str) -> int:
        total = 0
        for utxo in self.utxo.values():
            if utxo.address == address:
                total += utxo.amount
        return total
    
    def validate_tx(self, tx: Transaction) -> bool:
        # Coinbase
        if len(tx.inputs) == 0:
            return True

        total_in = 0
        for i in tx.inputs:
            key = (i.txid, i.index)
            if key not in self.utxo:
                return False
            total_in += self.utxo[key].amount

        total_out = sum(o.amount for o in tx.outputs)
        if total_out > total_in:
            return False

        return True
    
    def validate_tx_against_utxo(self, tx, utxo: dict) -> bool:
        # Coinbase: brak inputów -> zawsze poprawna
        if len(tx.inputs) == 0:
            return True

        total_in = 0

        for i in tx.inputs:
            key = (i.txid, i.index)
            if key not in utxo:
                return False   # próba wydania czegoś, czego nie ma

            total_in += utxo[key].amount

        total_out = sum(o.amount for o in tx.outputs)

        # nie można wydać więcej niż się ma
        if total_out > total_in:
            return False

        return True
    
    def _apply_tx_to_utxo(self, tx, utxo: dict):
        # usuń wydane wyjścia
        for i in tx.inputs:
            key = (i.txid, i.index)
            if key in utxo:
                del utxo[key]

        # dodaj nowe wyjścia jako UTXO
        for idx, o in enumerate(tx.outputs):
            utxo[(tx.txid, idx)] = o