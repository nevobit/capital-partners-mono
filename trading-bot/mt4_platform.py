import zmq
import pandas as pd
import logging
from typing import Dict, List, Any
from trading_platform import TradingPlatform

logger = logging.getLogger(__name__)

class MT4Platform(TradingPlatform):
    def __init__(self, address: str = "tcp://localhost:5555"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(address)
    
    def connect():
        print("CONNECT TO MT4")

    def _send_request(self, message: str) -> str:
        try:
            self.socket.send_string(message)
            response = self.socket.recv_string()
            parts = response.split('|')
            
            if parts[0] != "OK":
                raise Exception(parts[1] if len(parts) > 1 else "Unknown error")
                
            return response
            
        except Exception as e:
            logger.error(f"Error in ZMQ request: {e}")
            raise
            
    def get_rates(self, symbol: str, timeframe: int, num_candles: int) -> pd.DataFrame:
        response = self._send_request(f"RATES|{symbol}|{timeframe}|{num_candles}")
        parts = response.split('|')[1:]  # Skip "OK"
        
        data = []
        for candle in parts:
            time, open_, high, low, close, volume = candle.split(',')
            data.append({
                'time': pd.to_datetime(time),
                'open': float(open_),
                'high': float(high),
                'low': float(low),
                'close': float(close),
                'volume': int(volume)
            })
            
        return pd.DataFrame(data)
        
    def place_order(self, symbol: str, order_type: int, volume: float, 
                   price: float, sl: float, tp: float, magic: int) -> int:
        response = self._send_request(
            f"ORDER|{symbol}|{order_type}|{volume}|{price}|{sl}|{tp}|{magic}"
        )
        return int(response.split('|')[1])
        
    def close_order(self, ticket: int) -> Dict[str, float]:
        response = self._send_request(f"CLOSE|{ticket}")
        parts = response.split('|')[1:]
        return {
            'close_price': float(parts[0]),
            'profit': float(parts[1])
        }
        
    def get_positions(self) -> List[Dict[str, Any]]:
        response = self._send_request("POSITIONS")
        if response == "OK":  # No positions
            return []
            
        positions = []
        for pos_data in response.split('|')[1:]:
            ticket, symbol, type_, lots, open_price, sl, tp, profit, comment, magic = pos_data.split(',')
            positions.append({
                'ticket': int(ticket),
                'symbol': symbol,
                'type': int(type_),
                'volume': float(lots),
                'open_price': float(open_price),
                'sl': float(sl),
                'tp': float(tp),
                'profit': float(profit),
                'comment': comment,
                'magic': int(magic)
            })
            
        return positions
