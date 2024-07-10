import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

class OrderBlockBot:
    def __init__(self, symbol: str, timeframes: List[int], config: Dict):
        self.symbol = symbol
        self.timeframes = timeframes
        self.config = config

    def get_candles(self, timeframe: int, count: int) -> pd.DataFrame:
        """Obtiene las velas del mercado y las convierte en un DataFrame."""
        candles = mt5.copy_rates_from_pos(self.symbol, timeframe, 0, count)
        if candles is None or len(candles) < count:
            return pd.DataFrame()
        return pd.DataFrame(candles)

    def is_order_block(self, candles: pd.DataFrame) -> Tuple[bool, bool]:
        """Determina si las últimas dos velas forman un order block."""
        if len(candles) < 2:
            return False, False

        first_candle, second_candle = candles.iloc[-2:].reset_index(drop=True)
        
        buy_order_block = (first_candle['close'] > first_candle['open'] and 
                           second_candle['close'] < second_candle['open'])
        
        sell_order_block = (first_candle['close'] < first_candle['open'] and 
                            second_candle['close'] > second_candle['open'])
        
        return buy_order_block, sell_order_block

    def check_order_blocks(self) -> Dict[int, Dict[str, bool]]:
        """Verifica order blocks en múltiples timeframes."""
        order_block_signals = {tf: {'buy': False, 'sell': False} for tf in self.timeframes}
        
        for tf in self.timeframes:
            candles = self.get_candles(tf, 2)
            if not candles.empty:
                buy_ob, sell_ob = self.is_order_block(candles)
                order_block_signals[tf]['buy'] = buy_ob
                order_block_signals[tf]['sell'] = sell_ob
            else:
                print(f"No se pudieron obtener velas para el timeframe {tf}")
        
        return order_block_signals

    def analyze_order_blocks(self) -> Tuple[str, float]:
        """Analiza los order blocks y determina la dirección y fuerza de la señal."""
        signals = self.check_order_blocks()
        buy_signals = sum(tf_signal['buy'] for tf_signal in signals.values())
        sell_signals = sum(tf_signal['sell'] for tf_signal in signals.values())
        
        total_timeframes = len(self.timeframes)
        buy_strength = buy_signals / total_timeframes
        sell_strength = sell_signals / total_timeframes
        
        if buy_strength > sell_strength:
            return 'buy', buy_strength
        elif sell_strength > buy_strength:
            return 'sell', sell_strength
        else:
            return 'neutral', 0.0

    def run(self):
        direction, strength = self.analyze_order_blocks()
        if direction != 'neutral' and strength >= self.config['min_signal_strength']:
            print(f"Señal de {direction} detectada con fuerza {strength:.2f}")
            # Aquí puedes agregar la lógica para colocar órdenes
        else:
            print(f"No se detectó una señal fuerte. Dirección: {direction}, Fuerza: {strength:.2f}")

