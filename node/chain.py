import json
import time
import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional
from settings import CHAIN_FILE, MALICIOUS, MINER_ADDRESS, NODE_HOST, POW_DIFFICULTY
from tx import compute_txid, Transaction, TxOut

# =======================
# ====== BLOCK =========
# =======================

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
    def compute_hash(height, prev_hash, timestamp, miner, txs, nonce):
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
    def genesis(cls):
        height = 0
        prev_hash = ""
        timestamp = 0
        miner = "GENESIS"
        txs = []
        nonce = 0
        h = cls.compute_hash(height, prev_hash, timestamp, miner, txs, nonce)
        return cls(height, prev_hash, timestamp, miner, txs, nonce, h)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            height=data["height"],
            prev_hash=data["prev_hash"],
            timestamp=data["timestamp"],
            miner=data["miner"],
            txs=[Transaction.from_dict(tx) for tx in data["txs"]],
            nonce=data["nonce"],
            hash=data["hash"],
        )

    def to_dict(self):
        return asdict(self)


# =======================
# ===== CHAINSTORE =====
# =======================

class ChainStore:
    def __init__(self, path: str = CHAIN_FILE):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.blocks = {}          # hash -> Block
        self.children = {}        # hash -> list of child hashes
        self.tips = set()         # set of current tips
        self.orphans = {}         # prev_hash -> list of blocks
        self.best_tip = None

        self.utxo = {}
        self.mempool = []

        self.load()

    # =======================
    # ===== PERSISTENCE ====
    # =======================

    def load(self):
        if self.path.exists():
            raw = json.loads(self.path.read_text())
            blocks = [Block.from_dict(b) for b in raw]
        else:
            blocks = [Block.genesis()]
            self.save(blocks)

        # odbuduj graf
        for b in blocks:
            self._add_block_internal(b)

        self._recalculate_best_chain()

    def save(self, blocks=None):
        if blocks is None:
            blocks = self.blocks.values()
        raw = [b.to_dict() for b in blocks]
        self.path.write_text(json.dumps(raw, indent=2))

    # =======================
    # ===== BASIC API ======
    # =======================

    def has_hash(self, h: str) -> bool:
        return h in self.blocks

    def tip(self) -> Block:
        return self.blocks[self.best_tip]

    def height(self) -> int:
        return self.tip().height

    # =======================
    # ===== ADD BLOCK ======
    # =======================

    def add_block(self, block: Block) -> bool:
        # duplikat
        if block.hash in self.blocks:
            return False

        # orphan?
        if block.prev_hash not in self.blocks:
            self.orphans.setdefault(block.prev_hash, []).append(block)
            print(f"[ORPHAN] {block.hash[:8]} waiting for {block.prev_hash[:8]}")
            return False

        # walidacja względem rodzica
        if not self._validate_block(block):
            print("[INVALID BLOCK]")
            return False

        self._add_block_internal(block)

        # sprawdź czy ktoś na niego nie czekał
        self._process_orphans(block.hash)

        # przelicz najlepszy łańcuch
        self._recalculate_best_chain()
        return True

    def _add_block_internal(self, block: Block):
        self.blocks[block.hash] = block
        self.children.setdefault(block.prev_hash, []).append(block.hash)

        # aktualizacja tips
        if block.prev_hash in self.tips:
            self.tips.remove(block.prev_hash)
        self.tips.add(block.hash)

        # pierwszy blok
        if self.best_tip is None:
            self.best_tip = block.hash

    # =======================
    # ===== VALIDATION =====
    # =======================

    def _validate_block(self, block: Block) -> bool:
        parent = self.blocks.get(block.prev_hash)
        if not parent:
            return False

        # PoW
        if not block.hash.startswith("0" * POW_DIFFICULTY):
            return False

        # wysokość
        if block.height != parent.height + 1:
            return False

        # hash
        expected = Block.compute_hash(
            block.height,
            block.prev_hash,
            block.timestamp,
            block.miner,
            block.txs,
            block.nonce,
        )
        if block.hash != expected:
            return False

        # coinbase jako pierwsza
        if len(block.txs) == 0 or len(block.txs[0].inputs) != 0:
            return False

        return True
    
    def validate_block(self, block: Block) -> bool:
        return self._validate_block(block)

    # =======================
    # ===== ORPHANS ========
    # =======================

    def _process_orphans(self, parent_hash: str):
        if parent_hash not in self.orphans:
            return

        waiting = self.orphans.pop(parent_hash)
        for block in waiting:
            print(f"[ORPHAN RESOLVED] {block.hash[:8]}")
            self.add_block(block)

    # =======================
    # ===== CONSENSUS ======
    # =======================

    def _recalculate_best_chain(self):
        if not self.tips:
            return

        # wybierz najdłuższy łańcuch (max height)
        best = None
        best_height = -1

        for tip_hash in self.tips:
            h = self.blocks[tip_hash].height
            if h > best_height:
                best_height = h
                best = tip_hash

        if best != self.best_tip:
            print(f"[REORG] new best tip {best[:8]} height={best_height}")
            self.best_tip = best
            self._rebuild_utxo()

    # =======================
    # ===== UTXO ===========
    # =======================

    def _rebuild_utxo(self):
        print("[UTXO] rebuilding for best chain")
        self.utxo = {}

        chain = self._get_chain_to_genesis(self.best_tip)
        for block in chain:
            for tx in block.txs:
                self._apply_tx_to_utxo(tx, self.utxo)

    def _get_chain_to_genesis(self, tip_hash: str) -> List[Block]:
        chain = []
        cur = self.blocks[tip_hash]
        while cur.prev_hash:
            chain.append(cur)
            cur = self.blocks[cur.prev_hash]
        chain.append(cur)  # genesis
        return list(reversed(chain))

    def balance_of(self, address: str) -> int:
        total = 0
        for utxo in self.utxo.values():
            if utxo.address == address:
                total += utxo.amount
        return total

    def _apply_tx_to_utxo(self, tx, utxo: dict):
        for i in tx.inputs:
            key = (i.txid, i.index)
            if key in utxo:
                del utxo[key]

        for idx, o in enumerate(tx.outputs):
            utxo[(tx.txid, idx)] = o

    # =======================
    # ===== MINING =========
    # =======================

    def make_next_block(self, txs: Optional[list] = None) -> Block:
        if txs is None:
            txs = []

        parent = self.blocks[self.best_tip]
        if MALICIOUS:
            # złośliwy: kop na starym bloku (np. cofnij się o 2)
            for _ in range(2):
                if parent.prev_hash:
                    parent = self.blocks[parent.prev_hash]
        height = parent.height + 1
        prev_hash = parent.hash
        timestamp = int(time.time())
        miner = NODE_HOST

        # Coinbase
        coinbase = Transaction(
            txid="",
            inputs=[],
            outputs=[TxOut(address=MINER_ADDRESS, amount=50)]
        )
        coinbase.txid = compute_txid(coinbase)

        txs = [coinbase] + txs

        prefix = "0" * POW_DIFFICULTY
        nonce = 0

        while True:
            h = Block.compute_hash(height, prev_hash, timestamp, miner, txs, nonce)
            if h.startswith(prefix):
                break
            nonce += 1

        return Block(height, prev_hash, timestamp, miner, txs, nonce, h)