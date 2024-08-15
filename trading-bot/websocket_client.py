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
                                    ping_payload='{"type":"ping"}')
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
        if self.on_message_callback:
            self.on_message_callback(message)

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
