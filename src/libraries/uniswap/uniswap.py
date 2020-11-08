import os
import json
import time
import logging
import functools
from typing import List, Any, Optional, Callable, Union, Tuple, Dict

from web3 import Web3
from web3.eth import Contract
from web3.contract import ContractFunction
from web3.types import (
    TxParams,
    Wei,
    Address,
    ChecksumAddress,
    ENS,
    Nonce,
    HexBytes,
)
from eth_utils import is_same_address
from eth_typing import AnyAddress

ETH_ADDRESS = "0x0000000000000000000000000000000000000000"

logger = logging.getLogger(__name__)

# TODO: Consider dropping support for ENS altogether and instead use AnyAddress
AddressLike = Union[Address, ChecksumAddress, ENS]


class InvalidToken(Exception):
    def __init__(self, address: Any) -> None:
        Exception.__init__(self, f"Invalid token address: {address}")


class InsufficientBalance(Exception):
    def __init__(self, had: int, needed: int) -> None:
        Exception.__init__(self, f"Insufficient balance. Had {had}, needed {needed}")


def _load_abi(name: str) -> str:
    path = f"{os.path.dirname(os.path.abspath(__file__))}/assets/"
    with open(os.path.abspath(path + f"{name}.abi")) as f:
        abi: str = json.load(f)
    return abi


def supports(versions: List[int]) -> Callable:
    def g(f: Callable) -> Callable:
        @functools.wraps(f)
        def check_version(self: "Uniswap", *args: List, **kwargs: Dict) -> Any:
            if self.version not in versions:
                raise Exception(
                    "Function does not support version of Uniswap passed to constructor"
                )
            return f(self, *args, **kwargs)

        return check_version

    return g


def _str_to_addr(s: str) -> AddressLike:
    if s.startswith("0x"):
        return Address(bytes.fromhex(s[2:]))
    elif s.endswith(".eth"):
        return ENS(s)
    else:
        raise Exception("Could't convert string {s} to AddressLike")


def _addr_to_str(a: AddressLike) -> str:
    if isinstance(a, bytes):
        # Address or ChecksumAddress
        addr: str = Web3.toChecksumAddress("0x" + bytes(a).hex())
        return addr
    elif isinstance(a, str):
        if a.endswith(".eth"):
            # Address is ENS
            raise Exception("ENS not supported for this operation")
        elif a.startswith("0x"):
            addr = Web3.toChecksumAddress(a)
            return addr
        else:
            raise InvalidToken(a)


def _validate_address(a: AddressLike) -> None:
    assert _addr_to_str(a)


_netid_to_name = {1: "mainnet", 4: "rinkeby"}


class Uniswap:
    def __init__(
            self,
            web3: Web3 = None,
            version: int = 2,
    ) -> None:
        self.version = version

        # TODO: Write tests for slippage

        if web3:
            self.w3 = web3
        else:
            # Initialize web3. Extra provider for testing.
            raise Exception("Need web3")

        netid = int(self.w3.net.version)
        if netid in _netid_to_name:
            self.network = _netid_to_name[netid]
        else:
            raise Exception(f"Unknown netid: {netid}")
        logger.info(f"Using {self.w3} ('{self.network}')")

        # This code automatically approves you for trading on the exchange.
        # max_approval is to allow the contract to exchange on your behalf.
        # max_approval_check checks that current approval is above a reasonable number
        # The program cannot check for max_approval each time because it decreases
        # with each trade.
        self.max_approval_hex = f"0x{64 * 'f'}"
        self.max_approval_int = int(self.max_approval_hex, 16)
        self.max_approval_check_hex = f"0x{15 * '0'}{49 * 'f'}"
        self.max_approval_check_int = int(self.max_approval_check_hex, 16)

        if self.version == 1:
            factory_contract_addresses = {
                "mainnet": "0xc0a47dFe034B400B47bDaD5FecDa2621de6c4d95",
                "ropsten": "0x9c83dCE8CA20E9aAF9D3efc003b2ea62aBC08351",
                "rinkeby": "0xf5D915570BC477f9B8D6C0E980aA81757A3AaC36",
                "kovan": "0xD3E51Ef092B2845f10401a0159B2B96e8B6c3D30",
                "görli": "0x6Ce570d02D73d4c384b46135E87f8C592A8c86dA",
            }

            self.factory_contract = self._load_contract(
                abi_name="uniswap-v1/factory",
                address=_str_to_addr(factory_contract_addresses[self.network]),
            )
        elif self.version == 2:
            # For v2 the address is the same on mainnet, Ropsten, Rinkeby, Görli, and Kovan
            # https://uniswap.org/docs/v2/smart-contracts/factory
            factory_contract_address_v2 = _str_to_addr(
                "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
            )
            self.factory_contract = self._load_contract(
                abi_name="uniswap-v2/factory", address=factory_contract_address_v2,
            )
            self.router_address: AddressLike = _str_to_addr(
                "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
            )
            """Documented here: https://uniswap.org/docs/v2/smart-contracts/router02/"""
            self.router = self._load_contract(
                abi_name="uniswap-v2/router02", address=self.router_address,
            )
        else:
            raise Exception("Invalid version, only 1 or 2 supported")

        logger.info(f"Using factory contract: {self.factory_contract}")

    @supports([1])
    def get_all_tokens(self) -> List[dict]:
        # FIXME: This is a very expensive operation, would benefit greatly from caching
        tokenCount = self.factory_contract.functions.tokenCount().call()
        tokens = []
        for i in range(tokenCount):
            address = self.factory_contract.functions.getTokenWithId(i).call()
            if address == "0x0000000000000000000000000000000000000000":
                # Token is ETH
                continue
            token = self.get_token(address)
            tokens.append(token)
        return tokens

    def get_pair(self, token1: AddressLike, token2: AddressLike) -> AddressLike:
        return self.factory_contract.functions.getPair(token1, token2).call()

    def get_pair_liquidity(self, address: AddressLike):
        return self._load_contract(abi_name="uniswap-v2/pair", address=address).functions.getReserves().call()

    def get_pair_token_address(self, address: AddressLike, n):
        if n == 0:
            return self._load_contract(abi_name="uniswap-v2/pair", address=address).functions.token0().call()
        else:
            return self._load_contract(abi_name="uniswap-v2/pair", address=address).functions.token1().call()

    @supports([1])
    def get_token(self, address: AddressLike) -> dict:
        # FIXME: This function should always return the same output for the same input
        #        and would therefore benefit from caching
        token_contract = self._load_contract(abi_name="erc20", address=address)
        try:
            symbol = token_contract.functions.symbol().call()
            name = token_contract.functions.name().call()
        except Exception as e:
            logger.warning(
                f"Exception occurred while trying to get token {_addr_to_str(address)}: {e}"
            )
            raise InvalidToken(address)
        return {"name": name, "symbol": symbol}

    @supports([1])
    def exchange_address_from_token(self, token_addr: AddressLike) -> AddressLike:
        ex_addr: AddressLike = self.factory_contract.functions.getExchange(
            token_addr
        ).call()
        # TODO: What happens if the token doesn't have an exchange/doesn't exist? Should probably raise an Exception (and test it)
        return ex_addr

    @supports([1])
    def token_address_from_exchange(self, exchange_addr: AddressLike) -> Address:
        token_addr: Address = (
            self.exchange_contract(ex_addr=exchange_addr)
                .functions.tokenAddress(exchange_addr)
                .call()
        )
        return token_addr

    @functools.lru_cache()
    @supports([1])
    def exchange_contract(
            self, token_addr: AddressLike = None, ex_addr: AddressLike = None
    ) -> Contract:
        if not ex_addr and token_addr:
            ex_addr = self.exchange_address_from_token(token_addr)
        if ex_addr is None:
            raise InvalidToken(token_addr)
        abi_name = "uniswap-v1/exchange"
        contract = self._load_contract(abi_name=abi_name, address=ex_addr)
        logger.info(f"Loaded exchange contract {contract} at {contract.address}")
        return contract

    @functools.lru_cache()
    def erc20_contract(self, token_addr: AddressLike) -> Contract:
        return self._load_contract(abi_name="erc20", address=token_addr)

    @functools.lru_cache()
    @supports([2])
    def get_weth_address(self) -> ChecksumAddress:
        # Contract calls should always return checksummed addresses
        address: ChecksumAddress = self.router.functions.WETH().call()
        return address

    def _load_contract(self, abi_name: str, address: AddressLike) -> Contract:
        return self.w3.eth.contract(address=address, abi=_load_abi(abi_name))

    # ------ Exchange ------------------------------------------------------------------
    @supports([1, 2])
    def get_fee_maker(self) -> float:
        """Get the maker fee."""
        return 0

    @supports([1, 2])
    def get_fee_taker(self) -> float:
        """Get the taker fee."""
        return 0.003

    # ------ Market --------------------------------------------------------------------
    @supports([1, 2])
    def get_eth_token_input_price(self, token: AddressLike, qty: Wei) -> Wei:
        """Public price for ETH to Token trades with an exact input."""
        # print(str(qty))
        price = self.router.functions.getAmountsOut(
            qty, [self.get_weth_address(), token]
        ).call()[-1]
        return price

    @supports([1, 2])
    def get_token_eth_input_price(self, token: AddressLike, qty: int) -> int:
        """Public price for token to ETH trades with an exact input."""
        price = self.router.functions.getAmountsOut(
            qty, [token, self.get_weth_address()]
        ).call()[-1]
        return price

    @supports([2])
    def get_token_token_input_price(
            self, token0: AnyAddress, token1: AnyAddress, qty: int
    ) -> int:
        """Public price for token to token trades with an exact input."""
        # If one of the tokens are WETH, delegate to appropriate call.
        # See: https://github.com/shanefontaine/uniswap-python/issues/22
        if is_same_address(token0, self.get_weth_address()):
            return int(self.get_eth_token_input_price(token1, qty))
        elif is_same_address(token1, self.get_weth_address()):
            return int(self.get_token_eth_input_price(token0, qty))

        price: int = self.router.functions.getAmountsOut(
            qty, [token0, self.get_weth_address(), token1]
        ).call()[-1]
        return price

    @supports([1, 2])
    def get_eth_token_output_price(self, token: AddressLike, qty: int) -> Wei:
        """Public price for ETH to Token trades with an exact output."""
        if self.version == 1:
            ex = self.exchange_contract(token)
            price: Wei = ex.functions.getEthToTokenOutputPrice(qty).call()
        else:
            price = self.router.functions.getAmountsIn(
                qty, [self.get_weth_address(), token]
            ).call()[0]
        return price

    @supports([1, 2])
    def get_token_eth_output_price(self, token: AddressLike, qty: Wei) -> int:
        """Public price for token to ETH trades with an exact output."""
        if self.version == 1:
            ex = self.exchange_contract(token)
            price: int = ex.functions.getTokenToEthOutputPrice(qty).call()
        else:
            price = self.router.functions.getAmountsIn(
                qty, [token, self.get_weth_address()]
            ).call()[0]
        return price

    @supports([2])
    def get_token_token_output_price(
            self, token0: AnyAddress, token1: AnyAddress, qty: int
    ) -> int:
        """Public price for token to token trades with an exact output."""
        # If one of the tokens are WETH, delegate to appropriate call.
        # See: https://github.com/shanefontaine/uniswap-python/issues/22
        # TODO: Will these equality checks always work? (Address vs ChecksumAddress vs str)
        if is_same_address(token0, self.get_weth_address()):
            return int(self.get_eth_token_output_price(token1, qty))
        elif is_same_address(token1, self.get_weth_address()):
            return int(self.get_token_eth_output_price(token0, qty))

        price: int = self.router.functions.getAmountsIn(
            qty, [token0, self.get_weth_address(), token1]
        ).call()[0]
        return price

    # ------ ERC20 Pool ----------------------------------------------------------------
    @supports([1])
    def get_ex_eth_balance(self, token: AddressLike) -> int:
        """Get the balance of ETH in an exchange contract."""
        ex_addr: AddressLike = self.exchange_address_from_token(token)
        return self.w3.eth.getBalance(ex_addr)

    @supports([1])
    def get_ex_token_balance(self, token: AddressLike) -> int:
        """Get the balance of a token in an exchange contract."""
        erc20 = self.erc20_contract(token)
        balance: int = erc20.functions.balanceOf(
            self.exchange_address_from_token(token)
        ).call()
        return balance

    # TODO: ADD TOTAL SUPPLY
    @supports([1])
    def get_exchange_rate(self, token: AddressLike) -> float:
        """Get the current ETH/token exchange rate of the token."""
        eth_reserve = self.get_ex_eth_balance(token)
        token_reserve = self.get_ex_token_balance(token)
        return float(token_reserve / eth_reserve)

    # ------ Tx Utils ------------------------------------------------------------------
    def _deadline(self) -> int:
        """Get a predefined deadline. 10min by default (same as the Uniswap SDK)."""
        return int(time.time()) + 10 * 60

    # ------ Price Calculation Utils ---------------------------------------------------
    def _calculate_max_input_token(
            self, input_token: AddressLike, qty: int, output_token: AddressLike
    ) -> Tuple[int, int]:
        """
        For buy orders (exact output), the cost (input) is calculated.
        Calculate the max input and max eth sold for a token to token output swap.
        Equation from:
         - https://hackmd.io/hthz9hXKQmSyXfMbPsut1g
         - https://uniswap.org/docs/v1/frontend-integration/trade-tokens/
        """
        # Buy TokenB with ETH
        output_amount_b = qty
        input_reserve_b = self.get_ex_eth_balance(output_token)
        output_reserve_b = self.get_ex_token_balance(output_token)

        # Cost
        numerator_b = output_amount_b * input_reserve_b * 1000
        denominator_b = (output_reserve_b - output_amount_b) * 997
        input_amount_b = numerator_b / denominator_b + 1

        # Buy ETH with TokenA
        output_amount_a = input_amount_b
        input_reserve_a = self.get_ex_token_balance(input_token)
        output_reserve_a = self.get_ex_eth_balance(input_token)

        # Cost
        numerator_a = output_amount_a * input_reserve_a * 1000
        denominator_a = (output_reserve_a - output_amount_a) * 997
        input_amount_a = numerator_a / denominator_a - 1

        return int(input_amount_a), int(1.2 * input_amount_b)

    def _calculate_max_output_token(
            self, output_token: AddressLike, qty: int, input_token: AddressLike
    ) -> Tuple[int, int]:
        """
        For sell orders (exact input), the amount bought (output) is calculated.
        Similar to _calculate_max_input_token, but for an exact input swap.
        """
        # TokenA (ERC20) to ETH conversion
        inputAmountA = qty
        inputReserveA = self.get_ex_token_balance(input_token)
        outputReserveA = self.get_ex_eth_balance(input_token)

        # Cost
        numeratorA = inputAmountA * outputReserveA * 997
        denominatorA = inputReserveA * 1000 + inputAmountA * 997
        outputAmountA = numeratorA / denominatorA

        # ETH to TokenB conversion
        inputAmountB = outputAmountA
        inputReserveB = self.get_ex_token_balance(output_token)
        outputReserveB = self.get_ex_eth_balance(output_token)

        # Cost
        numeratorB = inputAmountB * outputReserveB * 997
        denominatorB = inputReserveB * 1000 + inputAmountB * 997
        outputAmountB = numeratorB / denominatorB

        return int(outputAmountB), int(1.2 * outputAmountA)

    # ------ Test utilities ------------------------------------------------------------

    def _buy_test_assets(self) -> None:
        """
        Buys some BAT and DAI.
        Used in testing.
        """
        ONE_ETH = 1 * 10 ** 18
        TEST_AMT = int(0.1 * ONE_ETH)
        tokens = self._get_token_addresses()

        for token_name in ["BAT", "DAI"]:
            token_addr = tokens[token_name.lower()]
            price = self.get_eth_token_output_price(_str_to_addr(token_addr), TEST_AMT)
            logger.info(f"Cost of {TEST_AMT} {token_name}: {price}")
            logger.info("Buying...")
            tx = self.make_trade_output(
                tokens["eth"], tokens[token_name.lower()], TEST_AMT
            )
            self.w3.eth.waitForTransactionReceipt(tx)

    def _get_token_addresses(self) -> Dict[str, str]:
        """
        Returns a dict with addresses for tokens for the current net.
        Used in testing.
        """
        netid = int(self.w3.net.version)
        netname = _netid_to_name[netid]
        if netname == "mainnet":
            return {
                "eth": "0x0000000000000000000000000000000000000000",
                "bat": Web3.toChecksumAddress(
                    "0x0D8775F648430679A709E98d2b0Cb6250d2887EF"
                ),
                "dai": Web3.toChecksumAddress(
                    "0x6b175474e89094c44da98b954eedeac495271d0f"
                ),
            }
        elif netname == "rinkeby":
            return {
                "eth": "0x0000000000000000000000000000000000000000",
                "bat": "0xDA5B056Cfb861282B4b59d29c9B395bcC238D29B",
                "dai": "0x2448eE2641d78CC42D7AD76498917359D961A783",
            }
        else:
            raise Exception(f"Unknown net '{netname}'")
