import time
import libraries.commands_util as commands_util
import libraries.graphs_util as graphs_util
import libraries.scrap_websites_util as scrap_websites_util
import libraries.requests_util as requests_util
import libraries.util as util
from libraries.util import float_to_str
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackContext
from libraries.images import Ocr
import csv
import datetime
import matplotlib
import matplotlib.dates
import matplotlib.pyplot as plt
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
    refresh_button = InlineKeyboardButton('Refresh ⌛', callback_data=callback_message)
    delete_button = InlineKeyboardButton('Delete 🗑️', callback_data='delete_message')
    button_list_chart = [[
                            refresh_button,
                            delete_button
                         ],
                         [
                            InlineKeyboardButton('2 hours', callback_data=callback_message_2_h),
                            InlineKeyboardButton('1 day', callback_data=callback_message_1_d),
                            InlineKeyboardButton('1 week', callback_data=callback_message_1_w),
                            InlineKeyboardButton('1 month', callback_data=callback_message_1_m)
                         ]]
    # menu = util.build_menu(button_list_chart, 4, header_buttons=header)
    reply_markup_chart = InlineKeyboardMarkup(button_list_chart)
    msg_time = " " + str(k_days) + " day(s) " if k_days > 0 else " last " + str(k_hours) + " hour(s) "
    print(float_to_str(last_price))
    ad = util.get_ad()
    message = "<b>" + token + "</b>" + msg_time + "<code>$" + float_to_str(last_price)[0:10] + "</code>\n" + ad + ""

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

    vol_24h = requests_util.get_volume_24h(graphclient_uni, contract)
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

    holders = requests_util.get_number_holder_token(contract)
    holders_str = "\nHolders = " + str(holders) if holders != -1 else ""
    ad = util.get_ad()
    message = "<code>" + name \
              + "\nETH: Ξ" + float_to_str(derivedETH_now)[0:10] \
              + "\nUSD: $" + float_to_str(token_price_now_usd)[0:10] \
              + "\n24H:  " + var_1d_str \
              + "\n7D :  " + var_7d_str \
              + "\n" \
              + msg_vol_24 \
              + "\nS.  Cap = " + supply_cat_pretty \
              + "\nM.  Cap = $" + market_cap \
              + holders_str \
              + "</code>" \
              + "\n" + ad
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


def download_image(update: Update, context: CallbackContext, path):
    image = context.bot.getFile(update.message.photo[-1])
    file_id = str(image.file_id)
    print("file_id: " + file_id)
    img_path = path + file_id + ".png"
    image.download(img_path)
    return img_path


def ocr_image(update: Update, context: CallbackContext, tmp_path):
    img_path = download_image(update, context, tmp_path)
    ocr = Ocr(img_path)
    text_in_ocr = ocr.start_ocr().replace('\n', ' ')
    print("recognized text = " + text_in_ocr)
    return text_in_ocr


def strp_date(raw_date):
    return datetime.datetime.strptime(raw_date, '%m/%d/%Y,%H:%M:%S')


def print_chart_supply(dates_raw, supply_t1, name_t1, supply_t2, name_t2, chart_path):
    dates = matplotlib.dates.date2num(dates_raw)
    cb91_green = '#47DBCD'
    plt.style.use('dark_background')

    matplotlib.rcParams.update({'font.size': 22})
    f = plt.figure(figsize=(16, 9))

    ax = f.add_subplot(111)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    plot1 = ax.plot_date(dates, supply_t1, 'r', label=name_t1)

    ax2 = ax.twinx()
    ax2.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    plot2 = ax2.plot_date(dates, supply_t2, cb91_green, label=name_t2)

    ax.set_ylabel(name_t1)
    ax2.set_ylabel(name_t2)

    plots = plot1 + plot2
    labs = [l.get_label() for l in plots]
    ax.legend(plots, labs, bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left',
              ncol=2, mode="expand", borderaxespad=0.)

    plt.gcf().autofmt_xdate()
    plt.savefig(chart_path, bbox_inches='tight', dpi=300)
    plt.close(f)


def send_supply_two_pyplot(supply_file_path, k_days, k_hours, name_t1, name_t2, chart_path):

    list_time_supply = []

    with open(supply_file_path, newline='') as csv_file:
        reader = csv.reader(csv_file, delimiter=' ', quotechar='|')
        for row in reader:
            list_time_supply.append((row[0], row[1], row[2]))

    now = datetime.datetime.utcnow()

    filtered_values = [x for x in list_time_supply if
                       now - strp_date(x[0]) < datetime.timedelta(days=k_days, hours=k_hours)]

    dates_pure = keep_dates(filtered_values)
    supply_t1 = [int(round(float(value[1]))) for value in filtered_values]
    supply_t2 = [int(round(float(value[2]))) for value in filtered_values]

    print_chart_supply(dates_pure, supply_t1, name_t1, supply_t2, name_t2, chart_path)
    current_t1_str = supply_t1[-1]
    current_t2_str = supply_t2[-1]
    return current_t1_str, current_t2_str


# util for get_chart_pyplot
def keep_dates(values_list):
    dates_str = []
    for values in values_list:
        dates_str.append(values[0])

    dates_datetime = []
    for date_str in dates_str:
        date_datetime = datetime.datetime.strptime(date_str, '%m/%d/%Y,%H:%M:%S')
        dates_datetime.append(date_datetime)
    return dates_datetime


def convert_to_usd_raw(amount, currency_ticker, graphqlclient_uni, graphqlclient_eth):
    contract_from_ticker = requests_util.get_token_contract_address(currency_ticker)
    (derivedETH_7d, token_price_7d_usd, derivedETH_1d, token_price_1d_usd, derivedETH_now,
     token_price_now_usd) = requests_util.get_price_raw(graphqlclient_eth, graphqlclient_uni, contract_from_ticker)
    total = amount * token_price_now_usd
    return total


def convert_to_usd(amount, currency_ticker, graphqlclient_uni, graphqlclient_eth):
    total = convert_to_usd_raw(amount, currency_ticker, graphqlclient_uni, graphqlclient_eth)
    total_str = util.number_to_beautiful(round(total)) if round(total) > 10 else float_to_str(total)
