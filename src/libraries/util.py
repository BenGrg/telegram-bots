import locale
import os
import random
import decimal
import hashlib
from binascii import hexlify

BASE_PATH = os.environ.get('BASE_PATH')

from datetime import datetime

# convert int to nice string: 1234567 => 1 234 567
def number_to_beautiful(nbr):
    return locale.format_string("%d", nbr, grouping=True).replace(",", " ")


def get_ad():
    ads_file_path = BASE_PATH + "ads/chart_ads.txt"
    with open(ads_file_path) as f:
        content = f.readlines()
    # you may also want to remove whitespace characters like `\n` at the end of each line
    content = [x.strip() for x in content]
    return random.choice(content)


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


# create a new context for this task
ctx = decimal.Context()

# 20 digits should be enough for everyone :D
ctx.prec = 20


def float_to_str(f):
    """
    Convert the given float to a string,
    without resorting to scientific notation
    """
    d1 = ctx.create_decimal(repr(f))
    return format(d1, 'f')


def pretty_number(num):
    if round(num) > 10:
        res = number_to_beautiful(round(num))
    elif 0.01 < num < 10.01:
        res = float_to_str(num)[0:5]
    else:
        res = float_to_str(num)[0:10]
    return res


def create_href_str(url, message):
    return "<a href=\"" + url + "\">" + message + "</a>"


def get_random_string(length):
    # put your letters in the following string
    sample_letters = 'abcdefghi'
    result_str = ''.join((random.choice(sample_letters) for i in range(length)))
    return result_str


def create_and_send_vote(ticker, method, username, zerorpc_client):
    now_ts = round(datetime.now().timestamp())
    id_vote = random.randint(0, 1000000000000)
    hex_username = hexlify(username.encode())
    hashed_username = hashlib.sha512(hex_username + hex_username).hexdigest()
    vote = (id_vote, hashed_username, now_ts, ticker.upper(), method)
    zerorpc_client.add_vote(vote)
