import os, json, base64, click
from cryptography.hazmat.primitives.asymmetric import ed25519
from crypto import gen_keypair, pubkey_bytes, address_from_pubkey, sign, verify
from keystore import save_keystore, load_keystore, DEFAULT_PATH


@click.group()
def cli():
    """Wallet (Stage 1)"""


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


if __name__ == "__main__":
    cli()