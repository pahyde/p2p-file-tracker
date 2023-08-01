import socket
import time

hashes = ['asdf83hfsfh3hrhdfllhf3hf', 'erutfh736d73yu3', '237r7329hsdfgsd3']

commands = [
    'LOCAL_CHUNKS',
    'WHERE_CHUNKS',
    'REQUEST_CHUNKS',
    'GET_CHUNK_FROM',
    'CHUNK_LOCATION_UNKNOWN'
]

idxs = '0 3 173 12'.split()

ips = ['localhost', '122.0.31.10']

ports = [5000, 3000, 80, 5100]

local_chunk_tests = []
for idx in idxs:
    for hash in hashes:
        for ip in ips:
            for port in ports:
                test_case = ','.join(map(str,[commands[0],idx,hash,ip,port]))
                local_chunk_tests.append(test_case)

where_chunk_tests = []
for idx in idxs:
    where_chunk_tests.append(f'{commands[1]},{idx}')

request_chunk_tests = []
for idx in idxs:
    request_chunk_tests.append(f'{commands[2]},{idx}')

get_chunk_from_tests = []
for idx in idxs:
    for hash in hashes:
        for port1 in ports[:2]:
            for port2 in ports[2:]:
                test_case = f'{commands[3]},{idx},{hash},{ips[0]},{port1},{ips[1]},{port2}'
                get_chunk_from_tests.append(test_case)

chunk_location_unknown_tests = []
for idx in idxs:
    chunk_location_unknown_tests.append(f'{commands[4]},{idx}')


# client. Connect to message parser server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect('localhost', 5000)
print('local chunk test')
for test in local_chunk_tests:
    sock.send(test.encode('utf-8'))
    time.sleep(1)

