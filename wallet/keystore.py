import os, json, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from typing import Tuple

DEFAULT_PATH = os.path.expanduser("~/.simplechain/keystore.json")

def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = Scrypt(
        salt=salt,
        length=32,
        n=2**14,
        r=8,
        p=1,
    )
    return kdf.derive(password.encode())

def save_keystore(sk: ed25519.Ed25519PrivateKey, pubkey_b: bytes, password: str, path: str = DEFAULT_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)

    private_bytes = sk.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )

    #encrypted_sk = aesgcm.encrypt(nonce, private_bytes, None)
    ct = aesgcm.encrypt(nonce, private_bytes, None)

    data = {
        "kdf": "scrypt",
        "salt": base64.b64encode(salt).decode(),
        "cipher": "aes-256-gcm",
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ct).decode(),
        "pubkey": base64.b64encode(pubkey_b).decode(),
    }

    with open(path, "w") as f:
        json.dump(data, f)

def load_keystore(password: str, path: str = DEFAULT_PATH) -> Tuple[ed25519.Ed25519PrivateKey, bytes]:
    with open(path, "r") as f:
        data = json.load(f)
    salt = base64.b64decode(data["salt"])
    nonce = base64.b64decode(data["nonce"])
    ct = base64.b64decode(data["ciphertext"])
    key = _derive_key(password, salt)
    priv_raw = AESGCM(key).decrypt(nonce, ct, None)
    sk = ed25519.Ed25519PrivateKey.from_private_bytes(priv_raw)
    pubkey_b = base64.b64decode(data["pubkey"])
    return sk, pubkey_b
