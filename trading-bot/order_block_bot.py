import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from typing import Dict
from trading_platform import TradingPlatform
from datetime import datetime, date
import time
import logging
from config import load_config
from api_client import APIClient

logger = logging.getLogger(__name__)

class OrderBlockBot:
    def __init__(self, platform: TradingPlatform, config: Dict):
        self.platform = platform
        self.symbol = config["symbol"]
        self.timeframes =  [15, 16385, 16388] 
        self.config = config
        self.orders_today = 0
        self.last_order_date = None
        self.max_orders_per_day = 10
        self.max_open_positions = 10  # Nuevo límite de posiciones abiertas
        self.magic = 100
        self.deviation = 20
        self.trailing_stop_percent = 0.003 
        self.position_info = {} 
        self.daily_loss = 0
        self.max_daily_loss = self.calculate_max_daily_loss()
        self.num_replicas = 1
        self.config_api = load_config()
        self.api_client = APIClient(self.config_api['api_base_url'])
        self.future_candle_count = 6

    def get_open_positions_count(self):
        positions = mt5.positions_get(symbol=self.symbol)
        return len(positions) if positions is not None else 0

    def reset_daily_counter(self):
        today = date.today()
        if self.last_order_date != today:
            self.orders_today = 0
            self.last_order_date = today
    
    def get_all_positions(self):
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None or len(positions) == 0:
            logger.info(f"No open positions for {self.symbol}")
            return []
        return list(positions)

    def initialize_position_info(self):
        positions = self.get_all_positions()
        for position in positions:
            if position.ticket not in self.position_info:
                self.position_info[position.ticket] = {
                    'max_profit': position.profit,
                    'trailing_stop': position.sl
                }
        logger.info(f"Initialized {len(self.position_info)} positions")

    def update_trailing_stop(self, position):
        current_price = mt5.symbol_info_tick(self.symbol).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(self.symbol).ask

        #print(f"Posición {position.ticket}: Tipo: {'Compra' if position.type == mt5.ORDER_TYPE_BUY else 'Venta'}")
        #print(f"Precio actual: {current_price}, Precio de apertura: {position.price_open}")
        #print(f"Stop Loss actual: {position.sl}, Take Profit: {position.tp}")
    
       

        if position.ticket not in self.position_info:
            self.position_info[position.ticket] = {
                'max_profit': position.profit,
                'trailing_stop': position.sl
            }

        info = self.position_info[position.ticket]

        point = mt5.symbol_info(self.symbol).point
        trailing_stop_distance = current_price * self.trailing_stop_percent / point

        if position.profit > info['max_profit']:
            info['max_profit'] = position.profit
            
            if position.type == mt5.ORDER_TYPE_BUY:
                new_sl = current_price - trailing_stop_distance * point
                if new_sl > position.sl:
                    request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": position.ticket,
                        "sl": new_sl,
                        "tp": position.tp
                    }
                    result = mt5.order_send(request)
                    if result.retcode != mt5.TRADE_RETCODE_DONE:
                        print(f"Failed to update trailing stop for position {position.ticket}, error code: {result.retcode}")
                    else:
                        print(f"Updated trailing stop for position {position.ticket} to {new_sl}")
                        info['trailing_stop'] = new_sl
            
            elif position.type == mt5.ORDER_TYPE_SELL:
                new_sl = current_price + trailing_stop_distance * point
                if new_sl < position.sl or position.sl == 0:
                    request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": position.ticket,
                        "sl": new_sl,
                        "tp": position.tp
                    }
                    result = mt5.order_send(request)
                    if result.retcode != mt5.TRADE_RETCODE_DONE:
                        print(f"Failed to update trailing stop for position {position.ticket}, error code: {result.retcode}")
                    else:
                        print(f"Updated trailing stop for position {position.ticket} to {new_sl}")
                        info['trailing_stop'] = new_sl

        # Verificar si se ha alcanzado el trailing stop
        if (position.type == mt5.ORDER_TYPE_BUY and current_price <= info['trailing_stop']) or \
        (position.type == mt5.ORDER_TYPE_SELL and current_price >= info['trailing_stop']):
            print(f"Trailing stop reached for position {position.ticket}. Closing...")
            self.close_position(position)

    def close_position(self, position):
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            print(f"Failed to get tick data for {self.symbol}")
            return False

        close_price = tick.bid if position.type == mt5.ORDER_TYPE_BUY else tick.ask
        print("Close price", close_price)
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": position.ticket,
            "symbol": self.symbol,
            "volume": position.volume,
            "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            "price": close_price,
            "deviation": self.deviation,
            "magic": 100,
            "comment": "Close position by trailing stop",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        print("CERRAR POSICION CONSOL", request)
        symbol = self.symbol
        order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        lot_size = position.volume
        price = close_price
        sl = 0
        tp = 0

        result = self.platform.close_order(position.ticket, symbol, lot_size,  5,0.5, self.deviation)
        #result = self.platform.place_order(request)
        print("Resultado",result)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Failed to close position {position.ticket}, error: {result}")
            return False
        logger.info(f"Position {position.ticket} closed successfully")
        closePrice = float(position.volume) * price
        operation_data = {
            "ticket": position.ticket,
            "statusOperation": 'Cerrada',
            "exitPrice": price,
            "profit": closePrice
        }
        api_response = self.api_client.update_operation(operation_data)
        logger.info("Operación actualizada en la API:", api_response)
        if position.ticket in self.position_info:
            del self.position_info[position.ticket]
        return True

    def manage_positions(self):
        positions = self.get_all_positions()
        tp = int(self.config["takeProfit"]) * 10
        for position in positions:
            self.update_trailing_stop(position)
            
            if position.type == mt5.ORDER_TYPE_BUY and mt5.symbol_info_tick(self.symbol).bid >= position.price_open + (tp * mt5.symbol_info(self.symbol).point):
                self.close_position(position)
                logger.info(f"Posición {position.ticket} cerrada por alcanzar take profit virtual")
            elif position.type == mt5.ORDER_TYPE_SELL and mt5.symbol_info_tick(self.symbol).ask <= position.price_open - (tp * mt5.symbol_info(self.symbol).point):
                self.close_position(position)
                logger.info(f"Posición {position.ticket} cerrada por alcanzar take profit virtual")

            # Verificar si se ha alcanzado el trailing stop
            current_price = mt5.symbol_info_tick(self.symbol).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(self.symbol).ask
            if position.ticket in self.position_info:
                if (position.type == mt5.ORDER_TYPE_BUY and current_price <= self.position_info[position.ticket]['trailing_stop']) or \
                (position.type == mt5.ORDER_TYPE_SELL and current_price >= self.position_info[position.ticket]['trailing_stop']):
                    logger.info(f"Trailing stop reached for position {position.ticket}. Closing...")
                    self.close_position(position)

    def get_data(self, timeframe):
        print("TO,E FRA,EEEEEE", timeframe)
        rates = mt5.copy_rates_from_pos(self.symbol, timeframe, 0, 40)
        print("RATES",len(rates))    
        if rates is None or len(rates) < 40:
            return
            
        df = pd.DataFrame(rates)
        df['timestamp'] = pd.to_datetime(df['time'], unit='s')
        df.drop('time', axis=1, inplace=True)

        df.rename(columns={'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'tick_volume': 'volume'}, inplace=True)
        df = pd.DataFrame(df)
        return df

    def calculate_rsi(self, df):
        print("IN CALCULATE TIME GRAME", df)
        if not isinstance(df, pd.DataFrame):
            return None
        delta = df['close'].diff(1)
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        return df

    def identify_order_blocks(self, df):
        block_high = df['high'].rolling(window=40).max()
        block_low = df['low'].rolling(window=40).min()
        df['order_block_zone'] = (df['close'] > block_low) & (df['close'] < block_high)
        return df

    def check_future_candles(self, df, future_count):
        last_row = df.iloc[-1]
        for i in range(1, future_count + 1):
            if len(df) <= i:
                return False
            future_candle = df.iloc[-i]
            if future_candle['close'] < last_row['close']:
                return True
        return False

    def calculate_sl_tp(self, direction: str, initial_price: float):
        point_value = mt5.symbol_info(self.symbol).point
        stop_loss_distance = 150 * point_value
        take_profit_distance = 200 * point_value

        sl = initial_price + stop_loss_distance if direction == 'sell' else initial_price - stop_loss_distance
        tp = initial_price + take_profit_distance if direction == "buy" else initial_price - take_profit_distance

        return sl, tp

    def get_account_balance(self):
        account_info = mt5.account_info()
        if account_info is None:
            logger.error("Failed to get account info")
            return None
        return account_info.balance

    def calculate_max_daily_loss(self):
        balance = self.get_account_balance()
        if balance is None:
            return 0
        return balance * 0.035  # 3.5% del balance

    def calculate_daily_loss(self):
        today = datetime.now().date()
        closed_positions = mt5.history_deals_get(date_from=datetime(today.year, today.month, today.day))
        if closed_positions is None:
            #logger.error("No trade history returned")
            return 0
        
        daily_loss = sum(deal.profit for deal in closed_positions if deal.profit < 0)
        

        open_positions = self.get_all_positions()
        unrealized_loss = sum(pos.profit for pos in open_positions if pos.profit < 0)
        
        return abs(daily_loss) + abs(unrealized_loss)

    def close_all_positions(self):
        positions = self.get_all_positions()
        for position in positions:
            self.close_position(position)
        logger.info("Todas las posiciones han sido cerradas debido a que se alcanzó el límite de pérdida diaria.")

    def place_order_with_replicas(self, symbol, order_type, lot_size, price, sl, tp, user):
        results = []
        print(self.num_replicas)
        for _ in range(self.num_replicas):
            print("REPLICASSS WITH INFO", _)
            result = self.platform.place_order(symbol, order_type, lot_size, price, sl, tp, user)
            print("RRRRR  ",result)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                results.append(result)
                print("TYPE", order_type)
                logger.info("Operación guardada en la API:")
                logger.info(f"Order placed successfully. Ticket: {result.order}")
            else:
                logger.error(f"Failed to place order. Error code: {result.retcode}")
        
        return results

    def run(self):
        self.reset_daily_counter()
        self.manage_positions()
        
        max_daily_loss = self.calculate_max_daily_loss()
        daily_loss = self.calculate_daily_loss()
        if daily_loss >= max_daily_loss:
            logger.warning(f"Se ha alcanzado la pérdida máxima diaria permitida ({daily_loss:.2f}). No se abrirán más posiciones hoy.")
            self.close_all_positions()           
            return

        open_positions_count = self.get_open_positions_count()

        if open_positions_count + 2 >= self.max_open_positions:
            print(f"Máximo de posiciones abiertas alcanzado ({open_positions_count}/{self.max_open_positions}). No se abrirán más posiciones.")
            return

        if self.orders_today + 2 >= self.max_orders_per_day:
            logger.info(f"Límite diario de órdenes alcanzado ({self.max_orders_per_day}). No se abrirán más posiciones hoy.")
            return

        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            logger.error(f"Failed to get tick data for {self.symbol}")
            return

        direction = self.config["direction"]
        initial_price = tick.ask if direction == "buy" else tick.bid
        sl, tp = self.calculate_sl_tp(direction, initial_price)
        print("Mission Control")

        df_15 = self.get_data(mt5.TIMEFRAME_M15)
        df_h1 = self.get_data(mt5.TIMEFRAME_H1)
        df_h4 = self.get_data(mt5.TIMEFRAME_H4)

        if df_15 is None or df_h1 is None or df_h4 is None:
            return

        df_m15 = self.calculate_rsi(df_15)

        df_m15 = self.identify_order_blocks(df_m15)
        df_h1 = self.identify_order_blocks(df_h1)
        df_h4 = self.identify_order_blocks(df_h4)

        if df_h4['order_block_zone'].iloc[-1] and self.check_future_candles(df_m15, self.future_candle_count):
            if df_m15['rsi'].iloc[-1] > 30: 
                print("Confirmando Order Block en H4 y M15. Ejecutando la operación.")
                print("DORECIOTN BUY", direction)
                print("Order")
                results = self.place_order_with_replicas(
                        self.symbol, 
                        mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL,
                        self.config["lotSize"], 
                        initial_price, 
                        sl, 
                        tp,
                        self.config["user"], 
                )
                if results:
                    self.orders_today += len(results)
                    print(f"Órdenes abiertas hoy: {self.orders_today}")
                return

        elif df_h1['order_block_zone'].iloc[-1] and self.check_future_candles(df_m15, self.future_candle_count):
            if df_m15['rsi'].iloc[-1] < 70:
                print("Confirmando Order Block en H1 y M15. Ejecutando la operación.")
                print("DORECIOTN SELL", direction)
                print("Order")
                results = self.place_order_with_replicas(
                        self.symbol, 
                        mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL,
                        self.config["lotSize"], 
                        initial_price, 
                        sl, 
                        tp,
                        self.config["user"], 
                )

                if results:
                    self.orders_today += len(results)
                    print(f"Órdenes abiertas hoy: {self.orders_today}")
                return
        else:
            print("No se detectó una señal fuerte.")