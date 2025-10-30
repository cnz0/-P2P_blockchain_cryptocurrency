import os

NODE_PORT = int(os.getenv("NODE_PORT", 8000))
NODE_HOST = os.getenv("NODE_HOST", f"http://localhost:{NODE_PORT}")
KNOWN_PEERS = [p.strip() for p in os.getenv("KNOWN_PEERS", "").split(",") if p.strip()]
STATE_FILE = os.getenv("STATE_FILE", "/data/peers.json")
WS_PATH = "/ws"