import json
from pathlib import Path
from typing import Set

class PeerStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._peers: Set[str] = set()
        self.load()

    def load(self):
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text())
                self._peers = set(p.rstrip("/") for p in loaded)
                self.save()
            except Exception:
                self._peers = set()

    def save(self):
        self.path.write_text(json.dumps(sorted(self._peers)))

    def add(self, peer: str):
        if peer:
            norm = peer.rstrip("/")
            self._peers.add(norm)
            self.save()

    def update_many(self, peers: list[str]):
        for p in peers:
            self._peers.add(p.rstrip("/"))
        self.save()

    def remove(self, peer: str):
        self._peers.discard(peer)
        self.save()

    def list(self) -> list[str]:
        return sorted(self._peers)