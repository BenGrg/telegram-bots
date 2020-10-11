import locale
import sys
import os

BASE_PATH = os.environ.get('BASE_PATH')
sys.path.insert(1, BASE_PATH + '/telegram-bots/src')

import time
from datetime import datetime
import pprint
import os.path
import re

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

import libraries.graphs_util as graphs_util
import libraries.general_end_functions as general_end_functions
import libraries.commands_util as commands_util

# ENV FILES
TELEGRAM_KEY = os.environ.get('CHART_TELEGRAM_KEY')

# log_file
charts_path = BASE_PATH + 'log_files/chart_bot/'

default_token = 'ROT'

locale.setlocale(locale.LC_ALL, 'en_US')


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


def get_candlestick(update: Update, context: CallbackContext):
    general_end_functions.get_candlestick_pyplot(update, context, default_token, charts_path)


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
        print("requesting coin " + token + " from " + str(k_days) + " days and " + str(k_hours) + " hours")
        path = charts_path + token + '.png'
        last_price = graphs_util.print_candlestick(token, t_from, t_to, path)
        message = "<code>" + token + " $" + str(last_price) + "</code>"
        context.bot.send_photo(chat_id=chat_id,
                               photo=open(path, 'rb'),
                               caption=message,
                               parse_mode="html")


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
"""
