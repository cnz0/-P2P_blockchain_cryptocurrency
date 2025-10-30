This is a 4-part project, which main purpose is to create a working private cryptocurrency for academic purposes.
Each part focuses on specific aspects of system, that is able to support cryptocurrencies.

#DONE 1. Peer to peer network and safe wallet. 

I did it, using Python Websockets and FastAPI, which helped me to establish connection between the peers. Whole project is
based in Docker. Each Node is a separate container, as is the Wallet. Dockerfile defines basic connections between
peers, after which each Node communicates with each other in order to propagate the known peer addresses among the network.

Wallet uses multiple algorithms in order to make sure, the Wallet is safe, user data is saved inside the Wallet container
which is supposed to be a "proto-user-app", so user credentials are stored safe outside the network.

Private Key generation: Ed-25519
Private Key encoding: User password based Scrypt and AES-GCM
Saving data: Base64
User unique address: Public key based SHA256 and Base58

#IN PROGRESS 2. Simple blockchain with one miner

