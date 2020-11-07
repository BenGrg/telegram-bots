import datetime
import time

import pandas as pd
import libraries.requests_util as requests_util
import libraries.util as util
import numpy as np
import plotly.io as pio
import pprint

INCREASING_COLOR = '#228B22'
DECREASING_COLOR = '#FF0000'




def __moving_average(interval, window_size=10):
    window = np.ones(int(window_size)) / float(window_size)
    return np.convolve(interval, window, 'same')


def __bbands(price, window_size=10, num_of_std=5):
    price_pd = pd.DataFrame(price)
    rolling_mean = price_pd.rolling(window=window_size).mean()
    rolling_std = price_pd.rolling(window=window_size).std()
    upper_band = rolling_mean + (rolling_std * num_of_std)
    lower_band = rolling_mean - (rolling_std * num_of_std)
    return rolling_mean, upper_band, lower_band


# Visualisation inspired by https://chart-studio.plotly.com/~jackp/17421/plotly-candlestick-chart-in-python/#/
# Huge thanks to the author!
def __process_and_write_candlelight(dates, openings, closes, highs, lows, volumes, file_path, token_name):
    data = [dict(
        type='candlestick',
        open=openings,
        high=highs,
        low=lows,
        close=closes,
        x=dates,
        yaxis='y2',
        name='GS',
        increasing=dict(line=dict(color=INCREASING_COLOR)),
        decreasing=dict(line=dict(color=DECREASING_COLOR)),
    )]

    # max_price = max(highs)
    # max_y = max_price + max_price * 0.2
    # min_price = min(lows)
    # min_y = max(0, min_price - min_price * 0.2)

    layout = dict()

    fig = dict(data=data, layout=layout)

    fig['layout'] = dict()
    fig['layout']['plot_bgcolor'] = 'rgb(250, 250, 250)'
    fig['layout']['autosize'] = False
    fig['layout']['width'] = 1600
    fig['layout']['height'] = 900
    fig['layout']['xaxis'] = dict(rangeslider=dict(visible=False))
    fig['layout']['yaxis'] = dict(domain=[0, 0.19], showticklabels=True, title='Volume ($)', side='right')
    fig['layout']['yaxis2'] = dict(domain=[0.2, 1], title=token_name + ' price ($)', side='right')
    fig['layout']['showlegend'] = False
    fig['layout']['margin'] = dict(t=15, b=15, r=15, l=15)

    # bb_avg, bb_upper, bb_lower = __bbands(closes)
    #
    # fig['data'].append(dict(x=dates, y=bb_upper[0].to_list(), type='scatter', yaxis='y2',
    #                         line=dict(width=1),
    #                         marker=dict(color='#ccc'), hoverinfo='none',
    #                         legendgroup='Bollinger Bands', name='Bollinger Bands'))
    #
    #
    # fig['data'].append(dict(x=dates, y=bb_lower[0].to_list(), type='scatter', yaxis='y2',
    #                         line=dict(width=1),
    #                         marker=dict(color='#ccc'), hoverinfo='none',
    #                         legendgroup='Bollinger Bands', showlegend=False))

    mv_y = __moving_average(closes)
    mv_x = list(dates)

    # Clip the ends
    mv_x = mv_x[5:-5]
    mv_y = mv_y[5:-5]

    fig['data'].append(dict(x=mv_x, y=mv_y, type='scatter', mode='lines',
                            line=dict(width=2),
                            marker=dict(color='#E377C2'),
                            yaxis='y2', name='Moving Average'))

    colors_volume = []

    for i in range(len(closes)):
        if i != 0:
            if closes[i] > closes[i - 1]:
                colors_volume.append(INCREASING_COLOR)
            else:
                colors_volume.append(DECREASING_COLOR)
        else:
            colors_volume.append(DECREASING_COLOR)

    fig['data'].append(dict(x=dates, y=volumes,
                            marker=dict(color=colors_volume),
                            type='bar', yaxis='y', name='Volume'))

    pio.write_image(fig=fig, file=file_path, scale=3)


# t_from and t_to should be numbers, not strings
def __calculate_resolution_from_time(t_from, t_to):
    delta = round(t_to - t_from)
    if delta < 6 * 3600:
        return 1
    elif delta < 13 * 3600:
        return 5
    elif delta < 24 * 3600:
        return 15
    elif delta < 24 * 3600 * 7 + 100:
        return 30
    else:
        return 60


def __preprocess_gecko_charts_data(values):

    prices_and_t = values['prices']
    volumes_and_t = values['total_volumes']
    prices = [float(x) for x in prices_and_t[1]]
    times = [float(x) for x in prices_and_t[0]]
    volumes = [float(x) for x in volumes_and_t[1]]

    times_from_chartex = [datetime.datetime.fromtimestamp(round(x)) for x in times]

    pprint.pprint("times:")
    pprint.pprint(times)
    pprint.pprint("prices:")
    pprint.pprint(prices)
    pprint.pprint("volumes:")
    pprint.pprint(volumes)

    closes = prices
    opens = prices
    highs = prices
    lows = prices
    volumes = volumes

    date_list = pd.date_range(start=times_from_chartex[0], end=times_from_chartex[-1]).to_pydatetime().tolist()


    return (date_list, opens, closes, highs, lows, volumes)


def __preprocess_chartex_data(values, resolution):
    times_from_chartex = [datetime.datetime.fromtimestamp(round(x)) for x in values['t']]

    closes = [float(x) for x in values['c']]
    opens = [float(x) for x in values['o']]
    highs = [float(x) for x in values['h']]
    lows = [float(x) for x in values['l']]
    volumes = [float(x) for x in values['v']]

    frequency = str(resolution) + "min"
    date_list = pd.date_range(start=times_from_chartex[0], end=times_from_chartex[-1],
                              freq=frequency).to_pydatetime().tolist()

    last_index = 0
    missing_dates_count = 0
    for date in date_list:
        if date in times_from_chartex:
            index = times_from_chartex.index(date)
            last_index = index + missing_dates_count
            # check if "too big" value and remove it in this case
            if index == 0:
                if highs[0] > highs[1] * 2:
                    # print("reducing highs index 0")
                    highs[0] = min(highs[1] * 3, highs[0] / 2)
                if lows[0] < lows[1] / 2:
                    # print("increasing lows index 0")
                    lows[0] = max(lows[0] * 2, lows[1] / 2)
            else:
                if highs[index] > highs[index - 1] * 2 and highs[index] > highs[index + 1] * 2:
                    # print("reducing highs")
                    highs[index] = (highs[index - 1] + highs[index + 1])
                if lows[index] < lows[index - 1] / 2 and lows[index] < lows[index + 1] / 2:
                    # print("increasing lows: from " + str(lows[index]) + ' to ' + str(min(lows[index - 1] - lows[index], lows[index + 1] - lows[index])))
                    lows[index] = min(lows[index - 1] - lows[index], lows[index + 1] - lows[index])
        else:
            index = last_index + 1
            price = closes[index - 1]
            closes.insert(index, price)
            highs.insert(index, price)
            lows.insert(index, price)
            opens.insert(index, price)
            volumes.insert(index, 0.0)
            last_index = last_index + 1
            missing_dates_count += 1
    return (date_list, opens, closes, highs, lows, volumes)


# t_from and t_to should be int epoch second
# return the last price
def print_candlestick(token, t_from, t_to, file_path):
    resolution = __calculate_resolution_from_time(t_from, t_to)

    if token == "eth" or token == "ETH" or token == "weth" or token == "WETH" or token == "ethereum" or token == "Ethereum":
        values = requests_util.get_gecko_chart("ethereum", t_from, t_to).json()
        print(str(values))
        (date_list, opens, closes, highs, lows, volumes) = __preprocess_gecko_charts_data(values)
    else:
        values = requests_util.get_graphex_data(token, resolution, t_from, t_to).json()
        (date_list, opens, closes, highs, lows, volumes) = __preprocess_chartex_data(values, resolution)

    __process_and_write_candlelight(date_list, opens, closes, highs, lows, volumes, file_path, token)
    return closes[-1]

#
# def test_print_candlestick(token, t_from, t_to, resolution=1):
#     t_1 = time.time_ns() // 1000000
#     values = requests_util.get_graphex_data(token, resolution, t_from, t_to).json()
#     t_2 = time.time_ns() // 1000000
#     (date_list, opens, closes, highs, lows, volumes) = __preprocess_chartex_data(values, resolution)
#     print("0 = " + str(date_list[0]))
#     print("last = " + str(date_list[-1]))
#     print("size = " + str(len(date_list)))
#     time_between = date_list[-1] - date_list[0]
#     print("diff: " + str(time_between))
#
#     # __process_and_write_candlelight(date_list, opens, closes, highs, lows, volumes, file_path, token)
#     print("time chartex query = " + str(t_2 - t_1))
#
#
# def main():
#     token = "ROT"
#     t_to = int(time.time())
#     t_from = 0
#     print_candlestick(token, t_from, t_to, "testaaa2.png")
#
#
# if __name__ == '__main__':
#     main()
