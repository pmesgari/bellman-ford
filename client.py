import socket
import sys

PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)


seconds = sys.argv[-1]
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect(ADDR)
    msg = str(seconds).encode('utf-8')
    s.sendall(msg)
    data = s.recv(1024)
print('Received', repr(data))
