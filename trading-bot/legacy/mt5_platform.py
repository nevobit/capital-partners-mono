import logging
import MetaTrader5 as mt5
import pandas as pd
from trading_platform import TradingPlatform

logger = logging.getLogger(__name__)

class MT5Platform(TradingPlatform):
    def __init__(self, server: str, login: int, password: str):
        self.server = server
        self.login = login
        self.password = password

    def connect(self):
        print(self.server)
        print(self.login)
        print(self.password)

        try:
            mt5.login(login=self.login, server=self.server, password=self.password)
            if not mt5.initialize(login=self.login, server=self.server, password=self.password):
                raise Exception(mt5.last_error())
            logger.info(f"Conectado a MT5: {self.server}")
        except Exception as e:
            logger.error(f"Error al conectar a MT5: {e}")
            raise

    def get_market_data(self, symbol: str, timeframe: int, num_candles: int):
        try:
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
            return pd.DataFrame(rates)
        except Exception as e:
            logger.error(f"Error al obtener datos de MT5: {e}")
            raise

    def place_order(self, symbol: str, order_type: str, volume: float, price: float, sl: float, tp: float):
        print("Place Order", price)
        try:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": 2.0,
                "type": order_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 20,
                "magic": 100,
                "comment": "Order Block Trade",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": 0,
            }
            print(request)
            result = mt5.order_send(request)
            logger.info(f"Orden colocada en MT5: {result}")
            return result
        except Exception as e:
            logger.error(f"Error al colocar orden en MT5: {e}")
            raise