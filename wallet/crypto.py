from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import hashes
import base58

def gen_keypair():
    sk = ed25519.Ed25519PrivateKey.generate()
    pk = sk.public_key()
    return sk, pk

def pubkey_bytes(pk) -> bytes:
    return pk.public_bytes(
        encoding=__import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.Raw,
        format=__import__("cryptography.hazmat.primitives.serialization", fromlist=["PublicFormat"]).PublicFormat.Raw,
    )

def privkey_bytes(sk) -> bytes:
    return sk.private_bytes(
        encoding=__import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.Raw,
        format=__import__("cryptography.hazmat.primitives.serialization", fromlist=["PrivateFormat"]).PrivateFormat.Raw,
        encryption_algorithm=__import__("cryptography.hazmat.primitives.serialization", fromlist=["NoEncryption"]).NoEncryption(),
    )

def address_from_pubkey(pk) -> str:
    digest = hashes.Hash(hashes.SHA256())
    digest.update(pubkey_bytes(pk))
    h = digest.finalize()
    return base58.b58encode_check(h)[:32].decode()

def sign(sk, message: bytes) -> bytes:
    return sk.sign(message)

def verify(pk, message: bytes, signature: bytes) -> bool:
    try:
        pk.verify(signature, message)
        return True
    except Exception:
        return False