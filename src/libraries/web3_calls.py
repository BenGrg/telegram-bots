import os
import json
from pprint import pprint

BASE_PATH = os.environ.get('BASE_PATH')


def get_decimals_contract(contract):
    decimals = contract.functions.decimals().call()
    return int(decimals)


def get_abi_erc20():
    with open(os.path.abspath(BASE_PATH + "erc20.abi")) as f:
        abi: str = json.load(f)
    return abi


def get_balance_token_wallet_raw(w3, wallet, token):
    contract = w3.eth.contract(address=token, abi=get_abi_erc20())
    decimals = get_decimals_contract(contract)
    res = contract.functions.balanceOf(wallet).call() / 10 ** decimals
    return res
