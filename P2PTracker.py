import socket
import threading
import sys
# import hashlib
# import time
# import logging


# TODO: Implement P2PTracker

LOCAL_CHUNKS = 'LOCAL_CHUNKS'
WHERE_CHUNK = 'WHERE_CHUNK'

GET_CHUNK_FROM = 'GET_CHUNK_FROM'
CHUNK_LOCATION_UNKNOWN = 'CHUNK_LOCATION_UNKNOWN'


class ClientSocket:
    def __init__(self, client_socket, client_address):
        self.socket = client_socket
        self.address = client_address

    def send(self, message):
        payload = message.encode('utf-8')
        header = len(payload).to_bytes(4, 'big')
        self.socket.send(header + payload)

    def recv(self):
        header = self.socket.recv(4)
        payload_len = int.from_bytes(header, 'big')
        return self.socket.recv(payload_len).decode('utf-8')


class Client:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port


class ChunkCandidate:
    def __init__(self, hash, ip, port):
        self.hash = hash
        self.ip = ip
        self.port = port


class Chunk:
    def __init__(self, client_list, hash):
        self.client_list = client_list
        self.hash = hash


class ChunkTracker:
    def __init__(self):
        self.check_list = {}
        self.chunk_list = {}

    def check_in(self, index, candidate):
        if self.is_verified(index):
            self.chunk_in(index, candidate)
            return
        self._check_in(index, candidate)
        if self.has_hash_majority(index):
            self.add_new_chunk(index, candidate)

    def chunk_in(self, index, candidate):
        client = Client(candidate.ip, candidate.port)
        self.chunk_list[index].client_list.append(client)

    def add_new_chunk(self, index, candidate):
        client = Client(candidate.ip, candidate.port)
        self.chunk_list[index] = Chunk([client], candidate.hash)

    def get_chunk(self, index):
        if index not in self.chunk_list:
            return None
        return self.chunk_list[index]

    def is_verified(self, index):
        return index in self.chunk_list

    def has_hash_majority(self, index):
        if index not in self.check_list:
            return False
        count = {}
        for candidate in self.check_list[index]:
            hash = candidate.hash
            count[hash] = count.get(hash, 0) + 1
            if count[hash] == 2:
                return True
        return False

    def _check_in(self, index, candidate):
        if index not in self.check_list:
            self.check_list[index] = []
        self.check_list[index].append(candidate)


tracker = ChunkTracker()


def create_tracker_socket(host, port):
    tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tracker_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tracker_socket.bind((host, port))
    tracker_socket.listen()
    return tracker_socket


def handle_local_chunks(client, request_tokens):
    index, hash, ip, port = request_tokens[1:]
    candidate = ChunkCandidate(hash, ip, port)
    tracker.check_in(index, candidate)


def handle_where_chunk(client, request_tokens):
    index = request_tokens[1]
    if not tracker.is_verified(index):
        client.send(f'{CHUNK_LOCATION_UNKNOWN},{index}')
        return
    chunk = tracker.get_chunk(index)
    clients = ''.join(f'{client.ip}{client.port}'
                      for client in chunk.client_list)
    client.send(f'{GET_CHUNK_FROM}{index}{chunk.hash}{clients}')


def handle_client_connection(client_socket, client_address):
    client = ClientSocket(client_socket, client_address)
    while True:
        request = client.recv()
        if not request:
            break
        print(f'received message: {request}')
        request_tokens = request.strip().split(',')
        request_type = request_tokens[0]
        if request_type == LOCAL_CHUNKS:
            handle_local_chunks(client, request_tokens)
        elif request_type == WHERE_CHUNK:
            handle_where_chunk(client, request_tokens)
        else:
            # Launch the missiles
            print('BAD REQUEST TYPE')
            pass
    client_socket.close()


def start_tracker(host, port):
    tracker_socket = create_tracker_socket(host, port)
    while True:
        client_socket, client_address = tracker_socket.accept()
        threading.Thread(
            target=handle_client_connection,
            args=(client_socket, client_address)
        ).start()


if __name__ == "__main__":
    start_tracker('127.0.0.1', 5001)
