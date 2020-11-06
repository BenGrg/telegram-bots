import requests
import pprint
import time
import json
import os

url_eth_price_gecko = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"

get_address_endpoint = "https://visitly.azurewebsites.net/api/pairs/ERC-20/"

etherscan_api_key = os.environ.get('ETH_API_KEY')

ethexplorer_holder_base_url = "https://ethplorer.io/service/service.php?data="

url_graphex_backend = "https://chartex.pro/api/history?symbol=UNISWAP%3A$SYMBOL&resolution=$RESOLUTION&from=$TFROM&to=$TTO"

symbol_chartex = {
    'ROT': 'ROT.5AE9E2'
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
        # TODO: work with regex as block numbers can be < 10000000
        last_block_indexed = str(res_uni_query).split('indexed up to block number ')[1][0:8]
        query_uni_updated = query_uni_now.replace("CONTRACT", token_contract) \
            .replace("NUMBER_TNOW", str(last_block_indexed))
        res_uni_query = graphql_client_uni.execute(query_uni_updated)
        json_resp_uni = json.loads(res_uni_query)
        pprint(json_resp_uni)
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

    # pprint.pprint(json_resp_uni)

    try:
        token_per_eth_now = float(json_resp_uni['data']['tnow']['derivedETH'])
    except KeyError:  # trying again, as sometimes the block that we query has not yet been indexed. For that, we read
        # the error message returned by uniswap and work on the last indexed block that is return in the error message
        # TODO: work with regex as block numbers can be < 10000000
        pprint.pprint(res_uni_query)
        last_block_indexed = str(res_uni_query).split('indexed up to block number ')[1][0:8]
        query_uni_updated = query_uni.replace("CONTRACT", token_contract) \
            .replace("NUMBER_T1", str(block_from_7d)) \
            .replace("NUMBER_T2", str(block_from_1d)) \
            .replace("NUMBER_TNOW", str(last_block_indexed))
        res_uni_query = graphql_client_uni.execute(query_uni_updated)
        json_resp_uni = json.loads(res_uni_query)
        pprint.pprint(json_resp_uni)
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
    if token_ticker == "eth" or "ETH":
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
            return res['ethereum']['usd']
    return 0

#
# def main():
#     res = get_eth_price_now()
#     pprint.pprint(res)
#
#
# if __name__ == '__main__':
#     main()
