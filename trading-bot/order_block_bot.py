import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from typing import Dict
from trading_platform import TradingPlatform
from datetime import datetime, date
import time
import logging

logger = logging.getLogger(__name__)

class OrderBlockBot:
    def __init__(self, platform: TradingPlatform, config: Dict):
        self.platform = platform
        self.symbol = config["symbol"]
        self.timeframes =  [16385, 16388, 15] 
        self.config = config
        self.orders_today = 0
        self.last_order_date = None
        self.max_orders_per_day = 5
        self.max_open_positions = 5  # Nuevo límite de posiciones abiertas
        self.magic = 100
        self.deviation = 20
        self.trailing_stop_percent = 0.003 
        self.position_info = {} 
        self.daily_loss = 0
        self.max_daily_loss = self.calculate_max_daily_loss()
        self.num_replicas = 1


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

        print(f"Posición {position.ticket}: Tipo: {'Compra' if position.type == mt5.ORDER_TYPE_BUY else 'Venta'}")
        print(f"Precio actual: {current_price}, Precio de apertura: {position.price_open}")
        print(f"Stop Loss actual: {position.sl}, Take Profit: {position.tp}")
    
    
        if position.ticket not in self.position_info:
            self.position_info[position.ticket] = {
                'max_profit': position.profit,
                'trailing_stop': position.sl
            }

        info = self.position_info[position.ticket]
        logger.info(f"Máximo beneficio registrado: {info['max_profit']}, Trailing stop actual: {info['trailing_stop']}")
    


        point = mt5.symbol_info(self.symbol).point
        trailing_stop_distance = current_price * self.trailing_stop_percent / point
        logger.info(f"Distancia del trailing stop: {trailing_stop_distance * point}")


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
                        logger.error(f"Failed to update trailing stop for position {position.ticket}, error code: {result.retcode}")
                    else:
                        logger.info(f"Updated trailing stop for position {position.ticket} to {new_sl}")
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
                        logger.error(f"Failed to update trailing stop for position {position.ticket}, error code: {result.retcode}")
                    else:
                        logger.info(f"Updated trailing stop for position {position.ticket} to {new_sl}")
                        info['trailing_stop'] = new_sl

        # Verificar si se ha alcanzado el trailing stop
        if (position.type == mt5.ORDER_TYPE_BUY and current_price <= info['trailing_stop']) or \
        (position.type == mt5.ORDER_TYPE_SELL and current_price >= info['trailing_stop']):
            logger.info(f"Trailing stop reached for position {position.ticket}. Closing...")
            self.close_position(position)



    def close_position(self, position):
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            logger.error(f"Failed to get tick data for {self.symbol}")
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

        print("djefe", request)

        result = mt5.send(request)
        print("Resultado",result)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Failed to close position {position.ticket}, error: {result}")
            return False
        logger.info(f"Position {position.ticket} closed successfully")
        if position.ticket in self.position_info:
            del self.position_info[position.ticket]
        return True

    def manage_positions(self):
        positions = self.get_all_positions()
        for position in positions:
            self.update_trailing_stop(position)
            
            if position.type == mt5.ORDER_TYPE_BUY and mt5.symbol_info_tick(self.symbol).bid >= position.price_open + (200 * mt5.symbol_info(self.symbol).point):
                self.close_position(position)
                logger.info(f"Posición {position.ticket} cerrada por alcanzar take profit virtual")
            elif position.type == mt5.ORDER_TYPE_SELL and mt5.symbol_info_tick(self.symbol).ask <= position.price_open - (200 * mt5.symbol_info(self.symbol).point):
                self.close_position(position)
                logger.info(f"Posición {position.ticket} cerrada por alcanzar take profit virtual")

            # Verificar si se ha alcanzado el trailing stop
            current_price = mt5.symbol_info_tick(self.symbol).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(self.symbol).ask
            if position.ticket in self.position_info:
                if (position.type == mt5.ORDER_TYPE_BUY and current_price <= self.position_info[position.ticket]['trailing_stop']) or \
                (position.type == mt5.ORDER_TYPE_SELL and current_price >= self.position_info[position.ticket]['trailing_stop']):
                    logger.info(f"Trailing stop reached for position {position.ticket}. Closing...")
                    self.close_position(position)

    def check_order_block(self):
        order_block_signals = {tf: {'buy': False, 'sell': False} for tf in self.timeframes}
        for tf in range(len(self.timeframes)):
            current_candle = mt5.copy_rates_from_pos(self.symbol, self.timeframes[tf], 0, 2)

            if current_candle is None or len(current_candle) < 2:
                continue

            open_price_first_candle = current_candle[0][1]
            close_price_first_candle = current_candle[0][4]
            open_price_second_candle = current_candle[1][1]
            close_price_second_candle = current_candle[1][4]

            buy_order_block = close_price_first_candle > open_price_first_candle and close_price_second_candle < open_price_second_candle
            sell_order_block = close_price_first_candle < open_price_first_candle and close_price_second_candle > open_price_second_candle

            order_block_signals[self.timeframes[tf]]['buy'] = buy_order_block
            order_block_signals[self.timeframes[tf]]['sell'] = sell_order_block

        return order_block_signals

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

    def place_order_with_replicas(self, symbol, order_type, lot_size, price, sl, tp):
        results = []
        for _ in range(self.num_replicas):
            result = self.platform.place_order(symbol, order_type, lot_size, price, sl, tp)
            print("RRRRR  ",result)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                results.append(result)
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
            logger.info(f"Máximo de posiciones abiertas alcanzado ({open_positions_count}/{self.max_open_positions}). No se abrirán más posiciones.")
            return

        if self.orders_today + 2 >= self.max_orders_per_day:
            logger.info(f"Límite diario de órdenes alcanzado ({self.max_orders_per_day}). No se abrirán más posiciones hoy.")
            return

        order_block_signals = self.check_order_block()
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            logger.error(f"Failed to get tick data for {self.symbol}")
            return

        direction = self.config["direction"]
        initial_price = tick.ask if direction == "buy" else tick.bid
        sl, tp = self.calculate_sl_tp(direction, initial_price)

        for tf, signal in order_block_signals.items():
            if signal[direction]:
                logger.info(f"Se identificó un Order Block en {tf}. Abriendo posición de {direction}.")
                results = self.place_order_with_replicas(
                    self.symbol, 
                    mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL,
                    self.config["lot_size"], 
                    initial_price, 
                    sl, 
                    tp
                )

                if results:
                    self.orders_today += len(results)
                    logger.info(f"Órdenes abiertas hoy: {self.orders_today}")
                return
        
        logger.info("No se detectó una señal fuerte.")