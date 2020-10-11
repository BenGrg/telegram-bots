import requests
import pprint
import time

url_graphex_backend = "https://chartex.pro/api/history?symbol=UNISWAP%3A$SYMBOL&resolution=$RESOLUTION&from=$TFROM&to=$TTO"

symbol_chartex = {
    'ROT': 'ROT.5AE9E2'
}


# t_from and t_to should be in epoch seconds.
# Resolution should be 1, 5, 15, 30, 60, 240, 720, 1D
def create_url_request_graphex(symbol, resolution, t_from, t_to):
    return url_graphex_backend\
        .replace("$SYMBOL", symbol)\
        .replace("$RESOLUTION", str(resolution)) \
        .replace("$TFROM", str(t_from))\
        .replace("$TTO", str(t_to))


def get_graphex_data(token, resolution, t_from, t_to):
    if token in symbol_chartex:
        symbol = symbol_chartex.get(token)
    else:
        symbol = token
    url = create_url_request_graphex(symbol, resolution, t_from, t_to)
    resp = requests.get(url)
    return resp


# def main():
#     now = int(time.time())
#     before = now - 3600 * 5
#     get_graphex_data("ROT", 5, before, now)
#
#
# if __name__ == '__main__':
#     main()
