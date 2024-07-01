import websocket
import logging

logger = logging.getLogger(__name__)

class WebSocketClient:
    def __init__(self, url: str):
        self.url = url
        self.ws = None
        self.on_message_callback = None

    def set_on_message_callback(self, callback):
        self.on_message_callback = callback

    def connect(self):
        self.ws = websocket.WebSocketApp(self.url,
                                         on_message=self._on_message,
                                         on_error=self._on_error,
                                         on_close=self._on_close,
                                         on_open=self._on_open)

    def run_forever(self):
        self.ws.run_forever()

    def _on_message(self, ws, message):
        if self.on_message_callback:
            self.on_message_callback(message)

    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws):
        logger.info("WebSocket connection closed")

    def _on_open(self, ws):
        logger.info("WebSocket connection opened")