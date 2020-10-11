import time
import libraries.commands_util as commands_util
import libraries.graphs_util as graphs_util
import libraries.scrap_websites_util as scrap_websites_util
import libraries.requests_util as requests_util
import libraries.util as util
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackContext

last_time_checked_4chan = 0


def send_candlestick_pyplot(token, charts_path, k_days, k_hours, t_from, t_to):
    print("requesting coin " + token + " from " + str(k_days) + " days and " + str(k_hours) + " hours")

    path = charts_path + token + '.png'
    last_price = graphs_util.print_candlestick(token, t_from, t_to, path)

    callback_message = 'refresh_chart_' + "h:" + str(k_hours) + "d:" + str(k_days) + "t:" + token
    callback_message_1_w = 'refresh_chart_' + "h:" + str(0) + "d:" + str(7) + "t:" + token
    callback_message_1_d = 'refresh_chart_' + "h:" + str(0) + "d:" + str(1) + "t:" + token
    callback_message_1_m = 'refresh_chart_' + "h:" + str(0) + "d:" + str(30) + "t:" + token
    callback_message_2_h = 'refresh_chart_' + "h:" + str(2) + "d:" + str(0) + "t:" + token
    header = [InlineKeyboardButton('Refresh ⌛', callback_data=callback_message)]
    button_list_chart = [[
                            header
                         ],
                         [
                            InlineKeyboardButton('Chart 2 h', callback_data=callback_message_2_h),
                            InlineKeyboardButton('Chart 1 day', callback_data=callback_message_1_d),
                            InlineKeyboardButton('Chart 1 week', callback_data=callback_message_1_w),
                            InlineKeyboardButton('Chart 1 month', callback_data=callback_message_1_m)
                         ]]
    # menu = util.build_menu(button_list_chart, 4, header_buttons=header)
    reply_markup_chart = InlineKeyboardMarkup(button_list_chart)
    msg_time = " last " + str(k_days) + " day(s) " if k_days > 0 else " last " + str(k_hours) + " hour(s) "
    ad = util.get_ad()
    message = "<code>" + token + msg_time + "$" + str(last_price)[0:10] + "\n" + ad + "</code>"

    return message, path, reply_markup_chart


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


def get_price(contract, pair_contract, graphclient_eth, graphclient_uni, name, decimals):
    (derivedETH_7d, token_price_7d_usd, derivedETH_1d, token_price_1d_usd, derivedETH_now,
     token_price_now_usd) = requests_util.get_price_raw(graphclient_eth, graphclient_uni, contract)

    supply_cap_token = requests_util.get_supply_cap_raw(contract, decimals)
    supply_cat_pretty = str(util.number_to_beautiful(round(supply_cap_token)))
    market_cap = util.number_to_beautiful(int(float(supply_cap_token) * token_price_now_usd))

    vol_24h = requests_util.get_volume_24h(graphclient_uni, pair_contract)
    var_7d = - int(((token_price_7d_usd - token_price_now_usd) / token_price_7d_usd) * 100) if token_price_7d_usd > token_price_now_usd else int(((token_price_now_usd - token_price_7d_usd) / token_price_7d_usd) * 100)
    var_1d = - int(((token_price_1d_usd - token_price_now_usd) / token_price_1d_usd) * 100) if token_price_1d_usd > token_price_now_usd else int(((token_price_now_usd - token_price_1d_usd) / token_price_1d_usd) * 100)

    var_7d_str = "+" + str(var_7d) + "%" if var_7d > 0 else str(var_7d) + "%"
    var_1d_str = "+" + str(var_1d) + "%" if var_1d > 0 else str(var_1d) + "%"

    vol_24_pretty = util.number_to_beautiful(vol_24h)

    msg_vol_24 = "\nVol 24H = $" + vol_24_pretty if vol_24_pretty != "0" else ""

    holders = requests_util.get_number_holder_token(contract)
    ad = util.get_ad()
    message = "<code>" + name \
              + "\nETH: Ξ" + str(derivedETH_now)[0:10] \
              + "\nUSD: $" + str(token_price_now_usd)[0:10] \
              + "\n24H:  " + var_1d_str \
              + "\n7D :  " + var_7d_str \
              + "\n" \
              + msg_vol_24 \
              + "\nS.  Cap = " + supply_cat_pretty \
              + "\nM.  Cap = $" + market_cap \
              + "\nHolders = " + str(holders) \
              + "\n" + ad + "</code>"
    return message


def get_help(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    message = """<b>How to use the bot:</b>
<b>/price:</b> display the price of the token as well as relevant metrics
<b>/chart:</b> display a candlestick chart of the last 24 hours.
To show the last 14 days: use /chart 14 d
To show the last 7 hours: use /chart 7 h
A problem? Suggestion? Want this bot for your token? -> contact @ rotted_ben"""
    context.bot.send_message(chat_id=chat_id, text=message, parse_mode='html')
