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

# Authentication
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

def getUser(tweet):
    
    userCreator = api.get_user(tweet.get("user").get("id"))._json
    r.rpush("users", json.dumps(userCreator))
        
    for userMention in tweet.get("entities").get("user_mentions"):
         user = api.get_user(userMention.get("id"))._json
         r.rpush("users", json.dumps(user))
         
    if(tweet.get("in_reply_to_user_id_str") != None):     
        r.rpush("users", json.dumps(api.get_user(tweet.get("in_reply_to_user_id_str"))._json))
       
def saveToRedis(tweet, replyed=False):
    if(tweet._json.get("lang") == "en"):
        if(replyed):
            print("reply : " + str(tweet.id))
        else:
            print(tweet.id)
        
        getUser(tweet._json)
        
        #initialTweet = tweet.retweeted_status
        if(tweet._json.get("retweeted_status") != None):
            getUser(tweet.retweeted_status._json)
            print("retweet")
            r.rpush("tweets", json.dumps(tweet.retweeted_status._json))
        
        r.rpush("tweets", json.dumps(tweet._json))

        if(tweet._json.get("in_reply_to_status_id") != None):
            saveToRedis(api.get_status(tweet._json.get("in_reply_to_status_id")), replyed = True)
           

#override tweepy.StreamListener to add logic to on_status
class MyStreamListener(tweepy.StreamListener):

    def on_status(self, tweet):
        saveToRedis(tweet)
        


myStreamListener = MyStreamListener()
myStream = tweepy.Stream(auth = api.auth, listener=myStreamListener)
print(sys.argv[1])
myStream.filter(track=[sys.argv[1]])

