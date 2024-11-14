import logging
import json
import time
import threading
from typing import Dict
from api_client import APIClient
from websocket_client import WebSocketClient
from market_hours import is_london_market_open
from order_block_bot import OrderBlockBot
from mt5_platform import MT5Platform
from mt4_platform import MT4Platform


logger = logging.getLogger(__name__)

class TradingManager:
    def __init__(self, api_client: APIClient, ws_client: WebSocketClient):
        self.api_client = api_client
        self.ws_client = ws_client
        self.platforms: Dict[str, TradingPlatform] = {}
        self.bots: Dict[str, OrderBlockBot] = {}
    
    def initialize(self):
        accounts = self.api_client.get_accounts()
        for account in accounts["items"]:
            if(account["type"] == "MT5"):
                platform_class =  MT5Platform
                platform = platform_class(account['server'], account['login'], account['password'])
                platform.connect()
                self.platforms[account['id']] = platform
            # else:
            #     platform_class =  MT4Platform
            #     platform = platform_class(account['server'], account['login'], account['password'])
            #     platform.connect()
            #     self.platforms[account['id']] = platform
                
        bots = self.api_client.get_bots()
        for bot_config in bots["items"]:
            if bot_config['account'] in self.platforms:
                print("info account")
                platform = self.platforms[bot_config['account']]
                print("info platform")
                bot = OrderBlockBot(platform, bot_config)
                self.bots[bot_config['id']] = bot
        self.ws_client.set_on_message_callback(self.handle_websocket_message)
        #self.ws_client.connect()

        
    def reset_accounts_and_bots(self):
        accounts = self.api_client.get_accounts()
        for account in accounts["items"]:
            platform_id = account['id']
            if platform_id in self.platforms:
                platform = self.platforms[platform_id]
                # Verificar si los datos de la plataforma han cambiado
                if platform.server != account['server'] or platform.login != account['login']:
                    platform.disconnect()  # Desconecta solo si es necesario
                    platform.connect(account['server'], account['login'], account['password'])
                    logger.info(f"Reconectada la cuenta {platform_id} por cambio en configuración.")
            else:
                # Crea y conecta la plataforma si no existe en `self.platforms`
                platform = MT5Platform(account['server'], account['login'], account['password'])
                platform.connect()
                self.platforms[platform_id] = platform

        # Reiniciar los bots para asegurar que están actualizados
        self.bots.clear()
        bots = self.api_client.get_bots()
        for bot_config in bots["items"]:
            if bot_config['account'] in self.platforms:
                platform = self.platforms[bot_config['account']]
                bot = OrderBlockBot(platform, bot_config)
                self.bots[bot_config['id']] = bot
        logger.info("Cuentas y bots actualizados.")

    def start_monitoring(self, check_interval=10):
        """
        Inicia un hilo separado para monitorear el cierre de operaciones por stop loss o take profit.
        """
        for platform_id, platform in self.platforms.items():
            thread = threading.Thread(target=self.monitor_operations, args=(platform, check_interval))
            thread.daemon = True
            thread.start()
            logger.info(f"Monitoreo iniciado para la plataforma {platform_id}")

    def monitor_operations(self, platform: MT5Platform, check_interval: int):
        """
        Monitorea las operaciones abiertas de una plataforma y guarda en la base de datos cuando una operación se cierra.
        """
        while True:
            platform.monitor_operations(check_interval)
            time.sleep(check_interval)
    
    def update_bot_config(self, bot_id: str, new_config: Dict):
        if bot_id in self.bots:
            self.bots[bot_id].config.update(new_config)
            logger.info(f"Configuración actualizada para el bot {bot_id}")

    def handle_websocket_message(self, message):
        data = message
        if data['type'] == 'CONFIG_UPDATE':
            self.update_bot_config(data['botId'], data['config'])
        elif data['type'] == 'BOT_STATUS_UPDATE':
            self.update_bot_status(data['botId'], data['status'], data['tp'], data['lot'] )
        elif data['type'] == 'BOT_DELETED':
            self.reset_accounts_and_bots()
        elif data['type'] == 'BOT_CREATED':
            self.reset_accounts_and_bots()
        elif data['type'] == 'ACCOUNT':
            self.reset_accounts_and_bots()

    def update_bot_status(self, bot_id: str, active: str, tp: int, lot: float):
        if bot_id in self.bots:
            self.bots[bot_id].config['botStatus'] = active
            self.bots[bot_id].config['takeProfit'] = tp
            self.bots[bot_id].config['lotSize'] = lot

    def run(self):
        # Iniciar WebSocket en un hilo separado
        ws_thread = threading.Thread(target=self.ws_client.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

        print(f"WebSocket Thread Alive: {ws_thread.is_alive()}")
        if not ws_thread.is_alive():
            print("WebSocket thread stopped unexpectedly!")
            # Opcional: intentar reiniciar el hilo si es necesario
            ws_thread = threading.Thread(target=self.ws_client.run_forever)
            ws_thread.daemon = True
            ws_thread.start()

        self.start_monitoring(check_interval=10)

        while True:
            if is_london_market_open():
                print("Market Open")
                for bot_id, bot in self.bots.items():
                    print("Bot Status", bot.config['botStatus'])
                    if bot.config['botStatus'] == "active":
                        print("Run Botsito", bot.config['id'])
                        bot.run()
            else:
                logger.info("Mercado de Londres cerrado. Esperando para la próxima sesión.")
            
            time.sleep(900) 