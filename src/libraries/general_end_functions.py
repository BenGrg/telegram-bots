import time
import libraries.commands_util as commands_util
import libraries.graphs_util as graphs_util
import libraries.scrap_websites_util as scrap_websites_util
import libraries.requests_util as requests_util
import libraries.util as util
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

last_time_checked_4chan = 0


def send_candlestick_pyplot(context: CallbackContext, token, charts_path, k_days, k_hours, t_from, t_to, chat_id):
    print("requesting coin " + token + " from " + str(k_days) + " days and " + str(k_hours) + " hours")
    path = charts_path + token + '.png'
    last_price = graphs_util.print_candlestick(token, t_from, t_to, path)
    message = "<code>" + token + " $" + str(last_price)[0:10] + "\nYour ad here -> @ rotted_ben" + "</code>"
    context.bot.send_photo(chat_id=chat_id,
                           photo=open(path, 'rb'),
                           caption=message,
                           parse_mode="html")


# sends the current biz threads
def get_biz_no_meme(update: Update, context: CallbackContext, re_4chan):
    chat_id = update.message.chat_id
    threads_ids = scrap_websites_util.get_biz_threads(re_4chan)

    base_url = "boards.4channel.org/biz/thread/"
    message = """Plz go bump the /biz/ threads:
"""
    for thread_id in threads_ids:
        excerpt = thread_id[2] + " | " + thread_id[1]
        message += base_url + str(thread_id[0]) + " -- " + excerpt[0: 100] + "[...] \n"
    if not threads_ids:
        print("sent reminder 4chan /biz/")
        meme_caption = "There hasn't been a Rotten /biz/ thread for a while. Plz go make one."
        context.bot.send_message(chat_id=chat_id, text=meme_caption)
    else:
        context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True)


def get_price(update: Update, context: CallbackContext, contract, pair_contract, graphclient_eth, graphclient_uni, name, decimals):
    (derivedETH_7d, rot_price_7d_usd, derivedETH_1d, rot_price_1d_usd, derivedETH_now,
     rot_price_now_usd) = requests_util.get_price_raw(graphclient_eth, graphclient_uni, contract)

    supply_cap_token = requests_util.get_supply_cap_raw(contract, decimals)
    supply_cat_pretty = str(util.number_to_beautiful(round(supply_cap_token)))
    market_cap = util.number_to_beautiful(int(float(supply_cap_token) * rot_price_now_usd))

    vol_24h = requests_util.get_volume_24h(graphclient_uni, pair_contract)
    var_7d = 0  # int(((rot_price_now_usd - rot_price_7d_usd) / rot_price_now_usd) * 100)
    var_1d = int(((rot_price_now_usd - rot_price_1d_usd) / rot_price_now_usd) * 100)

    var_7d_str = "+" + str(var_7d) + "%" if var_7d > 0 else str(var_7d) + "%"
    var_1d_str = "+" + str(var_1d) + "%" if var_1d > 0 else str(var_1d) + "%"

    vol_24_pretty = util.number_to_beautiful(vol_24h)

    msg_vol_24 = "\nVol 24H = $" + vol_24_pretty if vol_24_pretty != "0" else ""

    holders = requests_util.get_number_holder_token(contract)

    message = ""
    if str(rot_price_now_usd)[0:10] == "8559.66467":
        message = message + "Parts of Uniswap info seems down. Price might be outdated.\n"

        # + "\nETH: Ξ" + str(derivedETH_now)[0:10]
        # + "\nUSD: $" + str(rot_price_now_usd)[0:10]

    message = message + "<code>" + name \
              + "\nETH: Ξ" + str(derivedETH_now)[0:10] \
              + "\nUSD: $" + str(rot_price_now_usd)[0:10] \
              + "\n24H:  " + var_1d_str \
              + "\n7D :  " + var_7d_str \
              + "\n" \
              + msg_vol_24 \
              + "\nS.  Cap = " + supply_cat_pretty \
              + "\nM.  Cap = $" + market_cap \
              + "\nHolders = " + str(holders) + "</code>"
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=message, parse_mode='html')
