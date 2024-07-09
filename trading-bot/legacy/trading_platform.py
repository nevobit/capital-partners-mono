from abc import ABC, abstractmethod

class TradingPlatform(ABC):
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def get_market_data(self, symbol: str, timeframe: int, num_candles: int):
        pass

    @abstractmethod
    def place_order(self, symbol: str, order_type: str, volume: float, price: float, sl: float, tp: float):
        pass