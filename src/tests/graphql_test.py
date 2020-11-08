import json

from graphqlclient import GraphQLClient
from pprint import pprint


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


def get_latest_actions(pair, graphql_client_uni):
    updated_eth_query = query_get_latest.replace("$PAIR", '["' + pair + '"]')
    res_eth_query = graphql_client_uni.execute(updated_eth_query)
    json_resp_eth = json.loads(res_eth_query)
    return json_resp_eth


if __name__ == '__main__':
    pair = "0x6e31ef0b62a8abe30d80d35476ca78897dffa769"
    graphql_client = GraphQLClient('https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2')
    res = get_latest_actions(pair, graphql_client)
    pprint(res)
