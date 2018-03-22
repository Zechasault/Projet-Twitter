import redis
import ast
import json
import sys
import re
from pypher import Pypher
from nltk.tokenize import RegexpTokenizer
from nltk.stem.porter import PorterStemmer
from gensim import corpora, models
import gensim
from py2neo import Graph, Node, Relationship, authenticate
import copy

authenticate("hobby-pbjiefemnffigbkeelplibal.dbs.graphenedb.com:24780", "api", "b.tdzWlcyhOmi7.hCtKdrqtkO4fMZue")
g = Graph("https://hobby-pbjiefemnffigbkeelplibal.dbs.graphenedb.com:24780", bolt = False)

non_bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0xfffd)

# Get redis db
r = redis.Redis(host='localhost', port=6379, db=0)

tokenizer = RegexpTokenizer(r'\w+')

# create French stop words list
en_stop =["re", "s","t","m","d","a","u","about","above","after","again","against","all","am","an","and","any","are","aren't","as","at","be","because","been","before","being","below","between","both","but","by","can't","cannot","could","couldn't","did","didn't","do","does","doesn't","doing","don't","down","during","each","few","for","from","further","had","hadn't","has","hasn't","have","haven't","having","he","he'd","he'll","he's","her","here","here's","hers","herself","him","himself","his","how","how's","i","i'd","i'll","i'm","i've","if","in","into","is","isn't","it","it's","its","itself","let's","me","more","most","mustn't","my","myself","no","nor","not","of","off","on","once","only","or","other","ought","our","ours","ourselves","out","over","own","same","shan't","she","she'd","she'll","she's","should","shouldn't","so","some","such","than","that","that's","the","their","theirs","them","themselves","then","there","there's","these","they","they'd","they'll","they're","they've","this","those","through","to","too","under","until","up","very","was","wasn't","we","we'd","we'll","we're","we've","were","weren't","what","what's","when","when's","where","where's","which","while","who","who's","whom","why","why's","with","won't","would","wouldn't","you","you'd","you'll","you're","you've","your","yours","yourself","yourselves"]

# Create p_stemmer of class PorterStemmer
p_stemmer = PorterStemmer()


tweets = {}
users = {}
retweets = {}
directUser = []
indirectUser = []
ldamodels =[]
corp = []

def dbToDictTweets():
    for tweet in r.lrange ("tweets", 0, -1):
        tweetJson = json.loads(tweet.decode('utf-8'))
        if(tweetJson.get("retweeted_status") != None) :
            retweets[tweetJson.get("id")] = tweetJson
        else:
            tweets[tweetJson.get("id")] = tweetJson
    

def dbToDictUsers():
    for user in r.lrange ("users", 0, -1):
        userJson = json.loads(user.decode('utf-8'))
        users[userJson.get("id")] = userJson
    
      
def go():
    dbToDictTweets()
    dbToDictUsers()
    addUserToNeo4j()
    addTweetToNeo4j()
    
def addUserToNeo4j() :
    
    for userid, userJson in users.items():
        
        u = {}
        
        u["id"] = userJson.get("id_str")
        u["url"] = userJson.get("url")
        u["name"] = userJson.get("name")
        u["screen_name"] = userJson.get("screen_name")
        u["location"] = userJson.get("location")
        u["time_zone"] = userJson.get("time_zone")
        u["lang"] = userJson.get("lang")
        u["description"] = userJson.get("description")
        u["created_at"] = userJson.get("created_at")
        u["profile_image_url_https"] = userJson.get("profile_image_url_https")
        u["profile_image_url"] = userJson.get("profile_image_url")
        u["verified"] = userJson.get("verified")
        u["favourites_count"] = userJson.get("favourites_count")
        u["statuses_count"] = userJson.get("statuses_count")
        u["friends_count"] = userJson.get("friends_count")
        u["followers_count"] = userJson.get("followers_count")
        u["listed_count"] = userJson.get("listed_count")

        u_data = json.loads(json.dumps(u))
            
        query = """
        WITH {json} as json
        MERGE (u:User {id:json.id})
        SET u = json
        """
        
        g.run(query, json=u_data)

def addTweetToNeo4j() :
    retweet = []
    for tweetid, tweetJson in tweets.items():
        t = {}
        t["tweet"] = {}
        t["tweet"]["id"] = tweetJson.get("id_str")
        t["tweet"]["text"] = tweetJson.get("text")
        t["tweet"]["created_at"] = tweetJson.get("created_at")
        #t["tweet"]["place"] = tweetJson.get("place")
        t["tweet"]["source"] = tweetJson.get("source")
        t["tweet"]["favorite_count"] = tweetJson.get("favorite_count")
        t["tweet"]["retweet_count"] = tweetJson.get("retweet_count")
        #t["tweet"]["coordinates"] = tweetJson.get("coordinates")
        #t["tweet"]["geo"] = tweetJson.get("geo")
        t["tweet"]["in_reply_to_user_id"] = tweetJson.get("in_reply_to_user_id_str")
        t["tweet"]["userid"] = tweetJson.get("user").get("id_str")
        
        t["language"] = tweetJson.get("lang")
        
        t_data = json.loads(json.dumps(t))
            
        query = """
        WITH {json} as json
        MERGE (t:Tweet {id:json.tweet.id})
        SET t = json.tweet
        MERGE (l:Language {code:json.language})
        MERGE (u:User{id:json.tweet.userid})
        MERGE (t)-[:WRITTEN_IN]->(l)
        MERGE (t)-[:TWEETED_BY]->(u)
        """
        
        g.run(query, json=t_data)

        for hastag in tweetJson.get("entities").get("hashtags"):
            ht = {}
            ht["hashtag"] = hastag.get("text").lower()
            ht["tweetid"]   = tweetJson.get("id_str")
            
            ht_data = json.loads(json.dumps(ht))
            
            query_ht = """
            WITH {json} as json
            MERGE (t:Tweet {id:json.tweetid})
            MERGE (h:Hashtag {text:json.hashtag})
            MERGE (t)-[:TAGS]->(h)
            """
        
            g.run(query_ht, json=ht_data)

        for url in tweetJson.get("entities").get("urls"):
            ut = {}
            ut["url"] = url.get("expanded_url")
            ut["tweetid"]   = tweetJson.get("id_str")
            
            ut_data = json.loads(json.dumps(ut))
            
            query_ut = """
            WITH {json} as json
            MERGE (t:Tweet {id:json.tweetid})
            MERGE (l:Url {text:json.url})
            MERGE (t)-[:LINKS]->(l)
            """
        
            g.run(query_ut, json=ut_data)

        for userMention in tweetJson.get("entities").get("user_mentions"):
            mt = {}
            mt["userid"] = userMention.get("id_str")
            mt["tweetid"] = tweetJson.get("id_str")
            
            mt_data = json.loads(json.dumps(mt))
            
            query_mt = """
            WITH {json} as json
            MERGE (t:Tweet {id:json.tweetid})
            MERGE (u:User  {id:json.userid})
            MERGE (t)-[:MENTIONS]->(u)
            """
        
            g.run(query_mt, json=mt_data)

        if(tweetJson.get("in_reply_to_status_id_str") != None and tweetJson.get("in_reply_to_status_id") in tweets):
            urt = {}
            urt["replyedtweetid"] = tweetJson.get("in_reply_to_status_id_str")
            urt["tweetid"] = tweetJson.get("id_str")
            
            urt_data = json.loads(json.dumps(urt))
            
            query_urt = """
            WITH {json} as json
            MERGE (t1:Tweet {id:json.tweetid})
            MERGE (t2:Tweet  {id:json.replyedtweetid})
            MERGE (t1)-[:REPLIED_TO]->(t2)
            """
        
            g.run(query_urt, json = urt_data)
            
        addStemToNeo4j(tweetJson)
        
    for tweetid, tweetJson in retweets.items():
        t = {}
        t["userid"] = tweetJson.get("user").get("id_str")
        t["tweetid"] = tweetJson.get("retweeted_status").get("id_str")
        
        t_data = json.loads(json.dumps(t))
            
        query = """
        WITH {json} as json
        MERGE (t:Tweet {id:json.tweetid})
        MERGE (u:User{id:json.userid})
        MERGE (t)-[:RETWEETED_BY]->(u)
        """
        
        g.run(query, json=t_data)
    
def addRetweet():
    for tweetid, tweetJson in retweets.items():
        t = {}
        t["userid"] = tweetJson.get("user").get("id_str")
        t["tweetid"] = tweetJson.get("retweeted_status").get("id_str")
        
        t_data = json.loads(json.dumps(t))
            
        query = """
        WITH {json} as json
        MERGE (t:Tweet {id:json.tweetid})
        MERGE (u:User{id:json.userid})
        MERGE (t)-[:RETWEETED_BY]->(u)
        """
        
        g.run(query, json=t_data)
        
def addJustStem():
    for tweetid, tweetJson in tweets.items():
        addStemToNeo4j(tweetJson)
        
def addStemToNeo4j(tweetContent):
    
    #remove urls
    text = re.sub(r'\w+:\/{2}[\d\w-]+(\.[\d\w-]+)*(?:(?:\/[^\s/]*))*', '', tweetContent.get("text").translate(non_bmp_map))
    
    # clean and tokenize text
    raw = " ".join(filter(lambda x:x[0]!='@', text.lower().split()))
    raw = " ".join(filter(lambda x:x[0]!='#', raw.split()))
    
    tokens = tokenizer.tokenize(raw)
    
    # remove stop words from tokens
    stopped_tokens = [text for text in tokens if not text in en_stop]

    # stem tokens
    stemmed_tokens = [p_stemmer.stem(text) for text in stopped_tokens]

    for stem in stemmed_tokens:
        t = {}
        t["stem"] = stem
        t["tweetid"] = tweetContent.get("id_str")
        
        t_data = json.loads(json.dumps(t))
            
        query = """
        WITH {json} as json
        MERGE (t:Tweet {id:json.tweetid})
        MERGE (s:Stem{text:json.stem})
        MERGE (t)-[:HAS]->(s)
        """
        
        g.run(query, json=t_data)
    
    


        
