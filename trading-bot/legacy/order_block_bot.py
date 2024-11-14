import logging
from datetime import datetime, timedelta
import pytz
import pandas as pd
import numpy as np
from trading_platform import TradingPlatform
from mt5_platform import MT5Platform
import MetaTrader5 as mt5
logger = logging.getLogger(__name__)
LONDON_TZ = pytz.timezone('Europe/London')

class OrderBlockBot:
    def __init__(self, platform: TradingPlatform, config: dict):
        self.platform = platform
        self.config = config
        self.symbol = config['symbol']
        self.timeframe = 16385
        self.lot_size = float(config['lotSize'])
        self.last_check_time = datetime.now(LONDON_TZ) - timedelta(minutes=10)

    def custom_atr(self, high, low, close, period):
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    def custom_sma(self, series, period):
        sma = series.rolling(window=period).mean()
        return sma

    def identify_order_blocks(self, data: pd.DataFrame) -> pd.DataFrame:
        data['atr'] = self.custom_atr(data['high'], data['low'], data['close'], period=14)
        data['avg_volume'] = data['tick_volume'].rolling(window=20).mean()
        
        data['is_order_block'] = (
            (data['high'] - data['low'] > data['atr'] * 1.5) &
            (data['tick_volume'] > data['avg_volume'] * 2) &
            ((data['close'] - data['open']).abs() / (data['high'] - data['low']) > 0.5)
        )
        
        data['ob_bullish'] = data['is_order_block'] & (data['close'] > data['open'])
        data['ob_bearish'] = data['is_order_block'] & (data['close'] <= data['open'])
        

        print("Is orderbloc", data['is_order_block'])
        return data

    def find_entry_point(self, data: pd.DataFrame, direction: str, ob_index: int) -> float:
        tick = mt5.symbol_info_tick(self.symbol)
        price_dict = {"buy": tick.ask, "sell": tick.bid}
        print("Ask", tick.ask)
        print("Bid", tick.bid)

        return price_dict[direction]

    def calculate_risk_reward(self, entry: float, sl: float, tp: float) -> float:
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        return reward / risk if risk != 0 else 0

    def run(self):
        try:
            data = self.platform.get_market_data(self.symbol, self.timeframe, 200)
            data = self.identify_order_blocks(data)

            sma = self.custom_sma(data['close'], period=50)
            market_direction = 'buy' if data['close'].iloc[-1] > sma.iloc[-1] else 'sell'

            valid_obs = data[data['ob_bullish'] if market_direction == 'buy' else data['ob_bearish']].index

            if not valid_obs.empty:
                entry_point = self.find_entry_point(data, market_direction, valid_obs[0])
                if entry_point is None:
                    logger.info("No se encontró un punto de entrada válido")
                    return

                atr = data['atr'].iloc[-1]
                print("atr", atr)
                if market_direction == 'buy':
                    stop_loss = entry_point - atr * 2
                    take_profit = entry_point + (entry_point - stop_loss) *2
                    order_type = mt5.ORDER_TYPE_BUY_STOP
                else:  # sell
                    stop_loss = entry_point + atr * 2
                    take_profit = entry_point - (stop_loss - entry_point) * 2
                    order_type = mt5.ORDER_TYPE_SELL_STOP

                rr_ratio = self.calculate_risk_reward(entry_point, stop_loss, take_profit)

                if rr_ratio >= 2:
                    self.platform.place_order(self.symbol, order_type, float(self.lotSize), entry_point, stop_loss, take_profit)
                    logger.info(f"Orden colocada: {self.symbol}, Tipo: {market_direction}, Entrada: {entry_point:.5f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}, R:R: {rr_ratio:.2f}")
                else:
                    logger.info(f"Ratio R:R no aceptable: {rr_ratio:.2f}")
            else:
                logger.info("No se encontraron Order Blocks válidos")
        except Exception as e:
            logger.error(f"Error en la ejecución del bot: {e}")
