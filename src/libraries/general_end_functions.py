import time
import libraries.commands_util as commands_util
import libraries.graphs_util as graphs_util
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext


def send_candlestick_pyplot(context: CallbackContext, token, charts_path, k_days, k_hours, t_from, t_to, chat_id):
    print("requesting coin " + token + " from " + str(k_days) + " days and " + str(k_hours) + " hours")
    path = charts_path + token + '.png'
    last_price = graphs_util.print_candlestick(token, t_from, t_to, path)
    message = "<code>" + token + " $" + str(last_price)[0:10] + "\nYour ad here -> @ rotted_ben" + "</code>"
    context.bot.send_photo(chat_id=chat_id,
                           photo=open(path, 'rb'),
                           caption=message,
                           parse_mode="html")
