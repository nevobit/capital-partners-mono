import logging
from datetime import datetime, timedelta
import pytz
import pandas as pd
import numpy as np
import talib
from trading_platform import TradingPlatform
from mt4_platform import MT4Platform
from mt5_platform import MT5Platform

logger = logging.getLogger(__name__)
LONDON_TZ = pytz.timezone('Europe/London')

class OrderBlockBot:
    def __init__(self, platform: TradingPlatform, config: dict):
        self.platform = platform
        self.config = config
        self.symbol = config['symbol']
        self.timeframe = config['timeframe']
        self.lot_size = config['lot_size']
        self.last_check_time = datetime.now(LONDON_TZ) - timedelta(minutes=10)

    def identify_order_blocks(self, data: pd.DataFrame) -> pd.DataFrame:
        data['atr'] = talib.ATR(data['high'], data['low'], data['close'], timeperiod=self.config['atr_period'])
        data['avg_volume'] = data['tick_volume'].rolling(window=20).mean()
        
        data['is_order_block'] = (
            (data['high'] - data['low'] > data['atr'] * self.config['atr_multiplier']) &
            (data['tick_volume'] > data['avg_volume'] * self.config['volume_multiplier']) &
            ((data['close'] - data['open']).abs() / (data['high'] - data['low']) > 0.5)
        )
        
        data['ob_bullish'] = data['is_order_block'] & (data['close'] > data['open'])
        data['ob_bearish'] = data['is_order_block'] & (data['close'] <= data['open'])
        
        return data

    def find_entry_point(self, data: pd.DataFrame, direction: str, ob_index: int) -> float:
        fib_levels = np.array([0, 0.236, 0.382, 0.5, 0.618, 0.786, 1])
        if direction == 'buy':
            fib_prices = data['low'].iloc[ob_index] + fib_levels * (data['high'].iloc[ob_index] - data['low'].iloc[ob_index])
            entry = min((level for level in fib_prices if level > data['close'].iloc[-1]), default=None)
        else:  # sell
            fib_prices = data['high'].iloc[ob_index] - fib_levels * (data['high'].iloc[ob_index] - data['low'].iloc[ob_index])
            entry = max((level for level in fib_prices if level < data['close'].iloc[-1]), default=None)
        return entry

    def calculate_risk_reward(self, entry: float, sl: float, tp: float) -> float:
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        return reward / risk if risk != 0 else 0

    def run(self):
        try:
            data = self.platform.get_market_data(self.symbol, self.timeframe, 200)
            data = self.identify_order_blocks(data)

            sma = talib.SMA(data['close'], timeperiod=self.config['sma_period'])
            market_direction = 'buy' if data['close'].iloc[-1] > sma.iloc[-1] else 'sell'

            valid_obs = data[data['ob_bullish'] if market_direction == 'buy' else data['ob_bearish']].index

            if not valid_obs.empty:
                entry_point = self.find_entry_point(data, market_direction, valid_obs[0])
                if entry_point is None:
                    logger.info("No se encontró un punto de entrada válido")
                    return

                atr = data['atr'].iloc[-1]

                if market_direction == 'buy':
                    stop_loss = entry_point - atr * 2
                    take_profit = entry_point + (entry_point - stop_loss) * self.config['risk_reward_ratio']
                    order_type = MT4Platform.ORDER_TYPE_BUY_STOP if isinstance(self.platform, MT4Platform) else MT5Platform.ORDER_TYPE_BUY_STOP
                else:  # sell
                    stop_loss = entry_point + atr * 2
                    take_profit = entry_point - (stop_loss - entry_point) * self.config['risk_reward_ratio']
                    order_type = MT4Platform.ORDER_TYPE_SELL_STOP if isinstance(self.platform, MT4Platform) else MT5Platform.ORDER_TYPE_SELL_STOP

                rr_ratio = self.calculate_risk_reward(entry_point, stop_loss, take_profit)
                if rr_ratio >= self.config['risk_reward_ratio']:
                    self.platform.place_order(self.symbol, order_type, self.lot_size, entry_point, stop_loss, take_profit)
                    logger.info(f"Orden colocada: {self.symbol}, Tipo: {market_direction}, Entrada: {entry_point:.5f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}, R:R: {rr_ratio:.2f}")
                else:
                    logger.info(f"Ratio R:R no aceptable: {rr_ratio:.2f}")
            else:
                logger.info("No se encontraron Order Blocks válidos")
        except Exception as e:
            logger.error(f"Error en la ejecución del bot: {e}")