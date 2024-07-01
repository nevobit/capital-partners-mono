import logging
from config import load_config
from api_client import APIClient
from websocket_client import WebSocketClient
from trading_manager import TradingManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    config = load_config()
    api_client = APIClient(config['api_base_url'])
    ws_client = WebSocketClient(config['websocket_url'])
    manager = TradingManager(api_client, ws_client)
    manager.initialize()
    manager.run()

if __name__ == "__main__":
    main()