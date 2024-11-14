import websocket
import logging
import time
import threading
import json
import ssl

#logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebSocketClient:
    def __init__(self, url: str):
        self.url = url
        self.ws = None
        self.on_message_callback = None
        self.reconnect_interval = 5
        self.is_connected = False
        self.should_run = True
        self.heartbeat_interval = 30
        self.api_secret = "b17b7d9f8a9c1f4e5d8e3a9b2c7f6e3d1a2b9c7e5d8f1b2c3a4e7f6b9d2e3c1f7a5b6d"


    def set_on_message_callback(self, callback):
        self.on_message_callback = callback

    def connect(self):
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(self.url,
                                         on_message=self._on_message,
                                         on_error=self._on_error,
                                         on_close=self._on_close,
                                         on_open=self._on_open)

    def run_forever(self):
        while self.should_run:
            try:
                self.connect()
                self.ws.run_forever(ping_interval=self.heartbeat_interval,
                                    ping_timeout=10,
                                    ping_payload='{"type":"ping"}',
                                    sslopt={"cert_reqs": ssl.CERT_NONE})
            except Exception as e:
                logger.error(f"WebSocket run error: {e}")
            
            if self.should_run:
                time.sleep(self.reconnect_interval)

    def start(self):
        thread = threading.Thread(target=self.run_forever)
        thread.daemon = True
        thread.start()

    def stop(self):
        self.should_run = False
        if self.ws:
            self.ws.close()

    def _on_message(self, ws, message):
        print('Received message type:', type(message))  # Esto mostrará el tipo de mensaje
        try:
            # Intenta analizar el mensaje como JSON
            data = json.loads(message)
            print("Parsed JSON data:", data)  # Imprime los datos JSON

            # Si `data` es un diccionario, procede con los índices de string
            if isinstance(data, dict):
                if self.on_message_callback:
                    self.on_message_callback(data)
            else:
                logger.error("Received JSON data is not a dictionary. Received type: {}".format(type(data)))

        except json.JSONDecodeError:
            # Si el mensaje no es JSON, lo registra como texto
            logger.info(f"Received non-JSON message: {message}")
            if self.on_message_callback:
                self.on_message_callback(message)
        except TypeError as e:
            logger.error(f"Type error while processing message: {e}")
        except KeyError as e:
            logger.error(f"Key error: {e} in message {message}")

    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        self.is_connected = False

    def _on_open(self, ws):
        self.is_connected = True

    def send_message(self, message):
        if self.is_connected:
            try:
                self.ws.send(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
        else:
            logger.warning("Cannot send message. WebSocket is not connected.")
