import socket
import argparse
import os
import hashlib
import threading
import random
import time

from collections import deque
# import sys
# import logging


# TODO: Implement P2PClient that connects to P2PTracker


REQUEST_CHUNK = 'REQUEST_CHUNK'


class Chunk:
    def __init__(self, index, file_hash):
        self.index = index
        self.file_hash = file_hash

    def __str__(self):
        return f'{self.index}, {self.file_hash}'

    def __repr__(self):
        return self.__str__()


class Client:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port


class Socket:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.socket.connect((self.host, self.port))
        return self

    def listen(self):
        tracker_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen()
        return self

    def accept(self):
        return self.socket.accept()

    def close(self):
        self.socket.close()

    def sendall(self, payload):
        self.socket.sendall(payload)

    def recvall(self):
        rec = bytearray()
        while True:
            data = self.socket.recv(1024)
            if not data:
                break
            rec.extend(data)
        return rec

    def send_string(self, message):
        payload = message.encode('utf-8')
        self.send(payload)

    def recv_string(self):
        payload = self.recv()
        return payload.decode('utf-8')

    def send(self, payload):
        header = len(payload).to_bytes(4, 'big')
        self.socket.send(header + payload)

    def recv(self):
        header = self.socket.recv(4)
        payload_len = int.from_bytes(header, 'big')
        return self.socket.recv(payload_len)


class Tracker:
    def __init__(self, tracker_socket):
        self.host = '127.0.0.1'
        self.port = 5001
        self.client_host = None
        self.client_port = None
        self.socket = Socket(self.host, self.port).connect()

    def connect_from(self, client_host, client_port):
        self.client_host = client_host
        self.client_port = client_port
        return self

    def check_in_chunks(self, chunks):
        for chunk in chunks:
            self.check_in_chunk(chunk)
            time.sleep(1)

    def check_in_chunk(self, chunk):
        index = chunk.index
        file_hash = chunk.file_hash
        host = self.client_host
        port = self.client_port
        message = f'LOCAL_CHUNKS,{index},{file_hash},{host},{port}'
        print(f'sending_message: {message}')
        self.socket.send_string(message)

    def where_chunk(self, chunk_index):
        message = f'WHERE_CHUNK,{chunk_index}'
        self.socket.send_string(message)
        response = self.socket.recv_string()
        response_parts = response.split(',')
        if response_parts[0] == 'GET_CHUNK_FROM':
            return TrackerResponse(
                type='GET_CHUNK_FROM',
                index=response_parts[1],
                file_hash=response_parts[2],
                clients=self._get_client_list(response_parts[3:]))
        else:
            return TrackerResponse(
                type='CHUNK_LOCATION_UNKNOWN',
                index=None,
                file_hash=None,
                clients=None)

    def _get_client_list(parts):
        return [Client(parts[i], parts[i+1]) for i in range(0, len(parts), 2)]


class TrackerResponse:
    def __init__(self, type, index, file_hash, clients):
        self.type = type
        self.index = index
        self.file_hash = file_hash
        self.clients = clients


class P2PClient:
    def __init__(self, folder, transfer_port, name):
        self.folder = folder
        self.ip = '127.0.0.1'
        self.port = transfer_port
        self.local_chunks_path = os.path.join(folder, 'local_chunks.txt')
        self.lock = threading.Lock()

    def check_in_local_chunks(self):
        # connect to P2PTracker++
        self.tracker = Tracker('127.0.0.1', 5001)
        self.tracker.connect_from(self.ip, self.port)
        # check in local chunks on system
        local_chunks, capacity = self.get_local_chunks()
        self.missing_indices = self.get_missing_indices(local_chunks, capacity)
        self.capacity = capacity
        self.tracker.check_in_chunks(local_chunks)

    def generate_hash(self, file_name):
        path = os.path.join(self.folder, file_name)
        h = hashlib.sha1()
        with open(path, 'rb') as file:
            chunk = 0
            while chunk != b'':
                chunk = file.read(1024)
                h.update(chunk)
        return h.hexdigest()

    def get_local_chunks(self):
        path = os.path.join(self.folder, 'local_chunks.txt')
        local_chunks = []
        num_chunks = 0
        with open(path, "r") as file:
            for line in file:
                index_str, file_name = line.strip().split(',')
                index = int(index_str)
                if file_name == 'LASTCHUNK':
                    num_chunks = index
                    break
                file_hash = self.generate_hash(file_name)
                local_chunks.append(Chunk(index, file_hash))
                num_chunks += 1
        return local_chunks, num_chunks

    def get_missing_indices(self, found, total):
        found_indices = set(chunk.index for chunk in found)
        missing_indices = [n for n in range(1, total+1)
                           if n not in found_indices]
        missing_indices_queue = deque()
        for idx in missing_indices:
            missing_indices_queue.append(idx)
        return missing_indices_queue

    def request_missing_chunk(self, peer, index):
        peer_socket = Socket(peer.ip, peer.port).connect()
        message = f'{REQUEST_CHUNK},{index}'
        peer_socket.send_string(message)
        data = peer_socket.recvall()
        peer_socket.close()
        return data

    def get_missing_chunk(self, random_peer, index):
        file_data = self.request_missing_chunk(random_peer, index)
        file_name = f'chunk_{index}'
        self.write_to_file_system(file_name, file_data)
        self.append_to_local_chunks(index)

    def write_to_file_system(self, file_name, file_data):
        with self.lock:
            path = os.path.join(self.folder, file_name)
            with open(path, 'wb') as file:
                file.write(file_data)

    def append_to_local_chunks(self, new_index):
        chunks = []
        with open(self.local_chunks_path, "r+") as file:
            for line in file:
                index_str, file_name = line.strip().split(',')
                index = int(index_str)
                if file_name == 'LASTCHUNK':
                    break
                chunks.append(index)
            chunks.append(new_index)
            updated = '\n'.join(f'{i},chunk_{i}' for i in sorted(chunks))
            updated += f'\n{self.capacity},LASTCHUNK'
            file.write(updated)

    def request_missing_chunks(self, local_chunks, num_chunks, tracker):
        # use missing chunks queue to obtain missing chunks
        queue = self.missing_indices
        while len(queue) > 0:
            time.sleep(2)
            next_chunk_index = queue.popleft()
            print(f'searching for idx: {next_chunk_index}')
            response = tracker.where_chunk(next_chunk_index)
            if response.type != 'GET_CHUNK_FROM':
                queue.append(next_chunk_index)
            else:
                random_peer = random.choice(response.clients)
                self.get_missing_chunk(random_peer, next_chunk_index)
                tracker.check_in_chunk(Chunk(
                    response.index,
                    response.file_hash
                ))

    def handle_peer_request(self, peer_socket, peer_address):
        request = peer_socket.recv_string()
        file_index = request.strip().split(',')[0]
        file_name = f'chunk_{file_index}'
        file_data = self.read_file_data(file_name)
        peer_socket.sendall(file_data)

    def read_file_data(self, file_name):
        path = os.path.join(self.folder, file_name)
        with self.lock:
            data = bytearray()
            with open(path, "rb") as file:
                while True:
                    chunk = file.read(1024)
                    if not chunk:
                        break
                    data.extend(chunk)
            return data

    def listen_for_requests(self):
        client_socket = Socket(self.ip, self.port).listen()
        while True:
            peer_socket, peer_address = client_socket.accept()
            threading.Thread(
                target=self.handle_peer_request,
                args=(peer_socket, peer_address)
            ).start()


def start_client(folder, transfer_port, name):
    client = P2PClient(folder, transfer_port, name)
    client.check_in_local_chunks()
    # Find clients with missing chunks and request
    threading.Thread(
        target=client.request_missing_chunks,
        args=()
    ).start()
    # listen and serve incoming chunk requests
    threading.Thread(
        target=client.listen_for_requests,
        args=()
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-folder", type=str)
    parser.add_argument("-transfer_port", type=int)
    parser.add_argument("-name", type=str)
    args = parser.parse_args()
    start_client(
        args.folder,
        args.transfer_port,
        args.name
    )
