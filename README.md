# P2P File Tracker

This repository contains a simple implementation of a Peer-to-Peer (P2P) file tracker system. The system is designed to distribute chunks of files across a network of peers and keep track of which peer has which chunk.

## Structure

The repository contains the following main components:

- `P2PClient.py`: This script implements the client-side logic of the P2P system. It is responsible for checking in local chunks to the tracker, requesting missing chunks from other peers, and listening for incoming chunk requests from other peers.

- `P2PTracker.py`: This script implements the tracker-side logic of the P2P system. It maintains a list of chunks and their locations (i.e., which peers have them), and responds to chunk location queries from clients.

- `active` and `backup` directories: These directories simulate different peers in the network, each containing different chunks of files.


## Usage

To start a client, run the `P2PClient.py` script with the following arguments:

- `-folder`: The directory that the client should use to store its chunks.
- `-transfer_port`: The port that the client should use for P2P transfers.
- `-name`: The name of the client.

Example:

```bash
python P2PClient.py -folder active/folder1 -transfer_port 5001 -name Client1
```