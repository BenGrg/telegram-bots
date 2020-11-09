import locale
import sys
import os


BASE_PATH = os.environ.get('BASE_PATH')
sys.path.insert(1, BASE_PATH + '/telegram-bots/src')

from twython import Twython
from graphqlclient import GraphQLClient
import time
from datetime import datetime
import pprint
import os.path
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
import telegram.error
import libraries.graphs_util as graphs_util
import libraries.general_end_functions as general_end_functions
import libraries.commands_util as commands_util
import libraries.scrap_websites_util as scrap_websites_util
import libraries.git_util as git_util
import libraries.requests_util as requests_util
import libraries.util as util
from bots.boo_bank.bot_boo_values import links, test_error_token, how_to_swap
from libraries.timer_util import RepeatedTimer
from libraries.uniswap import Uniswap
from libraries.common_values import *
from web3 import Web3

button_list_price = [[InlineKeyboardButton('refresh', callback_data='refresh_price')]]
reply_markup_price = InlineKeyboardMarkup(button_list_price)

APP_KEY = os.environ.get('TWITTER_API_KEY')
APP_SECRET = os.environ.get('TWITTER_API_KEY_SECRET')
ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
ACCESS_SECRET_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')

TMP_FOLDER = BASE_PATH + 'tmp/'
MEME_GIT_REPO = os.environ.get('BLOODY_MEME_GIT_REPO')
git_url = "https://api.github.com/repos/rottedben/bloodyMemes/contents/memesFolder"
git_handler = git_util.MemeHandler(MEME_GIT_REPO, git_url)

twitter = Twython(APP_KEY, APP_SECRET, ACCESS_TOKEN, ACCESS_SECRET_TOKEN)



# web3
infura_url = os.environ.get('INFURA_URL')
pprint.pprint(infura_url)
w3 = Web3(Web3.HTTPProvider(infura_url))
uni_wrapper = Uniswap(web3=w3)

# time
last_time_checked_4chan = 0
last_time_checked_twitter = 0

# log_file
charts_path = BASE_PATH + 'log_files/chart_bot/'

locale.setlocale(locale.LC_ALL, 'en_US')

graphql_client_uni = GraphQLClient('https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2')
graphql_client_eth = GraphQLClient('https://api.thegraph.com/subgraphs/name/blocklytics/ethereum-blocks')

re_4chan = re.compile(r'\$BLOODY|BLOODY')
TELEGRAM_KEY = os.environ.get('BLOODY_TELEGRAM_KEY')
bloody_contract = "0x892f5a0b08bb7b1eecccc63ef3916ff201c93664"
name = "BloodyToken"
ticker = 'BLOODY'
pair_contract = "0xc01E75AFbEdD5F9B9B8BCC619852D839B182cD38"
decimals = 1000000000000000000  # that's 18

# add meme

supply_file_path = BASE_PATH + 'log_files/bloody_bot/supply_log.txt'
supply_chart_path = BASE_PATH + 'log_files/bloody_bot/supply_chart.png'

lambo_price_usd = 220000


# button refresh: h:int-d:int-t:token
def get_candlestick(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    query_received = update.message.text.split(' ')

    time_type, k_hours, k_days, tokens = commands_util.check_query(query_received, ticker)
    t_to = int(time.time())
    t_from = t_to - (k_days * 3600 * 24) - (k_hours * 3600)

    if isinstance(tokens, list):
        for token in tokens:
            (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(token, charts_path, k_days, k_hours, t_from, t_to)
            context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html", reply_markup=reply_markup_chart)
    else:
        (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(tokens, charts_path, k_days, k_hours, t_from, t_to)
        context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html", reply_markup=reply_markup_chart)


def special_custom_price():
    (derivedETH_7d, token_price_7d_usd, derivedETH_1d, token_price_1d_usd, derivedETH_now,
     token_price_now_usd) = requests_util.get_price_raw(graphql_client_eth, graphql_client_uni, bloody_contract)

    supply_cap_token = requests_util.get_supply_cap_raw(bloody_contract, decimals)
    supply_cat_pretty = str(util.number_to_beautiful(round(supply_cap_token * 55)))
    market_cap = util.number_to_beautiful(int(float(supply_cap_token * 55) * token_price_now_usd))

    vol_24h = requests_util.get_volume_24h(graphql_client_uni, bloody_contract)
    if token_price_7d_usd is not None and token_price_7d_usd != 0.0:
        var_7d = - int(((token_price_7d_usd - token_price_now_usd) / token_price_7d_usd) * 100) if token_price_7d_usd > token_price_now_usd else int(((token_price_now_usd - token_price_7d_usd) / token_price_7d_usd) * 100)
        var_7d_str = "+" + str(var_7d) + "%" if var_7d > 0 else str(var_7d) + "%"
    else:
        var_7d_str = "Not available"
    if token_price_1d_usd is not None and token_price_1d_usd != 0.0:
        var_1d = - int(((token_price_1d_usd - token_price_now_usd) / token_price_1d_usd) * 100) if token_price_1d_usd > token_price_now_usd else int(((token_price_now_usd - token_price_1d_usd) / token_price_1d_usd) * 100)
        var_1d_str = "+" + str(var_1d) + "%" if var_1d > 0 else str(var_1d) + "%"
    else:
        var_1d_str = "Not available"

    print("vol 24: " + str(vol_24h))

    vol_24_pretty = util.number_to_beautiful(vol_24h)

    msg_vol_24 = "\nVol 24H = $" + vol_24_pretty if vol_24_pretty != "0" else ""

    holders = requests_util.get_number_holder_token(bloody_contract)
    holders_str = "\nHolders = " + str(holders) if holders != -1 else ""
    ad = util.get_ad()
    message = "<code>" + name \
              + "\nETH: Ξ" + util.float_to_str(derivedETH_now)[0:10] \
              + "\nUSD: $" + util.float_to_str(token_price_now_usd)[0:10] \
              + "\n24H:  " + var_1d_str \
              + "\n7D :  " + var_7d_str \
              + "\n" \
              + msg_vol_24 \
              + "\nS.  Cap = " + supply_cat_pretty \
              + "\nM.  Cap = $" + market_cap \
              + holders_str \
              + "</code>" \
              + "\n"
    return message


# have to use custom function as supply is 55x what etherscan tells us
def get_price_token(update: Update, context: CallbackContext):
    message = special_custom_price()
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=message, parse_mode='html', reply_markup=reply_markup_price, disable_web_page_preview=True)


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
    try:
        context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html", reply_markup=reply_markup_chart)
    except telegram.error.BadRequest:
        print("couldn't find message to deleted but catched the error")
        pass


def refresh_price(update: Update, context: CallbackContext):
    print("refreshing price")
    message = special_custom_price()
    update.callback_query.edit_message_text(text=message, parse_mode='html', reply_markup=reply_markup_price, disable_web_page_preview=True)


def get_help(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    message = "Some bloody explanations right there: \n https://twitter.com/bag_hodler/status/1322371044506701824?s=21"
    context.bot.send_message(chat_id=chat_id, text=message, parse_mode='html', disable_web_page_preview=True)
    # general_end_functions.get_help(update, context)


def get_twitter(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    res = scrap_websites_util.get_last_tweets(twitter, ticker)
    context.bot.send_message(chat_id=chat_id, text=res, parse_mode='html', disable_web_page_preview=True)


def delete_chart_message(update: Update, context: CallbackContext):
    print("deleting chart")
    chat_id = update.callback_query.message.chat_id
    message_id = update.callback_query.message.message_id
    context.bot.delete_message(chat_id=chat_id, message_id=message_id)



# sends the current biz threads
def get_biz(update: Update, context: CallbackContext):
    global last_time_checked_4chan
    chat_id = update.message.chat_id
    new_time = round(time.time())
    if new_time - last_time_checked_4chan > 60:
        last_time_checked_4chan = new_time
        threads_ids = scrap_websites_util.get_biz_threads(re_4chan)

        base_url = "boards.4channel.org/biz/thread/"
        message = """Plz go bump the /biz/ threads:
"""
        for thread_id in threads_ids:
            excerpt = thread_id[2] + " | " + thread_id[1]
            message += base_url + str(thread_id[0]) + " -- " + excerpt[0: 100] + "[...] \n"
        if not threads_ids:
            # meme_url = git_handler.get_url_meme()
            meme_caption = "There hasn't been a Bloody /biz/ thread for a while, go make one https://boards.4channel.org/biz/."
            context.bot.send_message(chat_id=chat_id, text=meme_caption, disable_web_page_preview=True)
        else:
            context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True)
    else:
        context.bot.send_message(chat_id=chat_id,
                                 text='Only checking 4chan/twitter/charts once per minute. Don\'t spam.')


# sends the main links
def get_links(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=links, disable_web_page_preview=True, parse_mode='html')


def send_anthem(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    caption = "🎸🤘🎼 <i>I want my stacked boobiiiiieeesssss</i>🎼🤘🎸"
    context.bot.send_audio(chat_id=chat_id,
                           audio=open(BASE_PATH + 'audio/boo/boo_anthem.mp3', 'rb'),
                           caption=caption,
                           parse_mode='html')


def send_flyer(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    path = BASE_PATH + 'images/boo/flyer.jpg'
    context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'))


def log_current_supply():
    number_boob = requests_util.get_supply_cap_raw(bloody_contract, decimals)
    with open(supply_file_path, "a") as supply_file:
        time_now = datetime.now()
        date_time_str = time_now.strftime("%m/%d/%Y,%H:%M:%S")
        message_to_write = date_time_str + " " + str(number_boob) + "\n"
        supply_file.write(message_to_write)


def get_chart_supply(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    query_received = update.message.text.split(' ')

    time_type, k_hours, k_days, tokens = commands_util.check_query(query_received, ticker)

    current_boob_nbr, current_ecto_nbr = general_end_functions.send_supply_two_pyplot(supply_file_path,
                                                                                      k_days,
                                                                                      k_hours,
                                                                                      "BOOB",
                                                                                      "ECTO",
                                                                                      supply_chart_path)

    current_boob_str = util.number_to_beautiful(current_boob_nbr)
    current_ecto_str = util.number_to_beautiful(current_ecto_nbr)

    msg_time = " " + str(k_days) + " day(s) " if k_days > 0 else " last " + str(k_hours) + " hour(s) "

    caption = "Supply of the last " + msg_time + ".\nCurrent supply: \n<b>BOOB:</b> <pre>" + current_boob_str + \
              "</pre> \n<b>ECTO:</b> <pre>" + current_ecto_str + "</pre>"

    context.bot.send_photo(chat_id=chat_id,
                           photo=open(supply_chart_path, 'rb'),
                           caption=caption,
                           parse_mode="html")


def send_how_to_swap(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=how_to_swap, disable_web_page_preview=True, parse_mode='html')


def do_convert(update: Update, context: CallbackContext):
    query_received = update.message.text.split(' ')
    chat_id = update.message.chat_id
    message = general_end_functions.convert_to_something(query_received, graphql_client_uni, graphql_client_eth)
    context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True, parse_mode='html')


def handle_new_image(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    pprint.pprint(chat_id)
    try:
        caption = update['message']['caption']
        if caption == "/add_meme" and chat_id == -1001407194758:
            if git_handler.add_meme(update, context):
                context.bot.send_message(chat_id=chat_id, text="Got it boss!")
            else:
                error_msg = "Adding image failed: no image provided or incorrect format."
                context.bot.send_message(chat_id=chat_id, text=error_msg)
        else:
            __send_message_if_ocr(update, context)
    except KeyError:
        __send_message_if_ocr(update, context)


def __send_message_if_ocr(update, context):
    message_id = update.message.message_id
    chat_id = update.message.chat_id
    try:
        text_in_ocr = general_end_functions.ocr_image(update, context, TMP_FOLDER)
        if ('transaction cannot succeed' and 'one of the tokens' in text_in_ocr) or (
                'transaction will not succeed' and 'price movement or' in text_in_ocr):
            context.bot.send_message(chat_id=chat_id, text=test_error_token, reply_to_message_id=message_id)
    except IndexError:
        pass


def send_meme_to_chat(update: Update, context: CallbackContext):
    url = git_handler.get_url_meme()
    chat_id = update.message.chat_id
    context.bot.send_photo(chat_id=chat_id, photo=url)


def get_latest_actions(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    query_received = update.message.text.split(' ')
    if len(query_received) == 1:
        token_ticker = "BLOODY"
        latest_actions_pretty = general_end_functions.get_last_actions_token_in_eth_pair(token_ticker, uni_wrapper, graphql_client_uni)
        context.bot.send_message(chat_id=chat_id, text=latest_actions_pretty, disable_web_page_preview=True, parse_mode='html')
    elif len(query_received) == 2:
        token_ticker = query_received[1]
        latest_actions_pretty = general_end_functions.get_last_actions_token_in_eth_pair(token_ticker, uni_wrapper, graphql_client_uni)
        context.bot.send_message(chat_id=chat_id, text=latest_actions_pretty, disable_web_page_preview=True, parse_mode='html')
    else:
        context.bot.send_message(chat_id=chat_id, text="Please use the format /last_actions TOKEN_TICKER")


def main():
    updater = Updater(TELEGRAM_KEY, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('chart', get_candlestick))
    dp.add_handler(CommandHandler('price', get_price_token))
    dp.add_handler(CommandHandler('bloody', get_price_token))
    dp.add_handler(CallbackQueryHandler(refresh_chart, pattern='refresh_chart(.*)'))
    dp.add_handler(CallbackQueryHandler(refresh_price, pattern='refresh_price'))
    dp.add_handler(CallbackQueryHandler(delete_chart_message, pattern='delete_message'))
    dp.add_handler(CommandHandler('help', get_help))
    dp.add_handler(CommandHandler('twitter', get_twitter))
    dp.add_handler(CommandHandler('biz', get_biz))
    dp.add_handler(MessageHandler(Filters.photo, handle_new_image))
    dp.add_handler(CommandHandler('give_meme', send_meme_to_chat))
    dp.add_handler(CommandHandler('meme', send_meme_to_chat))
    # dp.add_handler(CommandHandler('chart_supply', get_chart_supply))
    dp.add_handler(CommandHandler('convert', do_convert))
    dp.add_handler(CommandHandler('last_actions', get_latest_actions))
    # RepeatedTimer(120, log_current_supply)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

commands = """
help - How to use the bot.
chart - Display a chart of the price.
bloody - Get the current price of $BLOODY.
twitter - Get the last tweets concerning $BLOODY.
biz - Display current 4chan threads.
convert - convert AMOUNT MONEY
"""
