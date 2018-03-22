import tweepy
import redis
import json
import sys
import datetime


# The user credential variables to access Twitter API
consumer_key = "IeS7hfJwaiLId2g2PVRX2E9tM"
consumer_secret = "KdjWrnHmQIbrH9Fgv64ylIE1INGtMxtU1xOD2pNKZbQgQXiYwg"
access_token = "2876464845-vjWa7E4M8w4WKqPdhPMe85gcXYP6VUufHnXszPb"
access_token_secret = "DYnslsp3bdNIb6YflKJxTDQ8UGHkDUL8Wz1TDallMKifi"

non_bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0xfffd)

# Get redis db
r = redis.Redis(host='localhost', port=6379, db=0)

# Authentication to the twitter api
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

# Get and save all users in relation with a tweet :
#       - The Creator of the tweet
#       - All users mentioned in the tweet
#       - The user to whom the creator replied to
def getUser(tweet):

    # Get user creator of the tweet
    userCreator = api.get_user(tweet.get("user").get("id"))._json
    r.rpush("users", json.dumps(userCreator))

    # Get all users mentioned in the tweet
    for userMention in tweet.get("entities").get("user_mentions"):
         user = api.get_user(userMention.get("id"))._json
         r.rpush("users", json.dumps(user))

    # The user to whom the creator replied to is exist
    if(tweet.get("in_reply_to_user_id_str") != None):     
        r.rpush("users", json.dumps(api.get_user(tweet.get("in_reply_to_user_id_str"))._json))

# Get and save all tweet and users in relation with it :
def saveToRedis(tweet, replyed=False):
    if(tweet._json.get("lang") == "en"):
        if(replyed):
            print("reply : " + str(tweet.id))
        else:
            print(tweet.id)
        
        getUser(tweet._json)
        
        # If it's a retweet, get and save the original tweet
        if(tweet._json.get("retweeted_status") != None):
            getUser(tweet.retweeted_status._json)
            print("retweet")
            r.rpush("tweets", json.dumps(tweet.retweeted_status._json))
        
        r.rpush("tweets", json.dumps(tweet._json))

        # If the tweet it's a reply of a tweet, get all chain of replied tweet
        if(tweet._json.get("in_reply_to_status_id") != None):
            saveToRedis(api.get_status(tweet._json.get("in_reply_to_status_id")), replyed = True)
           

# Stream to aspire tweet in real time
class MyStreamListener(tweepy.StreamListener):

    def on_status(self, tweet):
        saveToRedis(tweet)

myStreamListener = MyStreamListener()
myStream = tweepy.Stream(auth = api.auth, listener=myStreamListener)
print(sys.argv[1])
myStream.filter(track=[sys.argv[1]])

