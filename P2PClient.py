import socket
import argparse
import os
import time
import hashlib

from collections import deque
# import threading
# import sys
# import logging


# TODO: Implement P2PClient that connects to P2PTracker

class Chunk:
    def __init__(self, index, file_hash):
        self.index = index
        self.file_hash = file_hash

    def __str__(self):
        return f'{self.index}, {self.file_hash}'

    def __repr__(self):
        return self.__str__()


class TrackerSocket:
    def __init__(self, client_host, client_port):
        self.host = '127.0.0.1'
        self.port = 5001
        self.client_host = client_host
        self.client_port = client_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.bufsize = 1024

    def check_in_chunks(self, chunks):
        for chunk in chunks:
            self.check_in_chunk(chunk)

    def check_in_chunk(self, chunk):
        index = chunk.index
        file_hash = chunk.file_hash
        host = self.client_host
        port = self.client_port
        message = f'LOCAL_CHUNKS,{index},{file_hash},{host},{port}'
        print(f'sending_message: {message}')
        self.send(message)

    def where_chunk(self, chunk_index):
        message = f'WHERE_CHUNK,{chunk_index}'
        self.send(message)
        response = self.recv()
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

    def send(self, message):
        payload = message.encode('utf-8')
        header = len(payload).to_bytes(4, 'big')
        self.socket.send(header + payload)

    def recv(self):
        header = self.socket.recv(4)
        payload_len = int.from_bytes(header, 'big')
        return self.socket.recv(payload_len).decode('utf-8')


class TrackerResponse:
    def __init__(self, type, index, file_hash, clients):
        self.type = type
        self.index = index
        self.file_hash = file_hash
        self.clients = clients


def generate_hash(folder, file_name):
    path = os.path.join(folder, file_name)
    h = hashlib.sha1()
    with open(path, 'rb') as file:
        chunk = 0
        while chunk != b'':
            chunk = file.read(1024)
            h.update(chunk)
    return h.hexdigest()


def get_local_chunks(folder):
    path = os.path.join(folder, 'local_chunks.txt')
    local_chunks = []
    num_chunks = 0
    with open(path, "r") as file:
        for line in file:
            index_str, file_name = line.strip().split(',')
            index = int(index_str)
            if file_name == 'LASTCHUNK':
                num_chunks = index
                break
            file_hash = generate_hash(folder, file_name)
            local_chunks.append(Chunk(index, file_hash))
            num_chunks += 1
    return local_chunks, num_chunks


def get_missing_chunks(found, total):
    found_indices = set(chunk.index for chunk in found)
    missing_indices = [n for n in range(1, total+1) if n not in found_indices]
    print(total)
    missing_chunks = deque()
    for idx in missing_indices:
        missing_chunks.append(idx)
    return missing_chunks


def request_missing_chunks(local_chunks, num_chunks):
    # use missing chunks queue to obtain missing chunks
    missing_chunks = get_missing_chunks(local_chunks, num_chunks)
    while len(missing_chunks) > 0:
        next_chunk_index = missing_chunks.popleft()
        print(f'searching for idx {next_chunk_index}')
        response = tracker.where_chunk(next_chunk_index)
        if response.type == 'GET_CHUNK_FROM':
            print('chunk found!')
            print(response)
        elif response.type == 'CHUNK_LOCATION_UNKNOWN':
            missing_chunks.append(next_chunk_index)
        time.sleep(2)


def start_client(folder, transfer_port, name):
    # check in local chunks on system
    local_chunks, num_chunks = get_local_chunks(folder)
    tracker = TrackerSocket('127.0.0.1', 5001)
    tracker.check_in_chunks(local_chunks)



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