import locale
import sys
import os

BASE_PATH = os.environ.get('BASE_PATH')
sys.path.insert(1, BASE_PATH + '/telegram-bots/src')

from graphqlclient import GraphQLClient
import time
from datetime import datetime
import pprint
import os.path
import re

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

import libraries.general_end_functions as general_end_functions
import libraries.commands_util as commands_util

# ENV FILES

# log_file
charts_path = BASE_PATH + 'log_files/chart_bot/'

locale.setlocale(locale.LC_ALL, 'en_US')

graphql_client_uni = GraphQLClient('https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2')
graphql_client_eth = GraphQLClient('https://api.thegraph.com/subgraphs/name/blocklytics/ethereum-blocks')

## TO CHANGE
TELEGRAM_KEY = os.environ.get('SKPL_TELEGRAM_KEY')
contract = "0xc6e2573029e91ea391dee58b2cd348133b944137"
name = "SPOOK"
pair_contract = "0x0441bdc819a8a92e1ec8aac644a33655d8f74c59"
ticker = 'SKPL'
decimals = 1000000000000000000  # that's 18


def get_candlestick(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    query_received = update.message.text.split(' ')

    time_type, k_hours, k_days, tokens = commands_util.check_query(query_received, ticker)
    t_to = int(time.time())
    t_from = t_to - (k_days * 3600 * 24) - (k_hours * 3600)

    if isinstance(tokens, list):
        for token in tokens:
            general_end_functions.send_candlestick_pyplot(context, token, charts_path, k_days, k_hours, t_from, t_to, chat_id)
    else:
        general_end_functions.send_candlestick_pyplot(context, tokens, charts_path, k_days, k_hours, t_from, t_to, chat_id)


def get_price_token(update: Update, context: CallbackContext):
    general_end_functions.get_price(update, context, contract, pair_contract, graphql_client_eth, graphql_client_uni, name, decimals)


def main():
    updater = Updater(TELEGRAM_KEY, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('chart', get_candlestick))
    dp.add_handler(CommandHandler('price', get_price_token))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

commands = """
chart - Display a chart of the price.
price - Get the current price.
"""
