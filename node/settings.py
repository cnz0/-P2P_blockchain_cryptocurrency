import os

NODE_PORT = int(os.getenv("NODE_PORT", 8000))
NODE_HOST = os.getenv("NODE_HOST", f"http://localhost:{NODE_PORT}")
NODE_NAME = os.getenv("NODE_NAME", "node1")
TOPOLOGY = {
    "node1": ["node2"],
    "node2": ["node1", "node3"],
    "node3": ["node2"],
}
STATE_FILE = os.getenv("STATE_FILE", "/data/peers.json")
WS_PATH = "/ws"
CHAIN_FILE = os.getenv("CHAIN_FILE", "/data/chain.json")
MINER = os.getenv("MINER", "0") == "1"
MINING_INTERVAL = int(os.getenv("MINING_INTERVAL", "10"))
POW_DIFFICULTY = int(os.getenv("POW_DIFFICULTY", "4"))