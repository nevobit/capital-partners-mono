import logging
from pymt4 import MT4
import pandas as pd
from trading_platform import TradingPlatform

logger = logging.getLogger(__name__)

class MT4Platform(TradingPlatform):
    def __init__(self, server: str, login: int, password: str):
        self.mt4 = MT4()
        self.server = server
        self.login = login
        self.password = password

    def connect(self):
        try:
            self.mt4.connect(self.server, login=self.login, password=self.password)
            logger.info(f"Conectado a MT4: {self.server}")
        except Exception as e:
            logger.error(f"Error al conectar a MT4: {e}")
            raise

    def get_market_data(self, symbol: str, timeframe: int, num_candles: int):
        try:
            rates = self.mt4.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
            return pd.DataFrame(rates)
        except Exception as e:
            logger.error(f"Error al obtener datos de MT4: {e}")
            raise

    def place_order(self, symbol: str, order_type: str, volume: float, price: float, sl: float, tp: float):
        try:
            result = self.mt4.order_send(symbol=symbol, cmd=order_type, volume=volume,
                                         price=price, slippage=3, sl=sl, tp=tp)
            logger.info(f"Orden colocada en MT4: {result}")
            return result
        except Exception as e:
            logger.error(f"Error al colocar orden en MT4: {e}")
            raise