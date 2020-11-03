import locale
import sys
import os

from twython import Twython

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
import libraries.requests_util as requests_util
import libraries.util as util
import libraries.scrap_websites_util as scrap_websites_util
from libraries.common_values import *

# twitter
APP_KEY = os.environ.get('TWITTER_API_KEY')
APP_SECRET = os.environ.get('TWITTER_API_KEY_SECRET')
ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
ACCESS_SECRET_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
twitter = Twython(APP_KEY, APP_SECRET, ACCESS_TOKEN, ACCESS_SECRET_TOKEN)

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


# button refresh: h:int-d:int-t:token
def get_candlestick(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    query_received = update.message.text.split(' ')

    time_type, k_hours, k_days, tokens = commands_util.check_query(query_received, default_token)
    t_to = int(time.time())
    t_from = t_to - (k_days * 3600 * 24) - (k_hours * 3600)

    if isinstance(tokens, list):
        for token in tokens:
            (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(token, charts_path, k_days, k_hours, t_from, t_to)
            context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html", reply_markup=reply_markup_chart)
    else:
        (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(tokens, charts_path, k_days, k_hours, t_from, t_to)
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
        (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(token, charts_path, k_days, k_hours, t_from, t_to)
        context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html", reply_markup=reply_markup_chart)


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
    if msgs == "" or msgs is None or msgs == []:
        msgs = "No favorites for the moment. Add some with /add_fav"
    else:
        msgs = ', '.join(msgs)
    context.bot.send_message(chat_id=chat_id, text=msgs)


def get_price_token(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    query_received = update.message.text.split(' ')
    if len(query_received) == 2:
        ticker = query_received[1]
        contract_from_ticker = requests_util.get_token_contract_address(ticker)
        pprint.pprint(contract_from_ticker)
        if contract_from_ticker is None:
            context.bot.send_message(chat_id=chat_id, text='Contract address for ticker ' + ticker + ' not found.')
        else:
            button_list_price = [[InlineKeyboardButton('refresh', callback_data='r_p_' + contract_from_ticker + "_t_" + ticker)]]
            reply_markup_price = InlineKeyboardMarkup(button_list_price)
            message = general_end_functions.get_price(contract_from_ticker, pair_contract, graphql_client_eth, graphql_client_uni, ticker.upper(), decimals)
            context.bot.send_message(chat_id=chat_id, text=message, parse_mode='html', reply_markup=reply_markup_price, disable_web_page_preview=True)
    else:
        context.bot.send_message(chat_id=chat_id, text='Please specify the ticker of the desired token.')


def refresh_price(update: Update, context: CallbackContext):
    print("refreshing price")
    query = update.callback_query.data
    contract_from_ticker = query.split('r_p_')[1].split('_t')[0]
    token_name = query.split('_t_')[1]
    message = general_end_functions.get_price(contract_from_ticker, pair_contract, graphql_client_eth, graphql_client_uni,
                                              token_name.upper(), decimals)
    button_list_price = [[InlineKeyboardButton('refresh', callback_data='refresh_price_' + contract_from_ticker)]]
    reply_markup_price = InlineKeyboardMarkup(button_list_price)
    update.callback_query.edit_message_text(text=message, parse_mode='html', reply_markup=reply_markup_price, disable_web_page_preview=True)


def delete_message(update: Update, context: CallbackContext):
    print("deleting chart")
    chat_id = update.callback_query.message.chat_id
    message_id = update.callback_query.message.message_id
    context.bot.delete_message(chat_id=chat_id, message_id=message_id)


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


def refresh_chart(update: Update, context: CallbackContext):
    print("refreshing chart")
    query = update.callback_query.data

    k_hours = int(re.search(r'\d+', query.split('h:')[1]).group())
    k_days = int(re.search(r'\d+', query.split('d:')[1]).group())
    token = query.split('t:')[1]

    t_to = int(time.time())
    t_from = t_to - (k_days * 3600 * 24) - (k_hours * 3600)

    chat_id = update.callback_query.message.chat_id
    message_id = update.callback_query.message.message_id

    (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(token, charts_path, k_days, k_hours, t_from, t_to)
    context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html", reply_markup=reply_markup_chart)
    context.bot.delete_message(chat_id=chat_id, message_id=message_id)


# sends the current biz threads
def get_biz(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    query_received = update.message.text.split(' ')
    if len(query_received) == 2:
        word = query_received[-1]
        word_regex_friendly = word.replace('$', '\\$')
        threads_ids = scrap_websites_util.get_biz_threads(re.compile(word_regex_friendly))

        base_url = "boards.4channel.org/biz/thread/"
        message = """Plz go bump the /biz/ threads:
"""
        for thread_id in threads_ids:
            excerpt = thread_id[2] + " | " + thread_id[1]
            message += base_url + str(thread_id[0]) + " -- " + excerpt[0: 100] + "[...] \n"
        if not threads_ids:
            meme_caption = "No current /biz/ thread containing the word $WORD. Go make one https://boards.4channel.org/biz/.".replace("$WORD", word)
            context.bot.send_message(chat_id=chat_id, text=meme_caption, disable_web_page_preview=True)
        else:
            context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True)
    else:
        context.bot.send_message(chat_id=chat_id,
                                 text='Please use the format /biz WORD')


def get_twitter(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    query_received = update.message.text.split(' ')
    if len(query_received) == 2:
        ticker = query_received[-1]
        res = scrap_websites_util.get_last_tweets(twitter, ticker)
        context.bot.send_message(chat_id=chat_id, text=res, parse_mode='html', disable_web_page_preview=True)
    else:
        context.bot.send_message(chat_id=chat_id, text="Please use the format /twitter TOKEN_TICKER.", parse_mode='html', disable_web_page_preview=True)


def do_convert(update: Update, context: CallbackContext):
    query_received = update.message.text.split(' ')
    chat_id = update.message.chat_id
    message = general_end_functions.convert_to_something(query_received, graphql_client_uni, graphql_client_eth)
    context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True, parse_mode='html')


def main():
    updater = Updater(TELEGRAM_KEY, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('charts', get_candlestick))
    dp.add_handler(CommandHandler('chart', get_candlestick))
    dp.add_handler(CommandHandler('c', get_candlestick))
    dp.add_handler(CommandHandler('add_fav', add_favorite_token))
    dp.add_handler(CommandHandler('see_fav', see_fav_token))
    dp.add_handler(CommandHandler('remove_fav', delete_fav_token))
    dp.add_handler(CommandHandler('charts_fav', see_fav_charts))
    dp.add_handler(CommandHandler('price', get_price_token))
    dp.add_handler(CommandHandler('p', get_price_token))
    dp.add_handler(CommandHandler('twitter', get_twitter))
    dp.add_handler(CommandHandler('biz', get_biz))
    dp.add_handler(CommandHandler('convert', do_convert))
    dp.add_handler(CallbackQueryHandler(refresh_chart, pattern='refresh_chart(.*)'))
    dp.add_handler(CallbackQueryHandler(refresh_price, pattern='r_p_(.*)'))
    dp.add_handler(CallbackQueryHandler(delete_message, pattern='delete_message'))
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
price - get price of a token
"""
