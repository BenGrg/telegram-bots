import re


def get_from_query(query_received):
    time_type = query_received[2]
    try:
        time_start = int(query_received[1])
    except ValueError:
        time_start = int(re.search(r'\d+', query_received[1]).group())
        time_type = query_received[1][-1]

    if time_start < 0:
        time_start = - time_start
    k_hours = 0
    k_days = 0
    if time_type == 'h' or time_type == 'H':
        k_hours = time_start
    if time_type == 'd' or time_type == 'D':
        k_days = time_start
    return time_type, k_hours, k_days


def check_query(query_received, default_token):
    time_type, k_hours, k_days, tokens = 'd', 0, 1, default_token
    if len(query_received) == 1:
        pass
    elif len(query_received) == 2:
        tokens = [query_received[1]]
    elif len(query_received) == 3:
        time_type, k_hours, k_days = get_from_query(query_received)
    elif len(query_received) == 4:
        time_type, k_hours, k_days = get_from_query(query_received)
        tokens = [query_received[-1]]
    else:
        time_type, k_hours, k_days = get_from_query(query_received)
        tokens = query_received[3:]
    return time_type, k_hours, k_days, tokens
