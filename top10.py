from flask import Flask
from flask import jsonify
import tweepy, time
import datetime
import threading
from collections import deque
from collections import defaultdict
import heapq

consumer_key = "OlKSkE0X8DBiKyeTCt3MIGRVk"
consumer_secret = "z1NU4pyxI8qVFGidcfR41jS25Ssh5UlstD1w423uM2a4Dl71mg"
access_token = "808159748-WeA5CJGnohMfDE4NtJfUbU9zprUOITsBRKgyw3bE"
access_token_secret = "481fXjgukUQkUraXtWTYtA0KOHfgCaqy10nI41gQES9kh"

# We're going to use this list to keep track of tweets that occured every 1...n minutes before now.
# The index of an item in the list is a dictionary with tweet_id:occurences that happened index minutes ago
tweets_since = deque()

tweet_count_heap = []

tweet_heap_map = {}

tweetWorker = None

# remove i'th node from heap by swapping with last element and reheapifying
def remove_from_heap(h, i):
    h[i] = h[-1]
    heapq.heappop(h)

    # O(n) runtime, but if we want O(log n) for this particular case
    # we can go copy the _siftup function from python source
    heapq.heapify(h)


# Initiate the set of buckets for tweets that occured 1...n minutes
# We'll call this if the user inputs a different value for n
def initiate_tweets_since(elements):
    tweets_since_len = len(tweets_since)
    if tweets_since_len < elements:
        for i in range(elements - tweets_since_len):
            tweets_since.append(defaultdict(lambda: 0))
    elif tweets_since_len > elements:
        # pop the right number of tweets off the end
        for i in range(tweets_since_len):
            remove_tweets(tweets_since.pop())

def remove_tweets(tweets):
    for tweet_id, count in tweets.items():
        heap_node = tweet_heap_map[tweet_id]
        heap_node.count -= count
        if heap_node.count <= 0:
            remove_from_heap(tweet_count_heap, tweet_count_heap.index(heap_node))


def start_rotate_tweets():
    threading.Timer(60, rotate_tweets_since).start()

def rotate_tweets_since():
    # every 60 seconds, get rid of the last element in the deque and add a new one to the front
    # effectively shifting all elements over so tweets that were 1 minute old are now 2 minutes old, etc
    tweets_since.appendleft(defaultdict(lambda: 0))

    # take this and remove it from the heap, using the references we have to the appropriate nodes
    tweets_to_remove = tweets_since.pop()
    remove_tweets(tweets_to_remove)
    start_rotate_tweets()

class TweetCount:
    def __init__ (self, tweet_id, count, author, text):
        self.tweet_id = tweet_id
        self.count = count
        self.author = author
        self.text = text
    def __lt__ (self, other):
        return self.count < other.count
    def __gt__ (self, other):
        return self.count > other.count
    def __eq__ (self, other):
        return self.count == other.count
    def __ne__ (self, other):
        return self.count != other.count
    def serialize (self):
        return {
            "tweet_id" : self.tweet_id,
            "count" : self.count,
            "author" : self.author,
            "text" : self.text,
        }

class Top10Listener(tweepy.StreamListener):
    def __init__ (self, last_n_mins):
        super(Top10Listener, self).__init__()
        self.last_n_mins = last_n_mins

    def on_status(self, status):
        try:
            # we only care if the tweet is a retweet
            if hasattr(status, "retweeted_status"):
                parent_tweet = status.retweeted_status
                text = parent_tweet.text.encode("utf-8")
                text = text.replace("\n", "\\n")
                user = parent_tweet.author.screen_name.encode("utf-8")
                tweet_time = parent_tweet.created_at
                tweet_id = parent_tweet.id
                now = datetime.datetime.utcnow()
                mins_since_now = int((now - tweet_time).total_seconds() / 60)

                if mins_since_now <= self.last_n_mins - 1:
                    curr = tweets_since[mins_since_now][tweet_id]
                    tweets_since[mins_since_now][tweet_id] = curr + 1
                    if tweet_id in tweet_heap_map:
                        tweet_heap_map[tweet_id].count += 1
                    else:
                        t = TweetCount(tweet_id, 1, user, text)
                        heapq.heappush(tweet_count_heap, t)
                        tweet_heap_map[tweet_id] = t
        except Exception, e:
            print e
            return False

    def on_error(self, status):
        print "Error: " + str(status)
        return True

    def on_timeout(self):
        print "Timeout..."
        time.sleep(10)
        return True


# start getting tweets since n minute ago
def start_gathering_tweets(n):
    auth = tweepy.auth.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    stream = tweepy.Stream(auth, Top10Listener(n))
    initiate_tweets_since(n)
    rotate_tweets_since()
    print "Starting to gather tweets since the last %d minutes." % n
    global tweetWorker
    if tweetWorker is None:
        tweetWorker = threading.Thread(target=stream.sample)
        tweetWorker.start()

# from https://blog.skyred.fi/articles/better-crossdomain-snippet-for-flask.html
# because i hate cors
from datetime import timedelta
from flask import make_response, request, current_app
from functools import update_wrapper


def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers
            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            h['Access-Control-Allow-Credentials'] = 'true'
            h['Access-Control-Allow-Headers'] = \
                "Origin, X-Requested-With, Content-Type, Accept, Authorization"
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator


app = Flask(__name__)

@app.route("/start/<int:n>")
@crossdomain(origin='*')
def start(n):
    start_gathering_tweets(n)
    return "Gathering started."

@app.route("/top/<int:n>")
@crossdomain(origin='*')
def top(n):
    return jsonify(tweets=[tweet.serialize() for tweet in heapq.nlargest(n, tweet_count_heap)])

if __name__ == "__main__":
    app.run()


