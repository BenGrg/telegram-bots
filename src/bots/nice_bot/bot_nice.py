from gevent import monkey
monkey.patch_all()  # REALLY IMPORTANT: ALLOWS ZERORPC AND TG TO WORK TOGETHER

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, BaseFilter, \
    CallbackContext, Filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from twython import Twython, TwythonError
from graphqlclient import GraphQLClient
from PIL import Image
from git import Repo
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates
import matplotlib.pyplot
import csv
import requests
import random
import imagehash
import shutil
import time
import re
import random
import markovify
import locale
import os
import json
import plotly.graph_objects as go
from markovchain.text import MarkovText, ReplyMode
import pprint
import sys

BASE_PATH = os.environ.get('BASE_PATH')
sys.path.insert(1, BASE_PATH + '/telegram-bots/src')


from libraries.timer_util import RepeatedTimer
import libraries.graphs_util as graphs_util
import libraries.general_end_functions as general_end_functions
import libraries.commands_util as commands_util
import libraries.requests_util as requests_util
import libraries.util as util
import libraries.scrap_websites_util as scrap_websites_util
from libraries.uniswap import Uniswap
from libraries.common_values import *
from web3 import Web3
import zerorpc


# ZERORPC
zerorpc_client_data_aggregator = zerorpc.Client()
zerorpc_client_data_aggregator.connect("tcp://127.0.0.1:4243")
pprint.pprint(zerorpc_client_data_aggregator.hello("coucou"))

# web3
infura_url = os.environ.get('INFURA_URL')
pprint.pprint(infura_url)
w3 = Web3(Web3.HTTPProvider(infura_url))
uni_wrapper = Uniswap(web3=w3)


# ENV FILES
TELEGRAM_KEY = os.environ.get('NICE_TELEGRAM_KEY')
etherscan_api_key = os.environ.get('ETH_API_KEY')
APP_KEY = os.environ.get('TWITTER_API_KEY')
APP_SECRET = os.environ.get('TWITTER_API_KEY_SECRET')
ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
ACCESS_SECRET_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
MEME_GIT_REPO = os.environ.get('NICE_MEME_GIT_REPO')
TMP_FOLDER = os.environ.get('NICE_TMP_MEME_FOLDER')
BASE_PATH = os.environ.get('BASE_PATH')

charts_path = BASE_PATH + 'log_files/chart_bot/'

TMP_FOLDER = BASE_PATH + 'tmp/'

ethexplorer_holder_base_url = "https://ethplorer.io/service/service.php?data="

test_error_token = "Looks like you need to either: increase slippage (see /howtoslippage) and/or remove the decimals from the amount of ROT you're trying to buy"

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

req_graphql_vol24h_rot = '''{
  pairHourDatas(
    where: {hourStartUnix_gt: TIMESTAMP_MINUS_24_H, pair: "0x53f64be99da00fec224eaf9f8ce2012149d2fc88"})
    {
    hourlyVolumeUSD
  }
}'''

graphql_client_uni = GraphQLClient('https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2')
graphql_client_uni_2 = GraphQLClient('https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2')
graphql_client_eth = GraphQLClient('https://api.thegraph.com/subgraphs/name/blocklytics/ethereum-blocks')

# log_file
price_file_path = BASE_PATH + 'nice/log_files/price_hist.txt'
supply_file_path = BASE_PATH + 'nice/log_files/supply_hist.txt'
chart_price_file_path = BASE_PATH + 'nice/log_files/chart_price.png'
chart_supply_file_path = BASE_PATH + 'nice/log_files/chart_supply.png'
candels_file_path = BASE_PATH + 'nice/log_files/chart_candles.png'
david_logs_file_path = BASE_PATH + 'nice/log_files/david_logs.txt'
mahmoud_logs_file_path = BASE_PATH + 'nice/log_files/mahmoud_logs.txt'
all_logs_file_path = BASE_PATH + 'nice/log_files/all_logs.txt'
greg_logs_file_path = BASE_PATH + 'nice/log_files/greg_logs.txt'
tim_logs_file_path = BASE_PATH + 'nice/log_files/tim_logs.txt'
schizo_logs_file_path = BASE_PATH + 'nice/log_files/schizo_logs.txt'
legends_logs_file_path = BASE_PATH + 'nice/log_files/legends_logs.txt'
to_watch_log_file_path = BASE_PATH + 'nice/log_files/to_watch_logs.txt'
log_all = BASE_PATH + 'log_files/nice_bot/log.txt'

locale.setlocale(locale.LC_ALL, 'en_US')

# API PROPOSAL
api_proposal_url = 'https://rotapi.xyz/governance/getProposals'
last_proposal_received_id = -1
telegram_governance_url = 't.me/rottengovernance'
rotten_main_chat_id = -1001382715556
last_time_checked_price_chart = 0
last_time_checked_price_candles = 0
last_time_checked_price_supply = 0
last_time_checked_4chan = 0
last_time_checked_twitter = 0

re_4chan = re.compile(r'NICE| NICE |\$NICE')

twitter = Twython(APP_KEY, APP_SECRET, ACCESS_TOKEN, ACCESS_SECRET_TOKEN)

how_many_tweets = 5

## CONTRACT
nice_contract = '0x53f64be99da00fec224eaf9f8ce2012149d2fc88'
nice_contract_formatted_uni = "0x53f64be99da00fec224eaf9f8ce2012149d2fc88"

# messages

url_website = 'niceee.org'
url_uniswap_nice = 'https://app.uniswap.org/#/swap?inputCurrency=0x53f64be99da00fec224eaf9f8ce2012149d2fc88'
url_uniswap_pool_nice_eht = 'https://app.uniswap.org/#/add/ETH/0xD04785C4d8195e4A54d9dEc3a9043872875ae9E2'
url_etherscan_rot = 'https://etherscan.io/token/0x53f64be99da00fec224eaf9f8ce2012149d2fc88'
url_astrotools_rot = 'https://app.astrotools.io/pair-explorer/0x53f64be99da00fec224eaf9f8ce2012149d2fc88'
url_dextools_rot = 'https://www.dextools.io/app/uniswap/pair-explorer/0x53f64be99da00fec224eaf9f8ce2012149d2fc88'
url_coingecko_rot = 'https://www.coingecko.com/en/coins/rotten'
url_livecoinwatch_rot = 'https://www.livecoinwatch.com/price/Rotten-ROT'
url_twitter_rottenswap = 'https://twitter.com/thetimtempleton'
url_coinmarketcap = 'https://coinmarketcap.com/currencies/rotten/'


def create_href_str(url, message):
    return "<a href=\"" + url + "\">" + message + "</a>"


links = '<b>Website:</b> ' + create_href_str(url_website, 'rottenswap.org') + '\n' \
        + '<b>Uniswap:</b> ' + create_href_str(url_uniswap_nice, "$ROT") + '\n' \
        + '<b>Pools:</b> ' + create_href_str(url_uniswap_pool_nice_eht, 'ROT-ETH') + ' ' + '\n' \
        + '<b>Etherscan:</b> ' + create_href_str(url_etherscan_rot, '$ROT') + " " + '\n' \
        + '<b>Charts:</b> ' + create_href_str(url_astrotools_rot, 'Astrotools') + ' ' + create_href_str(
    url_dextools_rot, 'DexTools') + ' ' \
        + create_href_str(url_coingecko_rot, 'CoinGecko') + ' ' + create_href_str(url_livecoinwatch_rot,
                                                                                  'LiveCoinWatch') + ' ' + create_href_str(
    url_coinmarketcap, 'CoinMarketCap') + '\n' \
        + '<b>Social medias: </b>' + create_href_str(url_twitter_rottenswap, 'Twitter') + '\n' \
 \
    # GIT INIT
repo = Repo(MEME_GIT_REPO)
assert not repo.bare
repo.config_reader()  # get a config reader for read-only access
with repo.config_writer():  # get a config writer to change configuration
    pass  # call release() to be sure changes are written and locks are released
assert not repo.is_dirty()  # check the dirty state


# UTIL
def format_tweet(tweet):
    tweet_id = tweet['id_str']
    url = "twitter.com/anyuser/status/" + tweet_id
    message = tweet['text'].replace("\n", "").split('https')[0].replace('#', '').replace('@', '').replace('$', '')

    time_tweet_creation = tweet['created_at']
    new_datetime = datetime.strptime(time_tweet_creation, '%a %b %d %H:%M:%S +0000 %Y')
    current_time = datetime.utcnow()
    diff_time = current_time - new_datetime
    minutessince = int(diff_time.total_seconds() / 60)

    user = tweet['user']['screen_name']
    message_final = "<a href=\"" + url + "\"><b>" + str(
        minutessince) + " mins ago</b> | " + user + "</a> -- " + message + "\n"
    return message_final


# scraps the github project to get those sweet memes. Will chose one randomly and send it.
def get_url_meme():
    contents = requests.get("https://api.github.com/repos/niceeeeeeeeeee/memes/contents/memesFolder").json()
    potential_memes = []
    for file in contents:
        if ('png' in file['name'] or 'jpg' in file['name'] or 'jpeg' in file['name'] or 'mp4' in file['name']):
            potential_memes.append(file['download_url'])
    url = random.choice(potential_memes)
    return url


def send_meme_to_chat(update: Update, context: CallbackContext):
    url = get_url_meme()
    chat_id = update.message.chat_id
    context.bot.send_photo(chat_id=chat_id, photo=url)


# tutorial on how to increase the slippage.
def how_to_slippage(update: Update, context: CallbackContext):
    url = "https://i.imgur.com/TVFhZML.png"
    chat_id = update.message.chat_id
    context.bot.send_photo(chat_id=chat_id, photo=url)


def get_supply_cap_raw(contract_addr):
    base_addr = 'https://api.etherscan.io/api?module=stats&action=tokensupply&contractaddress=' + contract_addr + '&apikey=' + etherscan_api_key
    decimals = 1000000000000000000
    supply_cap = float(requests.post(base_addr).json()['result']) / decimals
    return supply_cap


# convert int to nice string: 1234567 => 1.234.567
def number_to_beautiful(nbr):
    return locale.format_string("%d", nbr, grouping=True).replace(",", " ")


# Get the supply cache from etherscan. Uses the ETH_API_KEY passed as an env variable.
def get_supply_cap(update: Update, context: CallbackContext):
    number_nice = str(round(get_supply_cap_raw(nice_contract)))
    message = "It's <b>NICE</b> around here! There are <pre>" + number_nice + "</pre> NICE tokens"
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=message, parse_mode='html')


# scraps /biz/ and returns a list of tuple (threadId, body, title) of threads matching the regex ^rot |rot$| rot |rotten|rotting
def get_biz_threads():
    url = 'https://a.4cdn.org/biz/catalog.json'
    response_json = requests.get(url).json()
    threads_ids = []
    for page in response_json:
        for thread in page['threads']:
            try:
                if 'com' in thread:
                    com = thread['com']
                else:
                    com = ""
                if 'sub' in thread:
                    sub = thread['sub']
                else:
                    sub = ""
            except KeyError:
                print("ERROR")
                pass
            else:
                if re_4chan.search(com) or re_4chan.search(sub):
                    thread_id = thread['no']
                    threads_ids.append((thread_id, com, sub))
    return threads_ids


# sends the current biz threads
def get_biz(update: Update, context: CallbackContext):
    global last_time_checked_4chan
    chat_id = update.message.chat_id
    new_time = round(time.time())
    if new_time - last_time_checked_4chan > 60:
        last_time_checked_4chan = new_time
        threads_ids = get_biz_threads()

        base_url = "boards.4channel.org/biz/thread/"
        message = """Plz go bump the /biz/ threads:
"""
        for thread_id in threads_ids:
            excerpt = thread_id[2] + " | " + thread_id[1]
            message += base_url + str(thread_id[0]) + " -- " + excerpt[0: 100] + "[...] \n"
        if not threads_ids:
            meme_url = get_url_meme()
            print("sent reminder 4chan /biz/")
            meme_caption = "There hasn't been a Rotten /biz/ thread for a while. Plz go make one https://boards.4channel.org/biz/, here's a meme, go make one."
            context.bot.send_photo(chat_id=chat_id, photo=meme_url, caption=meme_caption)
        else:
            context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True)
    else:
        context.bot.send_message(chat_id=chat_id,
                                 text='Only checking 4chan/twitter/charts once per minute. Don\'t spam.')


# sends the main links
def get_links(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=links, disable_web_page_preview=True, parse_mode='html')


# tutorial on how to stake
def stake_command(update: Update, context: CallbackContext):
    text = """<b>How to stake/farm ROT :</b> 

1. Buy on Uniswap : https://app.uniswap.org/#/swap?inputCurrency=0xd04785c4d8195e4a54d9dec3a9043872875ae9e2

2. Make sure to add the ROT contract number in your wallet so your wallet can show your ROT coins (metamask etc)

3. Buy/transfer eth

4. Add Liquidity ...
...
See the full instructions on https://medium.com/@rotted_ben/how-to-stake-on-rottenswap-5c71bdf57390"""
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=text, parse_mode='html', disable_web_page_preview=True)


last_time_since_check = 0


# callback function that sends a reminder if no /biz/ threads are rooting
def callback_4chan_thread(update: Update, context: CallbackContext):
    job = context.job
    global last_time_since_check
    biz = get_biz_threads()
    if not biz:
        meme_url = get_url_meme()
        last_time_since_check += 15
        print("sending 4chan reminder, no post for " + str(last_time_since_check))
        meme_caption = "There hasn't been a Rotten /biz/ thread in the last " + str(
            last_time_since_check) + " minutes. Plz go make one https://boards.4channel.org/biz/, here's a meme."
        context.bot.send_photo(chat_id=job.context, photo=meme_url, caption=meme_caption)
        # context.bot.send_message(chat_id=job.context, text='No /biz/ threads for a while. Let\'s go make one!')
    else:
        last_time_since_check = 0


def callback_timer(update: Update, context: CallbackContext):
    job = context.job
    print("CHAT ID:" + str(update.message.chat_id))
    context.bot.send_message(chat_id=update.message.chat_id, text='gotcha')
    job.run_repeating(callback_4chan_thread, 900, context=update.message.chat_id)


def query_tweets(easy=True):
    if easy:
        return twitter.search(q='$NICE')
    else:
        return twitter.search(q='$NICE')


def filter_tweets(all_tweets):
    message = ""
    if all_tweets.get('statuses'):
        count = 0
        tweets = all_tweets['statuses']
        for tweet in tweets:
            if "RT " not in tweet['text']:
                if count < how_many_tweets:
                    message = message + format_tweet(tweet)
                    count = count + 1
    return message


def get_last_tweets(update: Update, context: CallbackContext):
    global last_time_checked_twitter
    chat_id = update.message.chat_id
    new_time = round(time.time())
    if new_time - last_time_checked_twitter > 60:
        last_time_checked_twitter = new_time
        try:
            results = query_tweets(False)
        except TwythonError:
            time.sleep(0.5)
            results = query_tweets(False)
        message = "<b>Normies are tweeting about NICE, go comment/like/RT:</b>\n"
        rest_message = filter_tweets(results)
        if rest_message == "":
            print("empty tweets, fallback")
            results = query_tweets(False)
            rest_message = filter_tweets(results)
        full_message = message + rest_message
        chat_id = update.message.chat_id
        context.bot.send_message(chat_id=chat_id, text=full_message, parse_mode='html', disable_web_page_preview=True)
    else:
        context.bot.send_message(chat_id=chat_id,
                                 text='Only checking 4chan/twitter/charts once per minute. Don\'t spam.')


def download_image(update: Update, context: CallbackContext):
    image = context.bot.getFile(update.message.photo[-1])
    file_id = str(image.file_id)
    print("file_id: " + file_id)
    img_path = MEME_GIT_REPO + '/memesFolder/' + file_id + ".png"
    image.download(img_path)
    return img_path


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


# ADD MEME or PERFORM OCR to see if request to increase slippage
def handle_new_image(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    try:
        caption = update['message']['caption']
        if caption == "/add_meme" and chat_id == -1001187740219:
            try:
                tmp_path = download_image(update, context)
                img_hash = calculate_hash(tmp_path)
                is_present = check_file_already_present(img_hash)
                if not is_present:
                    filename = img_hash + '.jpg'
                    copy_file_to_git_meme_folder(tmp_path, filename)
                    add_file_to_git(filename)
                    context.bot.send_message(chat_id=chat_id, text="Got it boss!")
                else:
                    context.bot.send_message(chat_id=chat_id, text="Image already registered")
            except IndexError:
                error_msg = "Adding image failed: no image provided. Make sure to send it as a file and not an image."
                context.bot.send_message(chat_id=chat_id, text=error_msg)
        else:
            __send_message_if_ocr(update, context)
    except KeyError:
        __send_message_if_ocr(update, context)


def copy_file_to_git_meme_folder(path, hash_with_extension):
    shutil.copyfile(path, MEME_GIT_REPO + '/memesFolder/' + hash_with_extension)


def calculate_hash(path_to_image):
    return str(imagehash.average_hash(Image.open(path_to_image)))


def add_file_to_git(filename):
    index = repo.index
    index.add(MEME_GIT_REPO + "/memesFolder/" + filename)
    index.commit("adding dank meme " + filename)
    origin = repo.remote('origin')
    origin.push(force=True)


# Returns True if the file is already present in the MEME_GIT_REPO directory
def check_file_already_present(meme_hash):
    found = False
    for file in os.listdir(MEME_GIT_REPO + '/memesFolder/'):
        filename = os.fsdecode(file)
        filename_no_extension = filename.split(".")[0]
        if filename_no_extension == meme_hash:
            found = True
    return found


# REMOVE MEME
def delete_meme(update: Update, context: CallbackContext):
    query_received = update.message.text.split(' ')
    if len(query_received) == 3:
        print("someone wants to delete a meme")
        password = query_received[1]
        if password == "adbe5443-3bed-4230-a2e7-a94c8a8401ef":
            print("password correct")
            to_delete = query_received[2]
            if check_file_already_present(to_delete):
                print("meme found")
                filename = to_delete + '.jpg'
                index = repo.index
                index.remove(MEME_GIT_REPO + "/memesFolder/" + filename)
                index.commit("adding dank meme " + filename)
                origin = repo.remote('origin')
                origin.push(force=True)
                os.remove(MEME_GIT_REPO + "/memesFolder/" + filename)
                print("deleting meme " + to_delete)
                chat_id = update.message.chat_id
                context.bot.send_message(chat_id=chat_id, text="removed" + filename)


def get_number_holder_token(token):
    url = ethexplorer_holder_base_url + token
    res = requests.get(url).json()
    try:
        holders = res['pager']['holders']['records']
    except KeyError:
        holders = -1
    return int(holders)


def get_ad():
    return ""


# graphql queries
def get_price_nice_raw():
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

    query_uni_updated = query_uni.replace("CONTRACT", nice_contract_formatted_uni) \
        .replace("NUMBER_T1", str(block_from_7d)) \
        .replace("NUMBER_T2", str(block_from_1d)) \
        .replace("NUMBER_TNOW", str(latest_block))

    res_uni_query = graphql_client_uni.execute(query_uni_updated)
    json_resp_uni = json.loads(res_uni_query)

    # pprint.pprint(json_resp_uni)

    try:
        rot_per_eth_now = float(json_resp_uni['data']['tnow']['derivedETH'])
    except KeyError:  # trying again, as sometimes the block that we query has not yet been indexed. For that, we read
        # the error message returned by uniswap and work on the last indexed block that is return in the error message
        # TODO: work with regex as block numbers can be < 10000000
        last_block_indexed = str(res_uni_query).split('indexed up to block number ')[1][0:8]
        query_uni_updated = query_uni.replace("CONTRACT", nice_contract_formatted_uni) \
            .replace("NUMBER_T1", str(block_from_7d)) \
            .replace("NUMBER_T2", str(block_from_1d)) \
            .replace("NUMBER_TNOW", str(last_block_indexed))
        res_uni_query = graphql_client_uni.execute(query_uni_updated)
        json_resp_uni = json.loads(res_uni_query)
        rot_per_eth_now = float(json_resp_uni['data']['tnow']['derivedETH'])

    rot_per_eth_7d = 0.0  # float(json_resp_uni['data']['t1']['derivedETH'])
    rot_per_eth_1d = float(json_resp_uni['data']['t2']['derivedETH'])
    rot_per_eth_now = float(json_resp_uni['data']['tnow']['derivedETH'])

    eth_price_7d = float(json_resp_uni['data']['b1']['ethPrice'])
    eth_price_1d = float(json_resp_uni['data']['b2']['ethPrice'])
    eth_price_now = float(json_resp_uni['data']['bnow']['ethPrice'])

    rot_price_7d_usd = 0.0  # rot_per_eth_7d * eth_price_7d
    rot_price_1d_usd = rot_per_eth_1d * eth_price_1d
    rot_price_now_usd = rot_per_eth_now * eth_price_now

    return (rot_per_eth_7d, rot_price_7d_usd, rot_per_eth_1d, rot_price_1d_usd, rot_per_eth_now, rot_price_now_usd)


# return the amount of maggot per rot
def get_ratio_rot_per_maggot(last_swaps_maggot_rot_pair):
    interesting_part = last_swaps_maggot_rot_pair['data']['swaps'][0]
    last_swaps_amount_maggot_in = float(interesting_part['amount0In'])
    last_swaps_amount_maggot_out = float(interesting_part['amount0Out'])
    last_swaps_amount_rot_in = float(interesting_part['amount1In'])
    last_swaps_amount_rot_out = float(interesting_part['amount1Out'])
    # check which direction the transaction took place. For that, if amount1In = 0, it was maggot -> rot
    transaction_direction_maggot_to_rot = (last_swaps_amount_rot_in == 0)
    if transaction_direction_maggot_to_rot:
        return last_swaps_amount_rot_out / last_swaps_amount_maggot_in
    else:
        return last_swaps_amount_rot_in / last_swaps_amount_maggot_out


# return price 7 days ago, price 1 day ago, volume last 24h
def get_volume_24h_nice():
    now = int(time.time())
    yesterday = now - 3600 * 24

    res = graphql_client_uni_2.execute(req_graphql_vol24h_rot.replace("TIMESTAMP_MINUS_24_H", str(yesterday)))

    json_resp_eth = json.loads(res)

    # pprint.pprint(res)

    all_values = json_resp_eth['data']['pairHourDatas']

    amount = 0
    for value in all_values:
        amount += round(float(value['hourlyVolumeUSD']))

    return amount


def get_price_nice(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    ticker = "NICE"
    contract_from_ticker = requests_util.get_token_contract_address(ticker)
    pprint.pprint(contract_from_ticker)
    button_list_price = [[InlineKeyboardButton('refresh', callback_data='r_p_' + contract_from_ticker + "_t_" + ticker)]]
    reply_markup_price = InlineKeyboardMarkup(button_list_price)
    message = general_end_functions.get_price(contract_from_ticker, "", graphql_client_eth, graphql_client_uni, ticker.upper(), 10**18)
    util.create_and_send_vote(ticker, "price", update.message.from_user.name, zerorpc_client_data_aggregator)
    context.bot.send_message(chat_id=chat_id, text=message, parse_mode='html', reply_markup=reply_markup_price, disable_web_page_preview=True)


def log_current_price_rot_per_usd():
    global price_file_path
    (derivedETH_7d, rot_price_7d_usd, derivedETH_1d, rot_price_1d_usd, derivedETH_now,
     rot_price_now_usd) = get_price_nice_raw()
    with open(price_file_path, "a") as price_file:
        time_now = datetime.now()
        date_time_str = time_now.strftime("%m/%d/%Y,%H:%M:%S")
        message_to_write = date_time_str + " " + str(rot_price_now_usd) + "\n"
        price_file.write(message_to_write)


def log_current_supply():
    global supply_file_path
    number_rot = get_supply_cap_raw(nice_contract)
    with open(supply_file_path, "a") as supply_file:
        time_now = datetime.now()
        date_time_str = time_now.strftime("%m/%d/%Y,%H:%M:%S")
        message_to_write = date_time_str + " " + str(number_rot) + " " + "\n"
        supply_file.write(message_to_write)


def get_help(update: Update, context: CallbackContext):
    message = "Technical issues? A question? Need help? Join the guys at @rottenhelpgroup."
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=message)


def get_fake_price(update: Update, context: CallbackContext):
    message = '''<pre>FOR LEGAL REASONS THAT'S FAKE PRICE
(ROT) RottenToken
ETH: Ξ0.01886294
USD: $6.66000000
24H:   66%
7D :  666%

Vol 24H = $6 666 666
1 ETH   = 53 ROT
Holders = 6666
Con.Adr = 0xd04...9e2
@allUniSwapListings</pre>'''
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=message, parse_mode='html')


# def check_new_proposal(update: Update, context: CallbackContext):
#     global last_proposal_received_id
#     global last_time_checked
#
#     new_time = round(time.time())
#     if new_time - last_time_checked > 60:
#         pass
# print("Checking for new proposals...")
# log_current_price_rot_per_usd()
# log_current_supply()
# last_time_checked = new_time
# response_json = requests.get(api_proposal_url).json()
# if response_json != "" or response_json is not None:
#     last_proposal = response_json[-1]
#     id_last_proposal = last_proposal['id']
#     if last_proposal_received_id == -1:  # check if the bot just initialized
#         last_proposal_received_id = id_last_proposal
#     else:
#         if id_last_proposal > last_proposal_received_id:
#             last_proposal_received_id = id_last_proposal
#             proposal_title = last_proposal['title']
#             description = last_proposal['description']
#             message = 'New proposal added: <b>' + proposal_title + '</b>\n' \
#                       + description + '\nGo vote at ' \
#                       + telegram_governance_url
#             print("New proposal found and sent")
#             context.bot.send_message(chat_id=rotten_main_chat_id, text=message, parse_mode='html')


def get_from_query(query_received):
    time_type = query_received[2]
    time_start = int(query_received[1])
    if time_start < 0:
        time_start = - time_start
    k_hours = 0
    k_days = 0
    if time_type == 'h' or time_type == 'H':
        k_hours = time_start
    if time_type == 'd' or time_type == 'D':
        k_days = time_start
    return time_type, time_start, k_hours, k_days


def strp_date(raw_date):
    return datetime.strptime(raw_date, '%m/%d/%Y,%H:%M:%S')


# util for get_chart_pyplot
def keep_dates(values_list):
    dates_str = []
    for values in values_list:
        dates_str.append(values[0])

    dates_datetime = []
    for date_str in dates_str:
        date_datetime = datetime.strptime(date_str, '%m/%d/%Y,%H:%M:%S')
        dates_datetime.append(date_datetime)
    return dates_datetime


def print_chart_price(dates_raw, price):
    dates = matplotlib.dates.date2num(dates_raw)
    cb91_green = '#47DBCD'
    plt.style.use('dark_background')
    matplotlib.rcParams.update({'font.size': 22})
    f = plt.figure(figsize=(16, 9))
    ax = f.add_subplot(111)
    ax.yaxis.set_major_formatter('${x:1.3f}')
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    ax.yaxis.grid(alpha=0.3, linestyle='--')

    plt.plot_date(dates, price, cb91_green)
    plt.gcf().autofmt_xdate()
    plt.savefig(chart_price_file_path, bbox_inches='tight', dpi=300)
    plt.close(f)


def print_chart_supply(dates_raw, supply_rot):
    dates = matplotlib.dates.date2num(dates_raw)
    cb91_green = '#47DBCD'
    plt.style.use('dark_background')

    matplotlib.rcParams.update({'font.size': 22})
    f = plt.figure(figsize=(16, 9))

    ax = f.add_subplot(111)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))

    ax2 = ax.twinx()
    ax2.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    plot2 = ax2.plot_date(dates, supply_rot, cb91_green, label='rot')

    ax.set_ylabel("Maggot")
    ax2.set_ylabel("Rot")

    plots = plot2
    labs = [l.get_label() for l in plots]
    ax.legend(plots, labs, bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left',
              ncol=2, mode="expand", borderaxespad=0.)

    plt.gcf().autofmt_xdate()
    plt.savefig(chart_supply_file_path, bbox_inches='tight', dpi=300)
    plt.close(f)


def get_chart_price_pyplot(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    global last_time_checked_price_chart

    query_received = update.message.text.split(' ')
    if update.message.from_user.first_name == 'Ben':
        print("hello me")
        last_time_checked_price_chart = 1

    time_type, time_start, k_hours, k_days, query_ok, simple_query, token = check_query(query_received)

    if query_ok:
        new_time = round(time.time())
        if new_time - last_time_checked_price_chart > 60:
            if update.message.from_user.first_name != 'Ben':
                last_time_checked_price_chart = new_time
            list_time_price = []

            with open(price_file_path, newline='') as csvfile:
                spamreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
                for row in spamreader:
                    list_time_price.append((row[0], row[1]))

            now = datetime.utcnow()

            filtered_values = [x for x in list_time_price if
                               now - strp_date(x[0]) < timedelta(days=k_days, hours=k_hours)]

            dates_pure = keep_dates(filtered_values)
            price = [float(value[1]) for value in filtered_values]

            print_chart_price(dates_pure, price)

            if simple_query:
                caption = "Chart since the bot starting logging the price.\nCurrent price: <pre>$" + str(price[-1])[
                                                                                                     0:10] + "</pre>"
            else:
                caption = "Price of the last " + str(time_start) + str(time_type) + ".\nCurrent price: <pre>$" + str(
                    price[-1])[0:10] + "</pre>"

            if random.randrange(10) > 6:
                ad = get_ad()
                caption = caption + "\n" + ad

            context.bot.send_photo(chat_id=chat_id,
                                   photo=open(chart_price_file_path, 'rb'),
                                   caption=caption,
                                   parse_mode="html")
        else:
            context.bot.send_message(chat_id=chat_id,
                                     text="Displaying charts only once every minute. Don't abuse this NICE function")
    else:
        context.bot.send_message(chat_id=chat_id,
                                 text="Request badly formated. Please use /getchart time type (example: /getchart 3 h for the last 3h time range). Simply editing your message will not work, please send a new correctly formated message.")


def check_query(query_received):
    query_ok, simple_query = True, False
    time_type, time_start, k_hours, k_days, token = 'd', 1, 0, 1, "NICE"
    if len(query_received) == 1:
        simple_query = True
    elif len(query_received) == 2:
        token = query_received[1]
    elif len(query_received) == 3:
        time_type, time_start, k_hours, k_days = get_from_query(query_received)
    elif len(query_received) == 4:
        time_type, time_start, k_hours, k_days = get_from_query(query_received)
        token = query_received[-1]
    else:
        query_ok = False
    return time_type, time_start, k_hours, k_days, query_ok, simple_query, token


def get_candlestick_pyplot(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    query_received = update.message.text.split(' ')

    time_type, k_hours, k_days, tokens = commands_util.check_query(query_received, "NICE")
    t_to = int(time.time())
    t_from = t_to - (k_days * 3600 * 24) - (k_hours * 3600)

    if isinstance(tokens, list):
        for token in tokens:
            (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(token, charts_path, k_days, k_hours, t_from, t_to)
            util.create_and_send_vote(token, "chart", update.message.from_user.name, zerorpc_client_data_aggregator)
            context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html", reply_markup=reply_markup_chart)
    else:
        (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(tokens, charts_path, k_days, k_hours, t_from, t_to)
        util.create_and_send_vote(tokens, "chart", update.message.from_user.name, zerorpc_client_data_aggregator)
        context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html", reply_markup=reply_markup_chart)


def get_chart_supply_pyplot(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    global last_time_checked_price_supply

    query_received = update.message.text.split(' ')
    if update.message.from_user.first_name == 'Ben':
        print("hello me")
        last_time_checked_price_supply = 1

    time_type, time_start, k_hours, k_days, query_ok, simple_query, token = check_query(query_received)

    if query_ok:
        new_time = round(time.time())
        if new_time - last_time_checked_price_supply > 60:
            if update.message.from_user.first_name != 'Ben':
                last_time_checked_price_supply = new_time
            list_time_supply = []

            with open(supply_file_path, newline='') as csvfile:
                pprint.pprint(supply_file_path)
                spamreader = csv.reader((line.replace('\0', '') for line in csvfile), delimiter=' ', quotechar='|')
                for row in spamreader:
                    try:
                        list_time_supply.append((row[0], row[1]))
                    except csv.Error:
                        pass

            now = datetime.utcnow()

            filtered_values = [x for x in list_time_supply if
                               now - strp_date(x[0]) < timedelta(days=k_days, hours=k_hours)]

            dates_pure = keep_dates(filtered_values)
            supply_rot = [float(value[1]) for value in filtered_values]

            print_chart_supply(dates_pure, supply_rot)
            current_rot_str = str(round(supply_rot[-1]))
            if simple_query:
                caption = "Chart since the bot starting logging the supply.\nCurrent supply of <b>NICE:</b> <pre>" + current_rot_str + "</pre>"
            else:
                caption = "Supply of the last " + str(time_start) + str(
                    time_type) + ".\nCurrent supply: \n<b>NICE:</b> <pre>" + current_rot_str + "</pre>"

            if random.randrange(10) > 6:
                ad = get_ad()
                caption = caption + "\n" + ad

            context.bot.send_photo(chat_id=chat_id,
                                   photo=open(chart_supply_file_path, 'rb'),
                                   caption=caption,
                                   parse_mode="html")
        else:
            context.bot.send_message(chat_id=chat_id,
                                     text="Displaying charts only once every minute. Don't abuse this function")
    else:
        context.bot.send_message(chat_id=chat_id,
                                 text="Request badly formated. Please use /getchartsupply time type (example: /getchart 3 h for the last 3h time range). Simply editing your message will not work, please send a new correctly formated message.")


def get_airdrop(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    message = '''<a href="https://twitter.com/RottenSwap/status/1311624434038509568">As promised, here are the #airdrop details:
- Follow us, like and RT this tweet (click me),
- Join our TelegramGroup http://t.me/rottenswap,
- Hold 7,500 $ROT tokens minimum at snapshot time (random time between 1st and 31st October),
- Fill the form:</a> <a href="https://docs.google.com/forms/d/1Zjb0m9tSpqkjG9qql6kuMNIBLU7_29kekDf4rVOrUS4">https://docs.google.com/forms/d/1Zjb0m9tSpqkjG9qql6kuMNIBLU7_29kekDf4rVOrUS4</a>'''
    context.bot.send_message(chat_id=chat_id,
                             text=message,
                             parse_mode='html',
                             disable_web_page_preview=True)


def log_message(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    try:
        if update.message.from_user.username == 'cupckke':
            with open(david_logs_file_path, "a") as price_file:
                message_to_write = str(update.message.message_id) + "///))()" + str(update.message.text).replace("\n",
                                                                                                                 " ") + "\n"
                price_file.write(message_to_write)
        elif update.message.from_user.username == 'WNoailles':
            with open(schizo_logs_file_path, "a") as price_file:
                message_to_write = str(update.message.message_id) + "///))()" + str(update.message.text).replace("\n",
                                                                                                                 " ") + "\n"
                price_file.write(message_to_write)
        elif update.message.from_user.username == 'timtemplet':
            with open(tim_logs_file_path, "a") as price_file:
                message_to_write = str(update.message.message_id) + "///))()" + str(update.message.text).replace("\n",
                                                                                                                 " ") + "\n"
                price_file.write(message_to_write)
        elif update.message.from_user.username == 'FotanEnergy':
            with open(greg_logs_file_path, "a") as price_file:
                message_to_write = str(update.message.message_id) + "///))()" + str(update.message.text).replace("\n",
                                                                                                                 " ") + "\n"
                price_file.write(message_to_write)

        with open(all_logs_file_path, "a") as price_file:
            message_to_write = str(update.message.message_id) + "///))()" + str(update.message.text).replace("\n", ".").replace("nigger", " ").replace("nigga", " ")
            message_to_write += "\n"
            price_file.write(message_to_write)
    except AttributeError:
        pass


def generate_random_message_raw(filepath):
    with open(david_logs_file_path) as f:
        msgs = [line.rstrip().split('///))()')[1] for line in f]
    msg = ' '.join(msgs)
    text_model = markovify.Text(msg)
    return text_model.make_short_sentence(400)


def get_random_message_mahmoud(update: Update, context: CallbackContext):
    with open(mahmoud_logs_file_path) as f:
        msgs = [line.rstrip().split('///))()') for line in f]
    selected_message = random.choice(msgs)
    context.bot.send_message(text=selected_message[1],
                             reply_to_message_id=selected_message[0],
                             chat_id=update.message.chat_id,
                             disable_web_page_preview=True)


def get_random_message_david(update: Update, context: CallbackContext):
    with open(david_logs_file_path) as f:
        msgs = [line.rstrip().split('///))()') for line in f]
    selected_message = random.choice(msgs)
    context.bot.send_message(text="David says: \n" + selected_message[1],
                             chat_id=update.message.chat_id,
                             disable_web_page_preview=True)


def get_random_message_tim(update: Update, context: CallbackContext):
    with open(tim_logs_file_path) as f:
        msgs = [line.rstrip().split('///))()') for line in f]
    selected_message = random.choice(msgs)
    context.bot.send_message(text=selected_message[1],
                             reply_to_message_id=selected_message[0],
                             chat_id=update.message.chat_id,
                             disable_web_page_preview=True)


def get_random_message_schizo(update: Update, context: CallbackContext):
    with open(schizo_logs_file_path) as f:
        msgs = [line.rstrip().split('///))()') for line in f]
    selected_message = random.choice(msgs)
    context.bot.send_message(text=selected_message[1],
                             reply_to_message_id=selected_message[0],
                             chat_id=update.message.chat_id,
                             disable_web_page_preview=True)


def generate_random_david(update: Update, context: CallbackContext):
    res = generate_random_message_raw(david_logs_file_path)
    if random.randrange(10) == 5:
        res = '<a href="https://app.rarible.com/token/0xd07dc4262bcdbf85190c01c996b4c06a461d2430:37562:0xd08517cd0372cd12b710a554f5025cfd419b43ff">' + res + '</a>'
    context.bot.send_message(text=res,
                             chat_id=update.message.chat_id,
                             disable_web_page_preview=True,
                             parse_mode="html")


def generate_random_gregg(update: Update, context: CallbackContext):
    with open(greg_logs_file_path) as f:
        msgs = [line.rstrip().split('///))()')[1] for line in f]
    msg = ' '.join(msgs)
    text_model = markovify.Text(msg)
    res = text_model.make_short_sentence(280)
    context.bot.send_message(text=res,
                             chat_id=update.message.chat_id,
                             disable_web_page_preview=True,
                             parse_mode="html")


def generate_random_all_chat(update: Update, context: CallbackContext):
    with open(all_logs_file_path) as f:
        msgs = [line.rstrip().split('///))()')[1] for line in f]
    msg = ' '.join(msgs)
    text_model = markovify.Text(msg)
    res = text_model.make_short_sentence(280)
    if res is None or res == "null":
        markov = MarkovText()
        markov.data(msg)
        res = markov()
    context.bot.send_message(text=res,
                             chat_id=update.message.chat_id,
                             disable_web_page_preview=True)


def generate_random_mahmoud(update: Update, context: CallbackContext):
    with open(mahmoud_logs_file_path) as f:
        msgs = [line.rstrip().split('///))()')[1] for line in f]
    msg = ' '.join(msgs)
    text_model = markovify.Text(msg)
    res = text_model.make_short_sentence(280)
    context.bot.send_message(text=res,
                             chat_id=update.message.chat_id,
                             disable_web_page_preview=True,
                             parse_mode="html")


def generate_random_all_raw():
    with open(david_logs_file_path) as f:
        davids = [line.rstrip().split('///))()')[1] for line in f]
    with open(tim_logs_file_path) as f:
        tims = [line.rstrip().split('///))()')[1] for line in f]
    with open(schizo_logs_file_path) as f:
        schizos = [line.rstrip().split('///))()')[1] for line in f]

    david_msg = ' '.join(davids)
    pprint.pprint(david_msg)
    tim_msg = ' '.join(tims)
    schizo_msg = ' '.join(schizos)
    all_mixed = tim_msg + david_msg + schizo_msg
    text_model = markovify.Text(all_mixed)
    return text_model.make_short_sentence(400)


def generate_random_all(update: Update, context: CallbackContext):
    res = generate_random_all_raw()
    context.bot.send_message(text=res,
                             chat_id=update.message.chat_id,
                             disable_web_page_preview=True)


def generate_random_all_stats(update: Update, context: CallbackContext):
    with open(david_logs_file_path) as f:
        davids = [line.rstrip().split('///))()')[1] for line in f]
    with open(tim_logs_file_path) as f:
        tims = [line.rstrip().split('///))()')[1] for line in f]
    with open(schizo_logs_file_path) as f:
        schizos = [line.rstrip().split('///))()')[1] for line in f]
    david_msg = ' '.join(davids)
    tim_msg = ' '.join(tims)
    schizo_msg = ' '.join(schizos)
    percent_david = len(david_msg) / (len(david_msg) + len(tim_msg) + len(schizo_msg))
    percent_tim = len(tim_msg) / (len(david_msg) + len(tim_msg) + len(schizo_msg))
    percent_schizo = len(schizo_msg) / (len(david_msg) + len(tim_msg) + len(schizo_msg))
    text = "Percentage of message logged by user: \n" \
           + "david: " + str(round(percent_david * 100)) + "\n" \
           + "tim: " + str(round(percent_tim * 100)) + "\n" \
           + "schizo: " + str(round(percent_schizo * 100))
    context.bot.send_message(text=text,
                             chat_id=update.message.chat_id,
                             disable_web_page_preview=True)


def add_message_to_ai(update: Update, context: CallbackContext):
    if not os.path.isfile(legends_logs_file_path):
        f = open(legends_logs_file_path, "x")
        f.close()
    msg_to_add = update.message.text[7:].replace('\n', '').lstrip()
    msg_id = update.message.message_id

    with open(legends_logs_file_path) as f:
        msgs = [line.rstrip() for line in f]

    if msg_to_add in msgs:
        context.bot.send_message(reply_to_message_id=msg_id, text="Already stored fam", chat_id=update.message.chat_id,
                                 disable_web_page_preview=True)
    else:
        with open(legends_logs_file_path, "a") as fav_file:
            message_to_write = msg_to_add + "\n"
            fav_file.write(message_to_write)
        context.bot.send_message(reply_to_message_id=msg_id, text="Added it fam.", chat_id=update.message.chat_id,
                                 disable_web_page_preview=True)


def generate_random_legend(update: Update, context: CallbackContext):
    markov = MarkovText()

    with open(legends_logs_file_path) as fp:
        markov.data(fp.read())

    markov.data('', part=False)

    res = markov()

    if res == "null" or res is None:
        context.bot.send_message(text="Not enough data to generate something. Feed me with /add_ai plzzzz.",
                                 chat_id=update.message.chat_id,
                                 disable_web_page_preview=True)
    else:
        context.bot.send_message(text=res,
                                 chat_id=update.message.chat_id,
                                 disable_web_page_preview=True)


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


def refresh_price(update: Update, context: CallbackContext):
    print("refreshing price")
    query = update.callback_query.data
    contract_from_ticker = query.split('r_p_')[1].split('_t')[0]
    token_name = query.split('_t_')[1]

    message = general_end_functions.get_price(contract_from_ticker, "", graphql_client_eth, graphql_client_uni,
                                              token_name.upper(), 10**18)
    button_list_price = [[InlineKeyboardButton('refresh', callback_data='refresh_price_' + contract_from_ticker)]]
    reply_markup_price = InlineKeyboardMarkup(button_list_price)
    update.callback_query.edit_message_text(text=message, parse_mode='html', reply_markup=reply_markup_price, disable_web_page_preview=True)


def delete_message(update: Update, context: CallbackContext):
    print("deleting chart")
    chat_id = update.callback_query.message.chat_id
    message_id = update.callback_query.message.message_id
    context.bot.delete_message(chat_id=chat_id, message_id=message_id)


def do_convert(update: Update, context: CallbackContext):
    query_received = update.message.text.split(' ')
    chat_id = update.message.chat_id
    message = general_end_functions.convert_to_something(query_received, graphql_client_uni, graphql_client_eth)
    context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True, parse_mode='html')


def get_latest_actions(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    query_received = update.message.text.split(' ')
    if len(query_received) == 1:
        token_ticker = "NICE"
        latest_actions_pretty = general_end_functions.get_last_actions_token_in_eth_pair(token_ticker, uni_wrapper, graphql_client_uni)
        context.bot.send_message(chat_id=chat_id, text=latest_actions_pretty, disable_web_page_preview=True, parse_mode='html')
    elif len(query_received) == 2:
        token_ticker = query_received[1]
        latest_actions_pretty = general_end_functions.get_last_actions_token_in_eth_pair(token_ticker, uni_wrapper, graphql_client_uni)
        context.bot.send_message(chat_id=chat_id, text=latest_actions_pretty, disable_web_page_preview=True, parse_mode='html')
    else:
        context.bot.send_message(chat_id=chat_id, text="Please use the format /last_actions TOKEN_TICKER")


def get_trending(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    res = zerorpc_client_data_aggregator.view_trending()
    context.bot.send_message(chat_id=chat_id, text=res)


def main():
    updater = Updater(TELEGRAM_KEY, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('niceme', send_meme_to_chat))
    # dp.add_handler(CommandHandler('links', get_links))
    dp.add_handler(CommandHandler('nicefarmingguide', stake_command))
    dp.add_handler(CommandHandler('howtoslippage', how_to_slippage))
    dp.add_handler(CommandHandler('supplycap', get_supply_cap))
    dp.add_handler(CommandHandler('biz', get_biz))
    dp.add_handler(CommandHandler('twitter', get_last_tweets))
    dp.add_handler(MessageHandler(Filters.photo, handle_new_image))
    dp.add_handler(CommandHandler('nice', get_price_nice))
    # dp.add_handler(CommandHandler('help', get_help))
    dp.add_handler(CommandHandler('chart', get_chart_price_pyplot))
    dp.add_handler(CommandHandler('chartSupply', get_chart_supply_pyplot))
    # dp.add_handler(CommandHandler('startBiz', callback_timer, pass_job_queue=True))
    dp.add_handler(CommandHandler('delete_meme_secret', delete_meme))
    dp.add_handler(CommandHandler('candlestick', get_candlestick_pyplot))
    # dp.add_handler(CommandHandler('airdropinfo', get_airdrop))
    dp.add_handler(CommandHandler('david', get_random_message_david))
    dp.add_handler(CommandHandler('tim', get_random_message_tim))
    dp.add_handler(CommandHandler('schizo', get_random_message_schizo))
    dp.add_handler(CommandHandler('generate_random_david', generate_random_david))
    dp.add_handler(CommandHandler('generate_random_gregg', generate_random_gregg))
    dp.add_handler(CommandHandler('generate_random_mahmoud', generate_random_mahmoud))
    dp.add_handler(CommandHandler('mahmoud', get_random_message_mahmoud))
    dp.add_handler(CommandHandler('generate_random_david_tim_schizo', generate_random_all))
    dp.add_handler(CommandHandler('generate_random_all', generate_random_all_chat))
    dp.add_handler(CommandHandler('generate_random_all_stats', generate_random_all_stats))
    dp.add_handler(CommandHandler('add_ai', add_message_to_ai))
    dp.add_handler(CommandHandler('generate_random_legends', generate_random_legend))
    dp.add_handler(CommandHandler('last_actions', get_latest_actions))
    dp.add_handler(CommandHandler('trending', get_trending))
    dp.add_handler(CommandHandler('convert', do_convert))
    dp.add_handler(CallbackQueryHandler(refresh_chart, pattern='refresh_chart(.*)'))
    dp.add_handler(CallbackQueryHandler(refresh_price, pattern='r_p_(.*)'))
    dp.add_handler(CallbackQueryHandler(delete_message, pattern='delete_message'))
    dp.add_handler(MessageHandler(Filters.text, log_message))
    RepeatedTimer(15, log_current_price_rot_per_usd)
    RepeatedTimer(60, log_current_supply)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

commands = """
nice - Display some $NICE price
niceme - Give me a random meme
twitter - Fetch tweets talking about §NICE
biz - Get 4chan biz threads talking about $NICE
nicefarmingguide - Guide to farming with tegrity
supplycap - How NICE are we
add_meme - Add a meme to the common memes folder
chart - Display a (simple) price chart
chartsupply - Display a graph of the supply cap
candlestick - Candlestick chart 
add_ai - add message to ai
"""