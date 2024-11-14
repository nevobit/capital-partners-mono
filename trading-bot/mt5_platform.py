import logging
import MetaTrader5 as mt5
import pandas as pd
from trading_platform import TradingPlatform
from config import load_config
from api_client import APIClient
import time 
logger = logging.getLogger(__name__)

class MT5Platform(TradingPlatform):
    def __init__(self, server: str, login: int, password: str):
        self.server = server
        self.login = login
        self.password = password
        self.config = load_config()
        self.api_client = APIClient(self.config['api_base_url'])
        self.open_positions = {}

    def connect(self):
        try:
            mt5.login(login=self.login, server=self.server, password=self.password)
            if not mt5.initialize(login=self.login, server=self.server, password=self.password):
                raise Exception(mt5.last_error())
            logger.info(f"Conectado a MT5: {self.server}")
        except Exception as e:
            logger.error(f"Error al conectar a MT5: {e}")
            time.sleep(5)
            self.connect()

    def get_market_data(self, symbol: str, timeframe: int, num_candles: int):
        try:
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
            return pd.DataFrame(rates)
        except Exception as e:
            logger.error(f"Error al obtener datos de MT5: {e}")
            return pd.DataFrame()

    def place_order(self, symbol: str, order_type: str, volume: float, price: float, sl: float, tp: float, user: str):
        try:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(volume),
                "type": order_type,
                "price": price,
                "sl": sl,
                "deviation": 20,
                "magic": 100,
                "comment": "Order Block Trade",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": 0,
            }
       
            result = mt5.order_send(request)
            operation_data = {
                "type": 'Compra' if order_type == 0 else 'Venta' ,  # Por ejemplo, 'compra' o 'venta'
                "instrument": symbol,
                "entryPrice": str(price),
                "exitPrice": str(tp),  # Precio de Take Profit
                "profit": 0,  # Ganancia (ejemplo simple)
                "statusOperation": "Abierta",  # O 'cerrada', según corresponda
                "date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),  # Fecha en formato ISO
                "ticket": str(result.order),  # Número de ticket
                "volume": volume,
                "account": self.login,
                "user": user
            }
            api_response = self.api_client.create_operation(operation_data)
            logger.info("Operación guardada en la API:", api_response)

            logger.info(f"Orden colocada en MT5: {result}")
            return result
        except Exception as e:
            logger.error(f"Error al colocar orden en MT5: {e}")
            return None

    def close_order(self, ticket: int, symbol: str, volume: float, max_attempts: int = 5, delay_between_attempts: float = 0.5, deviation: int = 1000):
        """
        Cierra una orden específica en MetaTrader 5, manejando cambios de precio.

        :param ticket: El número de ticket de la orden a cerrar.
        :param symbol: El símbolo del instrumento financiero.
        :param volume: El volumen de la orden a cerrar.
        :param max_attempts: Número máximo de intentos para cerrar la orden.
        :param delay_between_attempts: Tiempo de espera entre intentos (en segundos).
        :param deviation: La desviación máxima del precio permitida (en puntos).
        :return: El resultado de la operación de cierre o None si falla.
        """
        for attempt in range(max_attempts):
            try:
                # Obtener información de la posición
                position = mt5.positions_get(ticket=ticket)
                print('POSTION 95', position)
                if not position:
                    logger.error(f"No se encontró la posición con ticket {ticket}")
                    return None

                position = position[0]
                order_type = mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY
                print("ODER TYPE SELL", mt5.ORDER_TYPE_SELL)
                # Obtener el precio actual
                current_tick = mt5.symbol_info_tick(symbol)
                if current_tick is None:
                    logger.error(f"No se pudo obtener la información del tick para {symbol}")
                    return None

                price = current_tick.bid if order_type == mt5.ORDER_TYPE_SELL else current_tick.ask

                # Preparar la solicitud
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "position": ticket,
                    "symbol": symbol,
                    "volume": float(volume),
                    "type": order_type,
                    "price": price,
                    "deviation": deviation,
                    "magic": 100,
                    "comment": f"Cierre de orden (intento {attempt + 1})",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }

                # Enviar la orden de cierre
                result = mt5.order_send(request)

               
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    closePrice = float(volume) * price
                    profit = position.profit
                    operation_data = {
                        "ticket": ticket,
                        "statusOperation": 'Cerrada',
                        "exitPrice": price,
                        "profit": profit
                    }
                    logger.info(f"Orden cerrada exitosamente en el intento {attempt + 1}: {result}")
                    api_response = self.api_client.update_operation(operation_data)
                    logger.info("Operación actualizada en la API:", api_response)
                    return result
                elif result.retcode == mt5.TRADE_RETCODE_REQUOTE:
                    logger.warning(f"Requote recibido en el intento {attempt + 1}. Reintentando...")
                else:
                    logger.error(f"Error al cerrar la orden en el intento {attempt + 1}: {result.comment}")

                # Esperar antes del siguiente intento
                time.sleep(delay_between_attempts)

            except Exception as e:
                logger.error(f"Error inesperado al cerrar la orden en MT5 (intento {attempt + 1}): {e}")

        logger.error(f"No se pudo cerrar la orden después de {max_attempts} intentos")
        return None

    def monitor_operations(self, check_interval: int = 10):
        """
        Monitorea continuamente las operaciones abiertas y verifica si alguna se cierra por stop loss o take profit.
        Si una operación se cierra, guarda los datos relevantes en la base de datos mediante la API.
        
        :param check_interval: Intervalo de tiempo en segundos entre cada verificación.
        """
        logger.info("Iniciando monitoreo de operaciones...")
        
        while True:
            # Obtener las posiciones abiertas en MetaTrader 5
            positions = mt5.positions_get()
            current_open_tickets = {pos.ticket for pos in positions}  # Tickets de posiciones abiertas actualmente

            # Revisar operaciones previamente abiertas que ya no están en la lista
            closed_tickets = set(self.open_positions.keys()) - current_open_tickets

            for ticket in closed_tickets:
                # Extraer los detalles de la operación cerrada
                position = self.open_positions.pop(ticket)
                print('POSITION', position)
                # Guardar los datos de la operación cerrada en la base de datos
                operation_data = {
                    "ticket": str(ticket),
                    "statusOperation": 'Cerrada',
                    "exitPrice": position.price_current,     # Precio de cierre
                    "profit": position.profit,       # Ganancia/perdida final de la operación
                }
                logger.info(f"Operación cerrada automáticamente: {operation_data}")
                
                # Guardar en la base de datos mediante la API
                try:
                    api_response = self.api_client.update_operation(operation_data)
                    logger.info(f"Operación guardada en la API: {api_response}")
                except Exception as e:
                    logger.error(f"Error al guardar la operación en la API: {e}")

            # Actualizar el estado de las posiciones abiertas
            self.open_positions = {pos.ticket: pos for pos in positions}

            # Esperar antes de la siguiente verificación
            time.sleep(check_interval)