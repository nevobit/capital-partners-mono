from datetime import datetime
import pytz

LONDON_TZ = pytz.timezone('Europe/London')

def is_london_market_open():
    now = datetime.now(LONDON_TZ)
    if now.weekday() >= 5:  # Es fin de semana
        return False
    market_open = now.replace(hour=0, minute=0, second=0, microsecond=0)
    market_close = now.replace(hour=23, minute=59, second=59, microsecond=0)
    return market_open <= now < market_close