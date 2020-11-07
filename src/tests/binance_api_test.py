from binance.client import Client
from pprint import pprint
import os

clef = os.environ.get('BINANCE_API_KEY')
secret = os.environ.get('BINANCE_API_SECRET')

client = Client(clef, secret)

t_from = 1604658519000
to = 1604744919000

candles = client.get_klines(symbol='BTCUSDT', interval="5m", startTime=t_from, endTime=to)

pprint(candles)

if __name__ == '__main__':
    pass