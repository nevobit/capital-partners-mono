import logging
from config import load_config
from api_client import APIClient
from websocket_client import WebSocketClient
from trading_manager import TradingManager
import socket

def start_socket_server():
    host = '127.0.0.1'
    port = 5555
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(15)

    client_socket,client_address = server_socket.accept()
    print(f"Conexion establecida con {client_address}")

    while True:
        data = client_socket.recv(1024)
        if not data:
            break
        print(f"Recibido: {data.decode()}")


def main():
    config = load_config()
    api_client = APIClient(config['api_base_url'])
    ws_client = WebSocketClient(config['websocket_url'])
    manager = TradingManager(api_client, ws_client)

    import threading
    socket_thread = threading.Thread(target=start_socket_server)
    socket_thread.deamon = True
    socket_thread.start()

    manager.initialize()
    manager.run()

if __name__ == "__main__":
    main()