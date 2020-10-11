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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler

import libraries.graphs_util as graphs_util
import libraries.general_end_functions as general_end_functions
import libraries.commands_util as commands_util
import libraries.util as util

# ENV FILES
TELEGRAM_KEY = os.environ.get('CHART_TELEGRAM_KEY')
contract = "0xd04785c4d8195e4a54d9dec3a9043872875ae9e2"
name = "ROT"
pair_contract = "0x5a265315520696299fa1ece0701c3a1ba961b888"
decimals = 1000000000000000000  # that's 18

# log_file
charts_path = BASE_PATH + 'log_files/chart_bot/'

default_token = 'ROT'

locale.setlocale(locale.LC_ALL, 'en_US')

graphql_client_uni = GraphQLClient('https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2')
graphql_client_eth = GraphQLClient('https://api.thegraph.com/subgraphs/name/blocklytics/ethereum-blocks')

button_list_price = [[InlineKeyboardButton('refresh', callback_data='refresh_price')]]
reply_markup_price = InlineKeyboardMarkup(button_list_price)


def read_favorites(path):
    with open(path) as f:
        msgs = [line.rstrip() for line in f]
    return msgs


def create_file_if_not_existing(path):
    if not os.path.isfile(path):
        f = open(path, "x")
        f.close()


def strp_date(raw_date):
    return datetime.strptime(raw_date, '%m/%d/%Y,%H:%M:%S')


def delete_line_from_file(path, msg):
    with open(path, "r") as f:
        # read data line by line
        data = f.readlines()
    # open file in write mode
    with open(path, "w") as f:
        for line in data:
            # condition for data to be deleted
            if line.strip("\n") != msg:
                f.write(line)


def check_query_fav(query_received):
    time_type, k_hours, k_days = 'd', 0, 1
    if len(query_received) == 1:
        pass
    elif len(query_received) == 2:
        pass
    else:
        time_type, k_hours, k_days = commands_util.get_from_query(query_received)
    return time_type, k_hours, k_days


def refresh_chart(update: Update, context: CallbackContext):
    pprint.pprint(update.message)
    pprint.pprint(update.callback_query.message)
    # chat_id = update.message.chat_id
    #
    # query_received = update.message.text.split(' ')
    #
    # time_type, k_hours, k_days, tokens = commands_util.check_query(query_received, default_token)
    # t_to = int(time.time())
    # t_from = t_to - (k_days * 3600 * 24) - (k_hours * 3600)
    #
    # if isinstance(tokens, list):
    #     for token in tokens:
    #         (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(context, token, charts_path, k_days, k_hours, t_from, t_to, chat_id)
    #         context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html")
    # else:
    #     (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(context, tokens, charts_path, k_days, k_hours, t_from, t_to, chat_id)
    #     context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html", reply_markup=reply_markup_chart)


# button refresh: h:int-d:int-token
def get_candlestick(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    query_received = update.message.text.split(' ')

    time_type, k_hours, k_days, tokens = commands_util.check_query(query_received, default_token)
    t_to = int(time.time())
    t_from = t_to - (k_days * 3600 * 24) - (k_hours * 3600)

    if isinstance(tokens, list):
        for token in tokens:
            (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(context, token, charts_path, k_days, k_hours, t_from, t_to, chat_id)
            context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html")
    else:
        (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(context, tokens, charts_path, k_days, k_hours, t_from, t_to, chat_id)
        context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html", reply_markup=reply_markup_chart)


def see_fav_charts(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    query_received = update.message.text.split(' ')

    time_type, k_hours, k_days = check_query_fav(query_received)
    username = update.message.from_user.username
    favorite_path = charts_path + username + '.txt'
    create_file_if_not_existing(favorite_path)
    tokens = read_favorites(favorite_path)
    t_to = int(time.time())
    t_from = t_to - (k_days * 3600 * 24) - (k_hours * 3600)

    for token in tokens:
        general_end_functions.send_candlestick_pyplot(context, token, charts_path, k_days, k_hours, t_from, t_to,
                                                      chat_id)


def delete_fav_token(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    username = update.message.from_user.username
    favorite_path = charts_path + username + '.txt'
    create_file_if_not_existing(favorite_path)
    msgs = read_favorites(favorite_path)
    to_delete = update.message.text.split(' ')[1]
    if to_delete not in msgs:
        context.bot.send_message(chat_id=chat_id, text=to_delete + " not in your favorites")
    else:
        delete_line_from_file(favorite_path, to_delete)
        context.bot.send_message(chat_id=chat_id, text="Removed " + to_delete + " from your favorites")


def see_fav_token(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    username = update.message.from_user.username
    favorite_path = charts_path + username + '.txt'
    create_file_if_not_existing(favorite_path)
    msgs = read_favorites(favorite_path)
    pprint.pprint(msgs)
    if msgs == "" or msgs is None or msgs == []:
        msgs = "No favorites for the moment. Add some with /add_fav"
    else:
        msgs = ', '.join(msgs)
    context.bot.send_message(chat_id=chat_id, text=msgs)


def get_price_token(update: Update, context: CallbackContext):
    message = general_end_functions.get_price(contract, pair_contract, graphql_client_eth, graphql_client_uni, name, decimals)
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=message, parse_mode='html', reply_markup=reply_markup_price)


def refresh_price(update: Update, context: CallbackContext):
    message = general_end_functions.get_price(contract, pair_contract, graphql_client_eth, graphql_client_uni,
                                              name, decimals)
    update.callback_query.edit_message_text(text=message, parse_mode='html', reply_markup=reply_markup_price)


def add_favorite_token(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    username = update.message.from_user.username
    favorite_path = charts_path + username + '.txt'
    create_file_if_not_existing(favorite_path)
    msgs = read_favorites(favorite_path)
    query_received = update.message.text.split(' ')

    if not len(query_received) == 2:
        context.bot.send_message(chat_id=chat_id, text="Error. Can only add one symbol at a time")
    else:
        symbol_to_add = query_received[1]
        if symbol_to_add in msgs:
            context.bot.send_message(chat_id=chat_id,
                                     text="Error. Looks like the symbol " + symbol_to_add + " is already in your favorites.")
        else:
            with open(favorite_path, "a") as fav_file:
                message_to_write = symbol_to_add + "\n"
                fav_file.write(message_to_write)
            context.bot.send_message(chat_id=chat_id, text="Added " + symbol_to_add + " to your favorites.")


def main():
    updater = Updater(TELEGRAM_KEY, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('charts', get_candlestick))
    dp.add_handler(CommandHandler('add_fav', add_favorite_token))
    dp.add_handler(CommandHandler('see_fav', see_fav_token))
    dp.add_handler(CommandHandler('remove_fav', delete_fav_token))
    dp.add_handler(CommandHandler('charts_fav', see_fav_charts))
    dp.add_handler(CommandHandler('price', get_price_token))
    dp.add_handler(CallbackQueryHandler(refresh_price, 'refresh_price'))
    dp.add_handler(CallbackQueryHandler(refresh_chart, 'refresh_chart(.*)'))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

commands = """
charts - Display some charts.
charts_fav - Display your favorite charts
add_fav - Add a favorite token.
see_fav - See your favorites tokens.
remove_fav - Remove a token from your favorites.
prive - get price of a token
"""
