import os
import json
from pprint import pprint
from web3 import Web3

BASE_PATH = os.environ.get('BASE_PATH')


def get_decimals_contract(contract):
    decimals = contract.functions.decimals().call()
    return int(decimals)


def get_abi_erc20():
    with open(os.path.abspath(BASE_PATH + "config_files/erc20.abi")) as f:
        abi: str = json.load(f)
    return abi


def get_balance_token_wallet_raw(w3, wallet, token):
    token_checksum = Web3.toChecksumAddress(token)
    wallet_checksum = Web3.toChecksumAddress(wallet)
    contract = w3.eth.contract(address=token_checksum, abi=get_abi_erc20())
    decimals = get_decimals_contract(wallet_checksum)
    res = contract.functions.balanceOf(wallet).call() / 10 ** decimals
    return res
