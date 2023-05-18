import socket
import threading
import sys
import time
import concurrent.futures

PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'

def start_without_thread():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(ADDR)
        print('1')
        s.listen()
        print('2')
        while True:
            try:
                conn, addr = s.accept()
                print('3')
                with conn:
                    print(f'[SERVER] Connected by {addr}')
                    while True:
                        data = conn.recv(1024)
                        if not data:
                            break
                        conn.sendall(data)
            except KeyboardInterrupt or Exception:
                print('\n[SERVER] Shutting down.')
                break

def handle_client(conn, addr):
    seconds = conn.recv(1024).decode(FORMAT)
    start = time.perf_counter()
    print(f'[SERVER] {addr} will sleep for {seconds} second(s).')
    time.sleep(int(seconds))
    end = time.perf_counter()
    print(f'[SERVER] {addr} woke up after {round(end - start, 2)} second(s).')
    conn.send('OK'.encode(FORMAT))
    conn.close()
    return 'Done'

def start_with_thread():
    conn = None
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(ADDR)
        print('1')
        s.listen()
        print('2')
        connections = {}
        while True:
            try:
                conn, addr = s.accept()
                connections[addr] = conn
                print(f'[SERVER] Connected by {addr}')
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                thread.daemon = True
                thread.start()
                print(f"[SERVER] Active connections: {threading.activeCount() - 1}")
            except KeyboardInterrupt or Exception:
                if connections:
                    for c in connections:
                        try:
                            c.send('SHUTTING DOWN'.encode('utf-8'))
                        except:
                            print('[SERVER] connection not alive.')
                print('\n[SERVER] Shutting down.')
                break
    sys.exit(0)


def start_with_thread_executer():
    conn = None
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(ADDR)
        print('1')
        s.listen()
        print('2')
        connections = {}
        while True:
            try:
                conn, addr = s.accept()
                connections[addr] = conn
                print(f'[SERVER] Connected by {addr}')
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    future = executor.submit(handle_client, conn, addr)
                    return_value = future.result()
                    print(return_value)
                print(f"[SERVER] Active connections: {threading.activeCount() - 1}")
            except KeyboardInterrupt or Exception:
                if connections:
                    for c in connections:
                        try:
                            c.send('SHUTTING DOWN'.encode('utf-8'))
                        except:
                            print('[SERVER] connection not alive.')
                print('\n[SERVER] Shutting down.')
                break
    sys.exit(0)

if __name__ == '__main__':
    # start_without_thread()
    # start_with_thread()
    start_with_thread_executer()