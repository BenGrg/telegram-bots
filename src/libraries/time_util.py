from datetime import datetime
from dateparser import parse


def get_duration(then, now=datetime.now(), interval="default"):
    # Returns a duration as specified by variable interval
    # Functions, except totalDuration, returns [quotient, remainder]

    duration = then - now  # For build-in functions
    duration_in_s = duration.total_seconds()

    def years():
        return divmod(duration_in_s, 31536000)  # Seconds in a year=31536000.

    def days(seconds=None):
        return divmod(seconds if seconds is not None else duration_in_s, 86400)  # Seconds in a day = 86400

    def hours(seconds=None):
        return divmod(seconds if seconds is not None else duration_in_s, 3600)  # Seconds in an hour = 3600

    def minutes(seconds=None):
        return divmod(seconds if seconds is not None else duration_in_s, 60)  # Seconds in a minute = 60

    def seconds(seconds=None):
        if seconds is not None:
            return divmod(seconds, 1)
        return duration_in_s

    def total_duration():
        y = years()
        d = days(y[1])  # Use remainder to calculate next variable
        h = hours(d[1])
        m = minutes(h[1])
        s = seconds(m[1])

        return "Time between dates: {} years, {} days, {} hours, {} minutes and {} seconds".format(int(y[0]), int(d[0]),
                                                                                                   int(h[0]), int(m[0]),
                                                                                                   int(s[0]))

    def total_duration_simple():
        y = years()
        d = days(y[1])  # Use remainder to calculate next variable
        h = hours(d[1])
        m = minutes(h[1])
        s = seconds(m[1])

        message = ""
        if int(y[0]) != 0:
            message += str(int(y[0])) + " year(s) "
        if int(d[0]) != 0:
            message += str(int(d[0])) + " day(s) "
        if int(h[0]) != 0:
            message += str(int(h[0])) + " hour(s) "
        if int(m[0]) != 0:
            message += str(int(m[0])) + " minute(s) "
        if int(s[0]) != 0:
            message += str(int(s[0])) + " s"
        message = message.replace(")", "),")
        return message

    return {
        'years': int(years()[0]),
        'days': int(days()[0]),
        'hours': int(hours()[0]),
        'minutes': int(minutes()[0]),
        'seconds': int(seconds()),
        'simple': total_duration_simple(),
        'default': total_duration()
    }[interval]


def parse_date(date_to_parse):
    return parse(date_to_parse)


def get_time_diff(date_to_parse):
    parsed_date = parse_date(date_to_parse)
    return get_duration(parsed_date)