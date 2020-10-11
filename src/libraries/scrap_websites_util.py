import time
import requests
from datetime import datetime, timedelta

from twython import TwythonError

how_many_tweets = 5


# scraps /biz/ and returns a list of tuple (threadId, body, title) of threads matching the regex ^rot |rot$| rot |rotten|rotting
def get_biz_threads(re_4chan):
    url = 'https://a.4cdn.org/biz/catalog.json'
    response_json = requests.get(url).json()
    threads_ids = []
    for page in response_json:
        for thread in page['threads']:
            try:
                if 'com' in thread:
                    com = thread['com']
                else:
                    com = ""
                if 'sub' in thread:
                    sub = thread['sub']
                else:
                    sub = ""
            except KeyError:
                print("ERROR")
                pass
            else:
                if re_4chan.search(com) or re_4chan.search(sub):
                    thread_id = thread['no']
                    threads_ids.append((thread_id, com, sub))
    return threads_ids


def format_tweet(tweet):
    tweet_id = tweet['id_str']
    url = "twitter.com/anyuser/status/" + tweet_id
    message = tweet['text'].replace("\n", "").split('https')[0].replace('#', '').replace('@', '')

    time_tweet_creation = tweet['created_at']
    new_datetime = datetime.strptime(time_tweet_creation, '%a %b %d %H:%M:%S +0000 %Y')
    current_time = datetime.utcnow()
    diff_time = current_time - new_datetime
    minutessince = int(diff_time.total_seconds() / 60)

    user = tweet['user']['screen_name']
    message_final = "<a href=\"" + url + "\"><b>" + str(
        minutessince) + " mins ago</b> | " + user + "</a> -- " + message + "\n"
    return message_final


def get_last_tweets(twitter, ticker):
    try:
        results = query_tweets(twitter, ticker)
    except TwythonError:
        time.sleep(0.5)
        results = query_tweets(twitter, ticker)
    message = "<b>Last tweets:</b>\n"
    rest_message = filter_tweets(results)
    if rest_message == "":
        print("empty tweets, fallback")
        rest_message = "Unable to find tweets right now."
    return message + rest_message


def filter_tweets(all_tweets):
    message = ""
    if all_tweets.get('statuses'):
        count = 0
        tweets = all_tweets['statuses']
        for tweet in tweets:
            if "RT " not in tweet['text']:
                if count < how_many_tweets:
                    message = message + format_tweet(tweet)
                    count = count + 1
    return message


def query_tweets(twitter, token):
    return twitter.search(q='$' + token)

