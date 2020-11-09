import json

from graphqlclient import GraphQLClient
from pprint import pprint
from dataclasses import dataclass
from datetime import datetime


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

# create a new context for this task
import decimal
ctx = decimal.Context()

# 20 digits should be enough for everyone :D
ctx.prec = 20

def float_to_str(f):
    """
    Convert the given float to a string,
    without resorting to scientific notation
    """
    d1 = ctx.create_decimal(repr(f))
    return format(d1, 'f')


@dataclass(frozen=True)
class Swap:
    buy: (str, int)
    sell: (str, int)
    id: str
    timestamp: int

    def is_positif(self):
        return self.sell[0] == 'WETH'

    def to_string(self, eth_price):
        message = ""
        # time_now = time_util.get_time_diff(self.timestamp)
        if self.is_positif():
            message += "👍 Buy  " + float_to_str(self.buy[1])[0:6] + " " + self.buy[0] + " for " + float_to_str(self.sell[1])[0:6] + " ETH."
        else:
            message += "👎 Sell " + float_to_str(self.sell[1])[0:6] + " " + self.sell[0] + " for " + float_to_str(self.buy[1])[0:6] + " ETH."
        message += " | " + '<a href=ehterscan.io/tx/' + str(self.id) + '">view</a>'
        return message


@dataclass(frozen=True)
class Mint:
    token_0: (str, int)
    token_1: (str, int)
    id: str
    timestamp: int

    def to_string(self):
        message = "🏦 Add " + float_to_str(self.token_0[1])[0:6] + self.token_0[0] + " and " + float_to_str(self.token_1[1])[0:6] + self.token_1[0] + " in liquidity."
        message += " | " + '<a href=ehterscan.io/tx/' + str(self.id) + '">view</a>'
        return message


@dataclass(frozen=True)
class Burn:
    token_0: (str, int)
    token_1: (str, int)
    id: str
    timestamp: int

    def to_string(self):
        message = "💥 Removed " + float_to_str(self.token_0[1])[0:6] + self.token_0[0] + " and " + float_to_str(self.token_1[1])[0:6] + self.token_1[0] + " in liquidity."
        message += " | " + '<a href=ehterscan.io/tx/' + str(self.id) + '">view</a>'
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
        id = swap['id']
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


if __name__ == '__main__':
    pair = "0x6e31ef0b62a8abe30d80d35476ca78897dffa769"
    graphql_client = GraphQLClient('https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2')
    res = get_latest_actions(pair, graphql_client)
    parsed_swaps = parse_swaps(res)
    parsed_swaps_sorted = sorted(parsed_swaps, key=lambda x: x.timestamp, reverse=True)
    parsed_mints = parse_mint(res)
    parsed_burns = parse_burns(res)
    all_actions = parsed_burns + parsed_mints + parsed_swaps
    all_actions_sorted = sorted(all_actions, key=lambda x: x.timestamp, reverse=True)
    all_actions_light = all_actions_sorted[0:10]
    strings = list(map(lambda x: x.to_string(), all_actions_light))
    string = '\n'.join(strings)
    print(string)
