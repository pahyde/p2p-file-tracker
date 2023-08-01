import socket
import threading
import sys
import time
# import hashlib
import logging


# TODO: Implement P2PTracker

LOCAL_CHUNKS = 'LOCAL_CHUNKS'
WHERE_CHUNK = 'WHERE_CHUNK'

GET_CHUNK_FROM = 'GET_CHUNK_FROM'
CHUNK_LOCATION_UNKNOWN = 'CHUNK_LOCATION_UNKNOWN'


lock = threading.Lock()


class Logger:
    def __init__(self, filename):
        logging.basicConfig(filename=filename, format='%(message)s', filemode='a')
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)

    def get_chunk_from(self, index, hash, clients):
        message = f'P2PTracker,GET_CHUNK_FROM,{index},{hash}{clients}'
        self.logger.info(message)

    def chunk_location_unknown(self, index):
        message = f'P2PTracker,{CHUNK_LOCATION_UNKNOWN},{index}'
        self.logger.info(message)

    def _use_local_host(self, ip):
        if ip == '127.0.0.1':
            return 'localhost'
        return ip


class ClientSocket:
    def __init__(self, client_socket, client_address):
        self.socket = client_socket
        self.address = client_address

    def send(self, message):
        payload = message.encode('utf-8')
        self.socket.send(payload)

    def recv(self):
        return self.socket.recv(512).decode('utf-8')


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
        with lock:
            if self.is_verified(index):
                self.chunk_in(index, candidate)
                return
            self._check_in(index, candidate)
            majority = self.hash_majority(index)
            if majority is not None:
                candidates = self.check_list[index]
                self.add_new_chunk(index, candidates, majority)

    def chunk_in(self, index, candidate):
        client = Client(candidate.ip, candidate.port)
        self.chunk_list[index].client_list.append(client)

    def add_new_chunk(self, index, candidates, hash):
        clients = [Client(c.ip, c.port) for c in candidates if c.hash == hash]
        self.chunk_list[index] = Chunk(clients, hash)

    def get_chunk(self, index):
        #with lock:
        if index not in self.chunk_list:
            return None
        return self.chunk_list[index]

    def is_verified(self, index):
        return index in self.chunk_list

    def hash_majority(self, index):
        if index not in self.check_list:
            return False
        count = {}
        for candidate in self.check_list[index]:
            hash = candidate.hash
            count[hash] = count.get(hash, 0) + 1
            if count[hash] == 2:
                return hash
        return None

    def _check_in(self, index, candidate):
        if index not in self.check_list:
            self.check_list[index] = []
        self.check_list[index].append(candidate)

    def __repr__(self):
        return f'{self.check_list}\n\n{self.chunk_list}\n\n\n'


tracker = ChunkTracker()
logger = Logger('logs.log')


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
        logger.chunk_location_unknown(index)
        return
    chunk = tracker.get_chunk(index)
    clients = ''.join(f',{client.ip},{client.port}'
                      for client in chunk.client_list)
    client.send(f'{GET_CHUNK_FROM},{index},{chunk.hash}{clients}')
    logger.get_chunk_from(index, chunk.hash, clients)


def handle_client_connection(client_socket, client_address):
    client = ClientSocket(client_socket, client_address)
    while True:
        time.sleep(1)
        request = client.recv()
        if not request:
            break
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
    start_tracker('localhost', 5100)
