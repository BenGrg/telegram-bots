import requests
import pprint
import time
import json
import os
from binance.client import Client
from dataclasses import dataclass
import os
import sys

BASE_PATH = os.environ.get('BASE_PATH')
sys.path.insert(1, BASE_PATH + '/telegram-bots/src')

from libraries.util import float_to_str, pretty_number, keep_significant_number_float
import libraries.time_util as time_util

query_get_latest = """
query {  mints(first: 20, where: {pair_in: $PAIR}, orderBy: timestamp, orderDirection: desc) {
    transaction {
      id
      timestamp
      __typename
    }
    pair {
      token0 {
        id
        symbol
        __typename
      }
      token1 {
        id
        symbol
        __typename
      }
      __typename
    }
    to
    liquidity
    amount0
    amount1
    amountUSD
    __typename
  }
  burns(first: 20, where: {pair_in: $PAIR}, orderBy: timestamp, orderDirection: desc) {
    transaction {
      id
      timestamp
      __typename
    }
    pair {
      token0 {
        id
        symbol
        __typename
      }
      token1 {
        id
        symbol
        __typename
      }
      __typename
    }
    sender
    liquidity
    amount0
    amount1
    amountUSD
    __typename
  }
  swaps(first: 30, where: {pair_in: $PAIR}, orderBy: timestamp, orderDirection: desc) {
    transaction {
      id
      timestamp
      __typename
    }
    id
    pair {
      token0 {
        id
        symbol
        __typename
      }
      token1 {
        id
        symbol
        __typename
      }
      __typename
    }
    amount0In
    amount0Out
    amount1In
    amount1Out
    amountUSD
    to
    __typename
  }
}

"""


url_eth_price_gecko = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"

get_address_endpoint = "https://visitly.azurewebsites.net/api/pairs/ERC-20/"

etherscan_api_key = os.environ.get('ETH_API_KEY')

ethexplorer_holder_base_url = "https://ethplorer.io/service/service.php?data="

url_graphex_backend = "https://chartex.pro/api/history?symbol=UNISWAP%3A$SYMBOL&resolution=$RESOLUTION&from=$TFROM&to=$TTO"

gecko_chart_url = "https://api.coingecko.com/api/v3/coins/$TOKEN/market_chart/range?vs_currency=usd&from=$T_FROM&to=$T_TO"

symbol_chartex = {
    'ROT': 'ROT.5AE9E2',
    'SAV3': 'SAV3'
}

# Graph QL requests
query_eth = '''query blocks {
    t1: blocks(first: 1, orderBy: timestamp, orderDirection: desc, where: {timestamp_gt: %d, timestamp_lt: %d}) {
            number
    }
    t2: blocks(first: 1, orderBy: timestamp, orderDirection: desc, where: {timestamp_gt: %d, timestamp_lt: %d}) {
            number
    }
    tnow: blocks(first: 1, orderBy: timestamp, orderDirection: desc, where: {timestamp_lt: %d}) {
            number
    }
}'''

query_uni = '''query blocks {
    t1: token(id: "CONTRACT", block: {number: NUMBER_T1}) {
        derivedETH
    }
    t2: token(id: "CONTRACT", block: {number: NUMBER_T2}) {
        derivedETH
    }
    tnow: token(id: "CONTRACT", block: {number: NUMBER_TNOW}) {
        derivedETH
    }
    b1: bundle(id: "1", block: {number: NUMBER_T1}) {
        ethPrice
    }
    b2: bundle(id: "1", block: {number: NUMBER_T2}) {
        ethPrice
    }
    bnow: bundle(id: "1", block: {number: NUMBER_TNOW}) {
        ethPrice
    }
}
'''


query_eth_now = '''
query blocks {
    tnow: blocks(first: 1, orderBy: timestamp, orderDirection: desc, where: {timestamp_lt: %d}) {
            number
    }
}
'''


query_uni_now = '''query blocks {
    tnow: token(id: "CONTRACT", block: {number: NUMBER_TNOW}) {
        derivedETH
    }
    bnow: bundle(id: "1", block: {number: NUMBER_TNOW}) {
        ethPrice
    }
}
'''


req_graphql_vol24h_rot = '''{
  pairHourDatas(
    where: {hourStartUnix_gt: TIMESTAMP_MINUS_24_H, pair: "PAIR_CHANGE"})
    {
    hourlyVolumeUSD
  }
}'''


# t_from and t_to should be in epoch seconds.
# Resolution should be 1, 5, 15, 30, 60, 240, 720, 1D
def create_url_request_graphex(symbol, resolution, t_from, t_to):
    return url_graphex_backend \
        .replace("$SYMBOL", symbol) \
        .replace("$RESOLUTION", str(resolution)) \
        .replace("$TFROM", str(t_from)) \
        .replace("$TTO", str(t_to))


def get_gecko_chart(token_name, t_from, t_to):
    print("token: " + token_name +  "f_from: " + str(t_from) + " - t_to: " + str(t_to))
    gecko_url_updated = gecko_chart_url.replace("$TOKEN", token_name)\
        .replace("$T_FROM", str(t_from))\
        .replace("$T_TO", str(t_to))
    pprint.pprint(gecko_url_updated)
    res = requests.get(gecko_url_updated)
    return res


def get_binance_chart_data(token_name, t_from, t_to):
    delta = round(t_to - t_from)
    if delta < 6 * 3600:
        res = "1m"
    elif delta < 13 * 3600:
        res = "5m"
    elif delta < 24 * 3600 + 100:
        res = "5m"
    elif delta < 24 * 3600 * 7 + 100:
        res = "1h"
    elif delta < 24 * 3600 * 30 + 100:
        res = "6h"
    else:
        res = "1d"

    t_from_ms = t_from * 1000
    t_to_ms = t_to * 1000
    print("token: " + token_name + "f_from: " + str(t_from) + " - t_to: " + str(t_to) + " - resolution = " + str(res))
    clef = os.environ.get('BINANCE_API_KEY')
    secret = os.environ.get('BINANCE_API_SECRET')

    client = Client(clef, secret)

    candles = client.get_klines(symbol=token_name, interval=res, startTime=t_from_ms, endTime=t_to_ms)
    return candles


def get_graphex_data(token, resolution, t_from, t_to):
    if token in symbol_chartex:
        symbol = symbol_chartex.get(token)
    else:
        symbol = token
    url = create_url_request_graphex(symbol, resolution, t_from, t_to)
    resp = requests.get(url)
    return resp


def get_price_raw_now(graphql_client_eth, graphql_client_uni, token_contract):
    now = int(time.time())

    updated_eth_query = query_eth_now % now
    res_eth_query = graphql_client_eth.execute(updated_eth_query)
    json_resp_eth = json.loads(res_eth_query)

    latest_block = int(json_resp_eth['data']['tnow'][0]['number'])

    query_uni_updated = query_uni_now.replace("CONTRACT", token_contract) \
        .replace("NUMBER_TNOW", str(latest_block))

    res_uni_query = graphql_client_uni.execute(query_uni_updated)
    json_resp_uni = json.loads(res_uni_query)

    try:
        token_per_eth_now = float(json_resp_uni['data']['tnow']['derivedETH'])
    except KeyError:  # trying again, as sometimes the block that we query has not yet been indexed. For that, we read
        # the error message returned by uniswap and work on the last indexed block that is return in the error message
        last_block_indexed = str(res_uni_query).split('indexed up to block number ')[1][0:8]
        query_uni_updated = query_uni_now.replace("CONTRACT", token_contract) \
            .replace("NUMBER_TNOW", str(last_block_indexed))
        res_uni_query = graphql_client_uni.execute(query_uni_updated)
        json_resp_uni = json.loads(res_uni_query)
        token_per_eth_now = float(json_resp_uni['data']['tnow']['derivedETH'])

    eth_price_now = float(json_resp_uni['data']['bnow']['ethPrice'])

    token_price_now_usd = token_per_eth_now * eth_price_now

    return token_per_eth_now, token_price_now_usd


# from graphqlclient import GraphQLClient
# graphql_client_uni_2 = GraphQLClient('https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2')
# graphql_client_eth = GraphQLClient('https://api.thegraph.com/subgraphs/name/blocklytics/ethereum-blocks')
def get_price_raw(graphql_client_eth, graphql_client_uni, token_contract):

    now = int(time.time())

    before_7d = now - 3600 * 24 * 7
    before_7d_high = before_7d + 600

    before_1d = now - 3600 * 24
    before_1d_high = before_1d + 600

    updated_eth_query = query_eth % (before_7d, before_7d_high, before_1d, before_1d_high, now)
    res_eth_query = graphql_client_eth.execute(updated_eth_query)
    json_resp_eth = json.loads(res_eth_query)

    block_from_7d = int(json_resp_eth['data']['t1'][0]['number'])
    block_from_1d = int(json_resp_eth['data']['t2'][0]['number'])
    latest_block = int(json_resp_eth['data']['tnow'][0]['number'])

    query_uni_updated = query_uni.replace("CONTRACT", token_contract) \
        .replace("NUMBER_T1", str(block_from_7d)) \
        .replace("NUMBER_T2", str(block_from_1d)) \
        .replace("NUMBER_TNOW", str(latest_block))

    res_uni_query = graphql_client_uni.execute(query_uni_updated)
    json_resp_uni = json.loads(res_uni_query)


    try:
        token_per_eth_now = float(json_resp_uni['data']['tnow']['derivedETH'])
    except KeyError:  # trying again, as sometimes the block that we query has not yet been indexed. For that, we read
        # the error message returned by uniswap and work on the last indexed block that is return in the error message
        # TODO: work with regex as block numbers can be < 10000000
        last_block_indexed = str(res_uni_query).split('indexed up to block number ')[1][0:8]
        query_uni_updated = query_uni.replace("CONTRACT", token_contract) \
            .replace("NUMBER_T1", str(block_from_7d)) \
            .replace("NUMBER_T2", str(block_from_1d)) \
            .replace("NUMBER_TNOW", str(last_block_indexed))
        res_uni_query = graphql_client_uni.execute(query_uni_updated)
        json_resp_uni = json.loads(res_uni_query)
        token_per_eth_now = float(json_resp_uni['data']['tnow']['derivedETH'])

    try:
        token_per_eth_7d = float(json_resp_uni['data']['t1']['derivedETH']) if 'derivedETH' in json_resp_uni['data']['t1'] else 0.0
    except TypeError:
        token_per_eth_7d = None
    try:
        token_per_eth_1d = float(json_resp_uni['data']['t2']['derivedETH']) if 'derivedETH' in json_resp_uni['data']['t2'] else 0.0
    except TypeError:
        token_per_eth_1d = None

    eth_price_7d = float(json_resp_uni['data']['b1']['ethPrice'])
    eth_price_1d = float(json_resp_uni['data']['b2']['ethPrice'])
    eth_price_now = float(json_resp_uni['data']['bnow']['ethPrice'])

    token_price_7d_usd = token_per_eth_7d * eth_price_7d if token_per_eth_7d is not None else None
    token_price_1d_usd = token_per_eth_1d * eth_price_1d if token_per_eth_1d is not None else None
    token_price_now_usd = token_per_eth_now * eth_price_now

    return (
        token_per_eth_7d, token_price_7d_usd, token_per_eth_1d, token_price_1d_usd, token_per_eth_now,
        token_price_now_usd)


def get_supply_cap_raw(contract_addr, decimals):
    base_addr = 'https://api.etherscan.io/api?module=stats&action=tokensupply&contractaddress=' + contract_addr + '&apikey=' + etherscan_api_key
    supply_cap = float(requests.post(base_addr).json()['result']) / decimals
    return supply_cap


# return price 7 days ago, price 1 day ago, volume last 24h
def get_volume_24h(graphclient_uni, pair_contract):
    now = int(time.time())
    yesterday = now - 3600 * 24
    updated_req = req_graphql_vol24h_rot.replace("TIMESTAMP_MINUS_24_H", str(yesterday)).replace("PAIR_CHANGE",
                                                                                                 pair_contract)
    res = graphclient_uni.execute(updated_req)
    json_resp_eth = json.loads(res)

    all_values = json_resp_eth['data']['pairHourDatas']

    amount = 0
    for value in all_values:
        amount += round(float(value['hourlyVolumeUSD']))

    return amount


def get_number_holder_token(token):
    url = ethexplorer_holder_base_url + token
    res = requests.get(url).json()
    try:
        holders = res['pager']['holders']['records']
    except KeyError:
        holders = -1
    return int(holders)


def get_token_contract_address(token_ticker):
    if token_ticker == "eth" or token_ticker == "ETH":
        return "0x0000000000000000000000000000000000000000"
    url = get_address_endpoint + token_ticker
    res = requests.get(url).json()
    for i in res:
        if 'token1' in i:
            if 'symbol' in i['token1']:
                if i['token1']['symbol'].lower() == token_ticker.lower():
                    if 'id' in i['token1']:
                        return i['token1']['id']

                elif i['token0']['symbol'].lower() == token_ticker.lower():
                    if 'id' in i['token0']:
                        return i['token0']['id']
    return None
    # pprint.pprint(res)


def get_eth_price_now():
    res = requests.get(url_eth_price_gecko).json()
    if 'ethereum' in res:
        if 'usd' in res['ethereum']:
            return int(res['ethereum']['usd'])
    return 0


def get_gas_price_raw():
    url = "https://ethgasstation.info/json/ethgasAPI.json"
    return requests.get(url).json()


@dataclass(frozen=True)
class Swap:
    buy: (str, int)
    sell: (str, int)
    id: str
    timestamp: int

    def is_positif(self):
        return self.buy[0] == 'WETH'

    def to_string(self, eth_price):
        message = ""
        time_since = time_util.get_minute_diff(self.timestamp)
        if self.is_positif():
            price_usd = pretty_number(self.buy[1] * eth_price)
            message += "🟢 Buy  " + pretty_number(self.sell[1])[0:9] + " " + self.sell[0] + " for " \
                       + pretty_number(self.buy[1])[0:9] + " ETH <code>($" + price_usd[0:6] + ")</code> " \
                       + str(time_since) + " mins ago."
        else:
            price_usd = pretty_number(self.sell[1] * eth_price)
            message += "🔴 Sell " + pretty_number(self.buy[1])[0:9] + " " + self.buy[0] + " for " \
                       + pretty_number(self.sell[1])[0:9] + " ETH <code>($" + price_usd[0:6] + ")</code> " \
                       + str(time_since) + " mins ago."
        message += " | " + '<a href="etherscan.io/tx/' + str(self.id) + '">view</a>'
        return message


@dataclass(frozen=True)
class Mint:
    token_0: (str, int)
    token_1: (str, int)
    id: str
    timestamp: int

    def to_string(self, eth_price):
        if self.token_0[0] == 'WETH':
            price_usd = pretty_number(self.token_0[1] * eth_price)
        else:
            price_usd = pretty_number(self.token_1[1] * eth_price)
        time_since = time_util.get_minute_diff(self.timestamp)
        message = "💚 Add " + pretty_number(self.token_0[1])[0:6] + ' ' + self.token_0[0] + " and " +\
                  pretty_number(self.token_1[1])[0:6] + ' ' + self.token_1[0] + " in liquidity" \
                  + " <code>($" + price_usd[0:6] + ")</code> " \
                  + str(time_since) + " mins ago."
        message += " | " + '<a href="etherscan.io/tx/' + str(self.id) + '">view</a>'
        return message


@dataclass(frozen=True)
class Burn:
    token_0: (str, int)
    token_1: (str, int)
    id: str
    timestamp: int

    def to_string(self, eth_price):
        if self.token_0[0] == 'WETH':
            price_usd = pretty_number(self.token_0[1] * eth_price)
        else:
            price_usd = pretty_number(self.token_1[1] * eth_price)
        time_since = time_util.get_minute_diff(self.timestamp)
        message = "💔 Removed " + pretty_number(self.token_0[1])[0:6] + ' ' + self.token_0[0] + " and " \
                  + pretty_number(self.token_1[1])[0:6] + ' ' + self.token_1[0] + " in liquidity" \
                  + " <code>($" + price_usd[0:6] + ")</code> "\
                  + str(time_since) + " mins ago."
        message += " | " + '<a href="etherscan.io/tx/' + str(self.id) + '">view</a>'
        return message


def get_latest_actions(pair, graphql_client_uni):
    updated_eth_query = query_get_latest.replace("$PAIR", '["' + pair + '"]')
    res_eth_query = graphql_client_uni.execute(updated_eth_query)
    json_resp_eth = json.loads(res_eth_query)
    return json_resp_eth


def parse_swaps(res):
    swaps = res['data']['swaps']
    l_swaps = []
    for swap in swaps:
        amount0In = float(swap['amount0In'])
        amount0Out = float(swap['amount0Out'])
        amount1In = float(swap['amount1In'])
        amount1Out = float(swap['amount1Out'])
        timestamp = int(swap['transaction']['timestamp'])
        id = swap['id'][:-2]
        token0, token1 = parse_pair(swap['pair'])
        if amount0In > 0:
            l_swaps.append(Swap((token0, amount0In), (token1, amount1Out), id, timestamp))
        else:
            l_swaps.append(Swap((token1, amount1In), (token0, amount0Out), id, timestamp))
    return l_swaps


def parse_mint(res):
    mints = res['data']['mints']
    l_mints = []
    for mint in mints:
        amount0 = float(mint['amount0'])
        amount1 = float(mint['amount1'])
        timestamp = int(mint['transaction']['timestamp'])
        id = mint['transaction']['id']
        token0, token1 = parse_pair(mint['pair'])
        l_mints.append(Mint((token0, amount0), (token1, amount1), id, timestamp))
    return l_mints


def parse_burns(res):
    burns = res['data']['burns']
    l_burns = []
    for burn in burns:
        amount0 = float(burn['amount0'])
        amount1 = float(burn['amount1'])
        timestamp = int(burn['transaction']['timestamp'])
        id = burn['transaction']['id']
        token0, token1 = parse_pair(burn['pair'])
        l_burns.append(Burn((token0, amount0), (token1, amount1), id, timestamp))
    return l_burns


def parse_pair(pair):
    """parse a json pair res queried with last actions"""
    token0 = pair['token0']['symbol']
    token1 = pair['token1']['symbol']
    return token0, token1


# TODO: stuff will need to be moved from here
def pretty_print(pair, graphql_client_uni):
    eth_price = get_eth_price_now()
    last_actions = get_latest_actions(pair.lower(), graphql_client_uni)
    parsed_swaps = parse_swaps(last_actions)
    parsed_mints = parse_mint(last_actions)
    parsed_burns = parse_burns(last_actions)
    all_actions = parsed_burns + parsed_mints + parsed_swaps
    all_actions_sorted = sorted(all_actions, key=lambda x: x.timestamp, reverse=True)
    all_actions_light = all_actions_sorted[0:5]
    strings = list(map(lambda x: x.to_string(eth_price), all_actions_light))
    string = '\n'.join(strings)
    return string


@dataclass(frozen=True)
class GasSpent:
    amountTx: int
    eth_spent: float
    total_gas: int
    avg_gas_price: float
    success: (int, int)
    fail: (int, int)

    def to_string(self):
        eth_price_now = get_eth_price_now()
        amount_spent_on_gas_raw = keep_significant_number_float(self.eth_spent, 2)
        amount_spent_on_gas_usd = keep_significant_number_float(amount_spent_on_gas_raw * eth_price_now, 2)
        avg_gas_cost = keep_significant_number_float(self.avg_gas_price, 1)
        eth_success = keep_significant_number_float(self.success[1] / 10**18, 3)
        eth_fail = keep_significant_number_float(self.fail[1] / 10**18, 3)
        eth_success_dollar = keep_significant_number_float(eth_success * eth_price_now, 3)
        eth_fail_dollar = keep_significant_number_float(eth_fail * eth_price_now, 3)
        message = "Total number of tx: " + str(self.amountTx) + '\n' \
                  + "Amount spent on gas: Ξ" + str(amount_spent_on_gas_raw) + " = $" + str(amount_spent_on_gas_usd) + '\n' \
                  + "Average gas spent per tx = " + str(avg_gas_cost) + '\n' \
                  + "Tx successful = " + str(self.success[0]) + " -> Ξ" + str(eth_success) + " spent in gas ($" + str(eth_success_dollar) + ')\n' \
                  + "Tx failed = " + str(self.fail[0]) + " -> Ξ" + str(eth_fail) + " spent in gas ($" + str(eth_fail_dollar) + ')'
        return message


def get_gas_spent(address):
    url = "https://api.etherscan.io/api?module=account&action=txlist&address=$ADDR&startblock=0&endblock=99999999&sort=asc&apikey=$APIKEY"
    url_prepared = url.replace("$APIKEY", etherscan_api_key).replace("$ADDR", address)
    results = requests.get(url_prepared).json()
    txs = results['result']
    total_gas_success = 0
    total_gas_fail = 0
    error_number = 0
    total_cost_success = 0
    total_cost_fail = 0
    avg_price = 0
    for tx in txs:
        gas_price_tx = int(tx['gasPrice'])
        gas_used = int(tx['gasUsed'])
        avg_price += gas_price_tx
        if int(tx['isError']) == 1:
            error_number += 1
            total_gas_fail += gas_used
            total_cost_fail += gas_used * gas_price_tx
        else:
            total_gas_success += gas_used
            total_cost_success += gas_used * gas_price_tx
    avg_price = round(avg_price / len(txs))
    total_gas = total_gas_success + total_cost_fail
    avg_price_rounded = avg_price / 10**9
    total_cost = ((total_cost_fail + total_cost_success) / 10**18)
    return GasSpent(len(txs), total_cost, total_gas, avg_price_rounded, (len(txs) - error_number, total_cost_success), (error_number, total_cost_fail))


def main():
    pass
    # token = "WBTC"
    # k_hours = 0
    # k_days = 1
    # t_to = int(time.time())
    # t_from = t_to - (k_days * 3600 * 24) - (k_hours * 3600)
    # resolution = 5
    # res = get_graphex_data(token, resolution, t_from, t_to).json()
    # pprint.pprint(res)


if __name__ == '__main__':
    main()
