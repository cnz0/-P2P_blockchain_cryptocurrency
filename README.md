## SimpleChain – Dockerized Blockchain Simulation with Proof-of-Work ##

SimpleChain is a distributed blockchain simulation implemented in Python.
It features asynchronous Proof-of-Work mining, UTXO-based transaction validation, fork resolution, and a CLI wallet with Ed25519 cryptography.
The project focuses on modeling core blockchain mechanisms, including consensus, networking, and state transitions across multiple nodes running in Docker.
This project was developed as part of a university course on distributed systems and blockchain technologies. It focuses on:
- Proof-of-Work consensus (hashcash-style)
- UTXO transaction model
- Fork handling and chain reorganization
- HTTP-based gossip protocol between nodes
- Asynchronous mining (non-blocking event loop)
- Wallet cryptography (Ed25519 + AES-GCM keystore)

## Features ##
### Node (Blockchain Layer) ###
Proof-of-Work (PoW):
- SHA-256 hashing
- Nonce brute-force
- Configurable difficulty (POW_DIFFICULTY)

UTXO Model:
- Input/output-based transactions
- Balance computed from unspent outputs

Chain Validation:
- Block structure validation
- PoW validation
- Height and hash consistency checks

Fork Handling:
- Multiple competing tips
- Longest-chain rule (by height)
- Automatic reorganization (rebuild UTXO on reorg)
- Orphan Block Pool

Asynchronous Mining:
- Mining loop runs as an asyncio task
- Does not block network API

Networking:
- HTTP-based P2P communication
- Gossip propagation of blocks and transactions
- Multi-node topology via Docker

### Wallet (CLI Layer) ###
- Ed25519 Key Pairs
- Address Generation (SHA-256 + Base58Check)

- Encrypted Keystore:
  - Password-based key derivation (Scrypt)
  - AES-256-GCM encryption

-Transaction Construction
- Message Signing & Verification
- CLI built using click

## Architecture ##

### Wallet ###
Wallet (CLI)
    ↓
HTTP
    ↓
Node (FastAPI)
    ↓
Blockchain State (ChainStore)

### Node flow ###
Transaction received
    ↓
UTXO validation
    ↓
Mempool
    ↓
Mining loop
    ↓
Block creation (PoW)
    ↓
Block validation
    ↓
Gossip to peers
    ↓
Fork resolution (if needed)
    ↓
UTXO rebuild (on reorg)

## Core Components ##
- chain.py – blockchain state, consensus, UTXO handling
- app.py – FastAPI node API and mining loop
- p2p.py – WebSocket-based broadcast layer
- tx.py – transaction data model
- keystore.py – encrypted wallet storage
- crypto.py – Ed25519 key operations
- docker-compose.yml – multi-node orchestration

## Consensus Model ##
- Proof-of-Work based on SHA-256 hash prefix matching
- Fixed difficulty (configurable via environment variables)
- Longest-chain rule based on block height
- No cumulative work calculation
- No dynamic difficulty adjustment

## Transaction Model ##
- UTXO-based accounting
- Coinbase transaction included in each mined block
- Inputs must exist in UTXO
- Total outputs <= total inputs
- Double-spend prevention via UTXO state

## Limitations / Future Work ##
- Signature verification layer implemented in wallet but not yet enforced at node consensus level
- Block-level transaction validation simplified (no full per-block UTXO snapshot simulation)
- Longest-chain selection based solely on height (not cumulative work)
- No dynamic difficulty adjustment
- Mining not parallelized across multiple CPU cores
- These limitations were intentional simplifications to focus on core consensus and state management mechanisms.

## Requirements ##
- Python 3.10+
- Docker & Docker Compose

## Running the Project ##

Start node network:
docker-compose up --build

This will:

- Start multiple blockchain nodes
- Connect them in predefined topology
- Enable mining (if configured via environment variables)

Example Workflow:

Initialize wallet:
```bash
python cli.py init
```
Get wallet address:
```bash
python cli.py address
```
Send transaction:
```bash
python cli.py send <recipient_address> <amount>
```
Query balance:
```bash
GET /balance?address=<address>
```
## What have I Learned ##
- Modeling distributed state machines
- Implementing Proof-of-Work consensus
- Handling blockchain forks and orphan blocks
- Rebuilding UTXO state after chain reorganization
- Designing modular separation between wallet and node

Using Docker to simulate multi-node distributed systems

Working with cryptographic primitives (Ed25519, AES-GCM, Scrypt)
