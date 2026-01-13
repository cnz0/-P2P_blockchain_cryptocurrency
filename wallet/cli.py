import os, json, base64, click
from cryptography.hazmat.primitives.asymmetric import ed25519
from crypto import gen_keypair, pubkey_bytes, address_from_pubkey, sign, verify
from keystore import save_keystore, load_keystore, DEFAULT_PATH
from tx import Transaction, TxIn, TxOut, compute_txid
import requests


@click.group()
def cli():
    """Wallet (Stage 3)"""


@cli.command()
@click.option("--path", default=DEFAULT_PATH, help="Keystore file path")
@click.password_option(prompt=True, confirmation_prompt=True)
def init(password, path):
    sk, pk = gen_keypair()
    save_keystore(sk, pubkey_bytes(pk), password, path)
    addr = address_from_pubkey(pk)
    click.echo(f"Created wallet. Address: {addr}\nKeystore: {path}")


@cli.command()
@click.option("--path", default=DEFAULT_PATH)
@click.password_option(prompt=True)
def address(password, path):
    sk, pub_b = load_keystore(password, path)
    pk = ed25519.Ed25519PublicKey.from_public_bytes(pub_b)
    click.echo(address_from_pubkey(pk))


@cli.command()
@click.argument("message")
@click.option("--path", default=DEFAULT_PATH)
@click.password_option(prompt=True)
def signmsg(message, password, path):
    sk, pub_b = load_keystore(password, path)
    sig = sk.sign(message.encode())
    click.echo(base64.b64encode(sig).decode())


@cli.command()
@click.argument("message")
@click.argument("signature")
@click.option("--path", default=DEFAULT_PATH)
def verifymessage(message, signature, path):
    with open(path) as f:
        pub_b = json.load(f)["pubkey"]
    pk = ed25519.Ed25519PublicKey.from_public_bytes(base64.b64decode(pub_b))
    try:
        pk.verify(base64.b64decode(signature), message.encode())
        click.echo("VALID")
    except Exception:
        click.echo("INVALID", err=True)

@cli.command()
@click.argument("to")
@click.argument("amount", type=int)
@click.option("--node", default="http://node1:8000")
@click.option("--path", default=DEFAULT_PATH)
@click.password_option(prompt=True)
def send(to, amount, node, password, path):
    sk, pub_b = load_keystore(password, path)
    pk = ed25519.Ed25519PublicKey.from_public_bytes(pub_b)
    from_addr = address_from_pubkey(pk)

    r = requests.get(f"{node}/utxo", params={"address": from_addr})
    utxos = r.json()["utxos"]

    total = 0
    inputs = []
    for u in utxos:
        inputs.append(TxIn(txid=u["txid"], index=u["index"]))
        total += u["amount"]
        if total >= amount:
            break

    if total < amount:
        click.echo("Not enough funds", err=True)
        return

    outputs = [TxOut(address=to, amount=amount)]
    change = total - amount
    if change > 0:
        outputs.append(TxOut(address=from_addr, amount=change))

    tx = Transaction(txid="", inputs=inputs, outputs=outputs)
    tx.txid = compute_txid(tx)

    r = requests.post(f"{node}/tx/new", json=tx.to_dict())
    if r.status_code == 200:
        click.echo(f"Transaction sent. TXID={tx.txid}")
    else:
        click.echo(f"Error: {r.text}", err=True)


if __name__ == "__main__":
    cli()