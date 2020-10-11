import time
import libraries.commands_util as commands_util
import libraries.graphs_util as graphs_util
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext


def send_candlestick_pyplot(update: Update, context: CallbackContext, default_token, charts_path):
    chat_id = update.message.chat_id

    query_received = update.message.text.split(' ')

    time_type, k_hours, k_days, tokens = commands_util.check_query(query_received, default_token)
    t_to = int(time.time())
    t_from = t_to - (k_days * 3600 * 24) - (k_hours * 3600)

    if isinstance(tokens, list):
        for token in tokens:
            print("requesting coin " + token + " from " + str(k_days) + " days and " + str(k_hours) + " hours")
            path = charts_path + token + '.png'
            last_price = graphs_util.print_candlestick(token, t_from, t_to, path)
            message = "<code>" + token + " $" + str(last_price)[0:10] + "\nYour ad here -> @ rotted_ben" + "</code>"
            context.bot.send_photo(chat_id=chat_id,
                                   photo=open(path, 'rb'),
                                   caption=message,
                                   parse_mode="html")
    else:
        print("requesting coin " + tokens + " from " + str(k_days) + " days and " + str(k_hours) + " hours")
        path = charts_path + tokens + '.png'
        last_price = graphs_util.print_candlestick(tokens, t_from, t_to, path)
        message = "<code>" + tokens + " $" + str(last_price)[0:10] + "\nYour ad here -> @ rotted_ben" + "</code>"
        context.bot.send_photo(chat_id=chat_id,
                               photo=open(path, 'rb'),
                               caption=message,
                               parse_mode="html")
