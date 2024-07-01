import logging
import json
import time
import threading
from typing import Dict
from api_client import APIClient
from websocket_client import WebSocketClient
from mt4_platform import MT4Platform
from mt5_platform import MT5Platform
from order_block_bot import OrderBlockBot
from market_hours import is_london_market_open

logger = logging.getLogger(__name__)

class TradingManager:
    def __init__(self, api_client: APIClient, ws_client: WebSocketClient):
        self.api_client = api_client
        self.ws_client = ws_client
        self.platforms: Dict[str, TradingPlatform] = {}
        self.bots: Dict[str, OrderBlockBot] = {}

    def initialize(self):
        accounts = self.api_client.get_accounts()
        for account in accounts:
            platform_class = MT4Platform if account['type'] == 'MT4' else MT5Platform
            platform = platform_class(account['server'], account['login'], account['password'])
            platform.connect()
            self.platforms[account['id']] = platform

        bots = self.api_client.get_bots()
        for bot_config in bots:
            if bot_config['account_id'] in self.platforms:
                platform = self.platforms[bot_config['account_id']]
                bot = OrderBlockBot(platform, bot_config)
                self.bots[bot_config['id']] = bot

        self.ws_client.set_on_message_callback(self.handle_websocket_message)
        self.ws_client.connect()

    def update_bot_config(self, bot_id: str, new_config: Dict):
        if bot_id in self.bots:
            self.bots[bot_id].config.update(new_config)
            logger.info(f"Configuración actualizada para el bot {bot_id}")

    def handle_websocket_message(self, message):
        data = json.loads(message)
        if data['type'] == 'CONFIG_UPDATE':
            self.update_bot_config(data['botId'], data['config'])
        elif data['type'] == 'BOT_STATUS_UPDATE':
            self.update_bot_status(data['botId'], data['active'])

    def update_bot_status(self, bot_id: str, active: bool):
        if bot_id in self.bots:
            self.bots[bot_id].config['active'] = active
            self.api_client.update_bot_status(bot_id, active)
            logger.info(f"Estado del bot {bot_id} actualizado a {'activo' if active else 'inactivo'}")

    def run(self):
        # Iniciar WebSocket en un hilo separado
        ws_thread = threading.Thread(target=self.ws_client.run_forever)
        ws_thread.start()

        while True:
            if is_london_market_open():
                for bot_id, bot in self.bots.items():
                    if bot.config['active']:
                        bot.run()
            else:
                logger.info("Mercado de Londres cerrado. Esperando para la próxima sesión.")
            
            time.sleep(15)  # Verificar cada 15 segundos