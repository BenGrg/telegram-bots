import locale
import sys
import os
from gevent import monkey
monkey.patch_all()  # REALLY IMPORTANT: ALLOWS ZERORPC AND TG TO WORK TOGETHER

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
from telegram.ext.dispatcher import run_async

import libraries.graphs_util as graphs_util
import libraries.general_end_functions as general_end_functions
import libraries.commands_util as commands_util
import libraries.requests_util as requests_util
import libraries.time_util as time_util
import libraries.util as util
import libraries.scrap_websites_util as scrap_websites_util
from libraries.uniswap import Uniswap
from libraries.common_values import *
from web3 import Web3
import zerorpc
import random


# ZERORPC
zerorpc_client_data_aggregator = zerorpc.Client()
zerorpc_client_data_aggregator.connect("tcp://127.0.0.1:4243")  # TODO: change port to env variable
pprint.pprint(zerorpc_client_data_aggregator.hello("coucou"))

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

# web3
infura_url = os.environ.get('INFURA_URL')
pprint.pprint(infura_url)
w3 = Web3(Web3.HTTPProvider(infura_url))

# web3 uni wrapper
uni_wrapper = Uniswap(web3=w3)

# log_file
charts_path = BASE_PATH + 'log_files/chart_bot/'

default_token = 'ROT'

locale.setlocale(locale.LC_ALL, 'en_US')

graphql_client_uni = GraphQLClient('https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2')
graphql_client_eth = GraphQLClient('https://api.thegraph.com/subgraphs/name/blocklytics/ethereum-blocks')

rejection_no_default_ticker_message = "No default token found for this chat. Please ask an admin to add one with /set_default_token <TICKER>"


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
@run_async
def get_candlestick(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    query_received = update.message.text.split(' ')
    default_default_token = default_token
    if len(query_received) == 1:
        channel_token = __get_default_token_channel(chat_id)
        if channel_token is not None:
            default_default_token = channel_token
        else:
            context.bot.send_message(chat_id=chat_id, text=rejection_no_default_ticker_message)
            pass

    time_type, k_hours, k_days, tokens = commands_util.check_query(query_received, default_default_token)
    t_to = int(time.time())
    t_from = t_to - (k_days * 3600 * 24) - (k_hours * 3600)
    trending = zerorpc_client_data_aggregator.view_trending_simple()

    if isinstance(tokens, list):
        for token in tokens:
            (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(token, charts_path,
                                                                                                k_days, k_hours, t_from,
                                                                                                t_to, txt=trending)
            util.create_and_send_vote(token, "chart", update.message.from_user.name, zerorpc_client_data_aggregator)
            context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html",
                                   reply_markup=reply_markup_chart)
    else:
        (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(tokens, charts_path, k_days,
                                                                                            k_hours, t_from,
                                                                                            t_to, txt=trending)
        util.create_and_send_vote(tokens, "chart", update.message.from_user.name, zerorpc_client_data_aggregator)
        context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html",
                               reply_markup=reply_markup_chart)


@run_async
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
            util.create_and_send_vote(ticker, "price", update.message.from_user.name, zerorpc_client_data_aggregator)
            button_list_price = [
                [InlineKeyboardButton('refresh', callback_data='r_p_' + contract_from_ticker + "_t_" + ticker)]]
            reply_markup_price = InlineKeyboardMarkup(button_list_price)
            message = general_end_functions.get_price(contract_from_ticker, pair_contract, graphql_client_eth,
                                                      graphql_client_uni, ticker.upper(), decimals)
            context.bot.send_message(chat_id=chat_id, text=message, parse_mode='html', reply_markup=reply_markup_price,
                                     disable_web_page_preview=True)
    elif len(query_received) == 1:  # TODO: merge all those duplicate things
        ticker = __get_default_token_channel(chat_id)
        if ticker is not None:
            contract_from_ticker = requests_util.get_token_contract_address(ticker)
            pprint.pprint(contract_from_ticker)
            if contract_from_ticker is None:
                context.bot.send_message(chat_id=chat_id, text='Contract address for ticker ' + ticker + ' not found.')
            else:
                util.create_and_send_vote(ticker, "price", update.message.from_user.name, zerorpc_client_data_aggregator)
                button_list_price = [
                    [InlineKeyboardButton('refresh', callback_data='r_p_' + contract_from_ticker + "_t_" + ticker)]]
                reply_markup_price = InlineKeyboardMarkup(button_list_price)
                message = general_end_functions.get_price(contract_from_ticker, pair_contract, graphql_client_eth,
                                                          graphql_client_uni, ticker.upper(), decimals)
                context.bot.send_message(chat_id=chat_id, text=message, parse_mode='html', reply_markup=reply_markup_price,
                                         disable_web_page_preview=True)
        else:
            message = rejection_no_default_ticker_message
            context.bot.send_message(chat_id=chat_id, text=message, parse_mode='html')
    else:
        context.bot.send_message(chat_id=chat_id, text='Please specify the ticker of the desired token.')


def refresh_price(update: Update, context: CallbackContext):
    print("refreshing price")
    query = update.callback_query.data
    contract_from_ticker = query.split('r_p_')[1].split('_t')[0]
    token_name = query.split('_t_')[1]
    message = general_end_functions.get_price(contract_from_ticker, pair_contract, graphql_client_eth,
                                              graphql_client_uni,
                                              token_name.upper(), decimals)
    button_list_price = [[InlineKeyboardButton('refresh', callback_data='refresh_price_' + contract_from_ticker)]]
    reply_markup_price = InlineKeyboardMarkup(button_list_price)
    update.callback_query.edit_message_text(text=message, parse_mode='html', reply_markup=reply_markup_price,
                                            disable_web_page_preview=True)


def delete_message(update: Update, context: CallbackContext):
    print("deleting chart")
    chat_id = update.callback_query.message.chat_id
    message_id = update.callback_query.message.message_id
    context.bot.delete_message(chat_id=chat_id, message_id=message_id)


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

    banner_txt = util.get_banner_txt(zerorpc_client_data_aggregator)

    (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(token, charts_path, k_days,
                                                                                        k_hours, t_from, t_to,
                                                                                        txt=banner_txt)
    context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html",
                           reply_markup=reply_markup_chart)
    context.bot.delete_message(chat_id=chat_id, message_id=message_id)


# sends the current biz threads
@run_async
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
            meme_caption = "No current /biz/ thread containing the word $WORD. Go make one https://boards.4channel.org/biz/.".replace(
                "$WORD", word)
            context.bot.send_message(chat_id=chat_id, text=meme_caption, disable_web_page_preview=True)
        else:
            context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True)
    else:
        context.bot.send_message(chat_id=chat_id,
                                 text='Please use the format /biz WORD')


@run_async
def get_twitter(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    query_received = update.message.text.split(' ')
    if len(query_received) == 2:
        ticker = query_received[-1]
        res = scrap_websites_util.get_last_tweets(twitter, ticker)
        context.bot.send_message(chat_id=chat_id, text=res, parse_mode='html', disable_web_page_preview=True)
    else:
        context.bot.send_message(chat_id=chat_id, text="Please use the format /twitter TOKEN_TICKER.",
                                 parse_mode='html', disable_web_page_preview=True)


def do_convert(update: Update, context: CallbackContext):
    query_received = update.message.text.split(' ')
    chat_id = update.message.chat_id
    message = general_end_functions.convert_to_something(query_received, graphql_client_uni, graphql_client_eth)
    context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True, parse_mode='html')


@run_async
def balance_token_in_wallet(update: Update, context: CallbackContext):
    query_received = update.message.text.split(' ')
    chat_id = update.message.chat_id
    if len(query_received) == 3:
        wallet = query_received[1]
        ticker = query_received[2]
        amount, amount_usd = general_end_functions.get_balance_token_wallet(w3, wallet, ticker, graphql_client_uni,
                                                                            graphql_client_eth)
        message = "wallet " + str(wallet) + " contains " + str(amount) + " " + ticker + " = " + str(
            amount_usd) + " usd."
        context.bot.send_message(chat_id=chat_id, text=message)
        # res = con
    elif len(query_received) == 2 and query_received[1] == "jackpot":
        wallet = "0x9284b7fb2c842666dae4e87ddb49106b72820d26"
        ticker = "LUCKY"
        amount, amount_usd = general_end_functions.get_balance_token_wallet(w3, wallet, ticker, graphql_client_uni,
                                                                            graphql_client_eth)
        message = "<b>🍀 Lucky Daily Jackpot Balance</b>," + str(amount) + " " + ticker + " = <b>" + str(
            amount_usd) + " usd</b>."
        context.bot.send_message(chat_id=chat_id, text=message, parse_mode="html")
    else:
        context.bot.send_message(chat_id=chat_id, text="Wrong arguments. Please use /balance WALLET TOKEN")


@run_async
def get_gas_average(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    asap, fast, average, low = general_end_functions.get_gas_price()
    message = "<b>Gas price:</b><code>" + \
              "\nASAP: " + str(asap) + \
              "\nFast: " + str(fast) + \
              "\nAvg : " + str(average) + \
              "\nSlow: " + str(low) + "</code>"
    context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True, parse_mode='html')


@run_async
def get_time_to(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    query_received = update.message.text[7:]
    if query_received == "jackpot" or query_received == " jackpot":
        query_received = "7 pm CST"
    pprint.pprint(query_received)

    higher, time_to = time_util.get_time_diff(query_received)
    pprint.pprint(time_to)
    word = ' is ' if higher else ' was '
    message = str(query_received) + word + str(time_to) + " from now."
    context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True)


@run_async
def get_latest_actions(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    query_received = update.message.text.split(' ')
    if len(query_received) == 1:
        token_ticker = __get_default_token_channel(chat_id)
        if token_ticker is not None:
            latest_actions_pretty = general_end_functions.get_last_actions_token_in_eth_pair(token_ticker, uni_wrapper, graphql_client_uni)
            util.create_and_send_vote(token_ticker, "actions", update.message.from_user.name, zerorpc_client_data_aggregator)
            context.bot.send_message(chat_id=chat_id, text=latest_actions_pretty, disable_web_page_preview=True, parse_mode='html')
        else:
            context.bot.send_message(chat_id=chat_id, text=rejection_no_default_ticker_message)
    elif len(query_received) == 2:
        token_ticker = query_received[1]
        latest_actions_pretty = general_end_functions.get_last_actions_token_in_eth_pair(token_ticker, uni_wrapper, graphql_client_uni)
        util.create_and_send_vote(token_ticker, "actions", update.message.from_user.name, zerorpc_client_data_aggregator)
        context.bot.send_message(chat_id=chat_id, text=latest_actions_pretty, disable_web_page_preview=True, parse_mode='html')
    else:
        context.bot.send_message(chat_id=chat_id, text="Please use the format /last_actions TOKEN_TICKER")


@run_async
def get_trending(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    res = zerorpc_client_data_aggregator.view_trending()
    context.bot.send_message(chat_id=chat_id, text=res)


@run_async
def get_gas_spent(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    query_received = update.message.text.split(' ')
    if len(query_received) == 2:
        addr = query_received[1].lower()
        res = general_end_functions.get_gas_spent(addr)
        context.bot.send_message(chat_id=chat_id, text=res)
    else:
        context.bot.send_message(chat_id=chat_id, text="Please use the format /gas_spent address (ex: /gas_spent 0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8)")


# ADMIN STUFF
def set_default_token(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    query_received = update.message.text.split(' ')
    if __is_user_admin(context, update):
        if len(query_received) == 2:
            ticker = query_received[1].upper()
            pprint.pprint("setting default channel " + str(chat_id) + " - " + str(ticker))
            res = zerorpc_client_data_aggregator.set_default_token(chat_id, ticker)
            context.bot.send_message(chat_id=chat_id, text=res)
        else:
            context.bot.send_message(chat_id=chat_id, text="Please use the format /set_default_token TICKER")
    else:
        context.bot.send_message(chat_id=chat_id, text="Only an admin can do that you silly.")


def get_default_token(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    res = __get_default_token_channel(chat_id)
    context.bot.send_message(chat_id=chat_id, text=res)


def __get_default_token_channel(channel_id: int):
    res = zerorpc_client_data_aggregator.get_default_token(channel_id)
    pprint.pprint("Default token channel " + str(channel_id) + " is " + str(res))
    return res


def __is_user_admin(context, update):
    status = context.bot.get_chat_member(update.effective_chat.id, update.message.from_user.id).status
    pprint.pprint(status)
    return status == 'administrator' or status == 'creator'


def main():
    updater = Updater(TELEGRAM_KEY, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('charts', get_candlestick))
    dp.add_handler(CommandHandler('chart', get_candlestick))
    dp.add_handler(CommandHandler('c', get_candlestick))
    dp.add_handler(CommandHandler('price', get_price_token))
    dp.add_handler(CommandHandler('p', get_price_token))
    dp.add_handler(CommandHandler('gas', get_gas_average))
    dp.add_handler(CommandHandler('twitter', get_twitter))
    dp.add_handler(CommandHandler('biz', get_biz))
    dp.add_handler(CommandHandler('convert', do_convert))
    dp.add_handler(CommandHandler('gas', get_gas_average))
    dp.add_handler(CommandHandler('balance', balance_token_in_wallet))
    dp.add_handler(CommandHandler('timeto', get_time_to))
    dp.add_handler(CommandHandler('last_actions', get_latest_actions))
    dp.add_handler(CommandHandler('trending', get_trending))
    dp.add_handler(CommandHandler('gas_spent', get_gas_spent))
    dp.add_handler(CommandHandler('set_default_token', set_default_token))
    dp.add_handler(CommandHandler('get_default_token', get_default_token))
    dp.add_handler(CallbackQueryHandler(refresh_chart, pattern='refresh_chart(.*)'))
    dp.add_handler(CallbackQueryHandler(refresh_price, pattern='r_p_(.*)'))
    dp.add_handler(CallbackQueryHandler(delete_message, pattern='delete_message'))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

commands = """
chart - <TICKER> Display charts of the TICKER.
twitter - <TICKER> Get latests twitter containing $<TICKER> 
price - <TICKER> get price of the <TICKER> token
biz - <WORD> get 4chan/biz threads containing <WORD>
gas - Get gas price.
convert - <AMOUNT> <TICKER> option(<TICKER>) convert amount of ticker to usd (and to the second ticker if specified) 
balance - <WALLET> <TICKER> check how much an address has of a specific coin
timeto - time until date passed as argument
last_actions - <TICKER> get the last trades / liq events of the coin
trending - See which coins are trending in dextrends
"""
