# -*- coding: utf-8 -*-
# Name: Zhenchao Gan
# Email: zhgan@eng.ucsd.edu
# PID: A53092819
from pyspark import SparkContext
sc = SparkContext()
# coding: utf-8

# # Homework 2
#
# In this homework, we are going to play with Twitter data.
#
# The data is represented as rows of of [JSON](https://en.wikipedia.org/wiki/JSON#Example) strings.
# It consists of [tweets](https://dev.twitter.com/overview/api/tweets), [messages](https://dev.twitter.com/streaming/overview/messages-types), and a small amount of broken data (cannot be parsed as JSON).
#
# For this homework, we will only focus on tweets and ignore all other messages.
#
# # UPDATES
#
# ## Announcement
#
# **We changed the test files size and the corresponding file paths.**
#
# In order to avoid long waiting queue, we decided to limit the input files size for the Playground submissions. Please read the following files to get the input file paths:
#     * 1GB test: `../Data/hw2-files-1gb.txt`
#     * 5GB test: `../Data/hw2-files-5gb.txt`
#     * 20GB test: `../Data/hw2-files-20gb.txt`
#
# **We updated the json parsing section of this notebook.**
#
# Python built-in json library is too slow. In our experiment, 70% of the total running time is spent on parsing tweets. Therefore we recommend using [ujson](https://pypi.python.org/pypi/ujson) instead of json. It is at least 15x faster than the built-in json library according to our tests.
#
#
# ## Important Reminders
#
# 1. The tokenizer in this notebook contains UTF-8 characters. So the first line of your `.py` source code must be `# -*- coding: utf-8 -*-` to define its encoding. Learn more about this topic [here](https://www.python.org/dev/peps/pep-0263/).
# 2. The input files (the tweets) contain UTF-8 characters. So you have to correctly encode your input with some function like `lambda text: text.encode('utf-8')`.
# 3. `../Data/hw2-files-<param>` may contain multiple lines, one line for one input file. You can use a single textFile call to read multiple files: `sc.textFile(','.join(files))`.
# 4. The input file paths in `../Data/hw2-files-<param>` contains trailing spaces (newline etc.), which may confuse HDFS if not removed.
# 5. Your program will be killed if it cannot finish in 5 minutes. The running time of last 100 submissions (yours and others) can be checked at the "View last 100 jobs" tab. For your information, here is the running time of our solution:
#    * 1GB test:  53 seconds,
#    * 5GB test:  60 seconds,
#    * 20GB test: 114 seconds.
#
#
#
#
#
# ## Tweets
#
# A tweet consists of many data fields. [Here is an example](https://gist.github.com/arapat/03d02c9b327e6ff3f6c3c5c602eeaf8b). You can learn all about them in the Twitter API doc. We are going to briefly introduce only the data fields that will be used in this homework.
#
# * `created_at`: Posted time of this tweet (time zone is included)
# * `id_str`: Tweet ID - we recommend using `id_str` over using `id` as Tweet IDs, becauase `id` is an integer and may bring some overflow problems.
# * `text`: Tweet content
# * `user`: A JSON object for information about the author of the tweet
#     * `id_str`: User ID
#     * `name`: User name (may contain spaces)
#     * `screen_name`: User screen name (no spaces)
# * `retweeted_status`: A JSON object for information about the retweeted tweet (i.e. this tweet is not original but retweeteed some other tweet)
#     * All data fields of a tweet except `retweeted_status`
# * `entities`: A JSON object for all entities in this tweet
#     * `hashtags`: An array for all the hashtags that are mentioned in this tweet
#     * `urls`: An array for all the URLs that are mentioned in this tweet
#
#
# ## Data source
#
# All tweets are collected using the [Twitter Streaming API](https://dev.twitter.com/streaming/overview).
#
#
# ## Users partition
#
# Besides the original tweets, we will provide you with a Pickle file, which contains a partition over 452,743 Twitter users. It contains a Python dictionary `{user_id: partition_id}`. The users are partitioned into 7 groups.

# # Part 0: Load data to a RDD

# The tweets data is stored on AWS S3. We have in total a little over 1 TB of tweets. We provide 10 MB of tweets for your local development. For the testing and grading on the homework server, we will use different data.
#
# ## Testing on the homework server
# In the Playground, we provide three different input sizes to test your program: 1 GB, 10 GB, and 100 GB. To test them, read files list from `../Data/hw2-files-1gb.txt`, `../Data/hw2-files-5gb.txt`, `../Data/hw2-files-20gb.txt`, respectively.
#
# For final submission, make sure to read files list from `../Data/hw2-files-final.txt`. Otherwise your program will receive no points.
#
# ## Local test
#
# For local testing, read files list from `../Data/hw2-files.txt`.
# Now let's see how many lines there are in the input files.
#
# 1. Make RDD from the list of files in `hw2-files.txt`.
# 2. Mark the RDD to be cached (so in next operation data will be loaded in memory)
# 3. call the `print_count` method to print number of lines in all these files
#
# It should print
# ```
# Number of elements: 2193
# ```

# In[1]:

def print_count(rdd):
    print 'Number of elements:', rdd.count()


# In[2]:

# Your code here
with open('../Data/hw2-files-final.txt') as f:
    files = [l.strip() for l in f.readlines()]
contents = sc.textFile(','.join(files)).map(lambda x:x.encode('utf-8')).cache()
print_count(contents)


# # Part 1: Parse JSON strings to JSON objects

# Python has built-in support for JSON.
#
# **UPDATE:** Python built-in json library is too slow. In our experiment, 70% of the total running time is spent on parsing tweets. Therefore we recommend using [ujson](https://pypi.python.org/pypi/ujson) instead of json. It is at least 15x faster than the built-in json library according to our tests.

# In[3]:

import ujson

json_example = '''
    {
    "id": 1,
    "name": "A green door",
    "price": 12.50,
    "tags": ["home", "green"]
    }
    '''

json_obj = ujson.loads(json_example)
json_obj


# ## Broken tweets and irrelevant messages
#
# The data of this assignment may contain broken tweets (invalid JSON strings). So make sure that your code is robust for such cases.
#
# In addition, some lines in the input file might not be tweets, but messages that the Twitter server sent to the developer (such as [limit notices](https://dev.twitter.com/streaming/overview/messages-types#limit_notices)). Your program should also ignore these messages.
#
# *Hint:* [Catch the ValueError](http://stackoverflow.com/questions/11294535/verify-if-a-string-is-json-in-python)
#
#
# (1) Parse raw JSON tweets to obtain valid JSON objects. From all valid tweets, construct a pair RDD of `(user_id, text)`, where `user_id` is the `id_str` data field of the `user` dictionary (read [Tweets](#Tweets) section above), `text` is the `text` data field.

# In[4]:

import ujson

def safe_parse(raw_json):
    try:
        json_object = ujson.loads(raw_json)
    except ValueError, e:
        return []
    if 'user' not in json_object.keys():
        return []
    return [json_object]

# your code here
usertweets = contents.flatMap(lambda x: safe_parse(x)).map(lambda x:(x['user']['id_str'], x['text'])).cache()


# (2) Count the number of different users in all valid tweets (hint: [the `distinct()` method](https://spark.apache.org/docs/latest/programming-guide.html#transformations)).
#
# It should print
# ```
# The number of unique users is: 2083
# ```

# In[5]:

def print_users_count(count):
    print 'The number of unique users is:', count


# In[6]:



# your code here
users = usertweets.map(lambda x:x[0]).distinct()
print_users_count(users.count())


# # Part 2: Number of posts from each user partition

# Load the Pickle file `../Data/users-partition.pickle`, you will get a dictionary which represents a partition over 452,743 Twitter users, `{user_id: partition_id}`. The users are partitioned into 7 groups. For example, if the dictionary is loaded into a variable named `partition`, the partition ID of the user `59458445` is `partition["59458445"]`. These users are partitioned into 7 groups. The partition ID is an integer between 0-6.
#
# Note that the user partition we provide doesn't cover all users appear in the input data.

# (1) Load the pickle file.

# In[7]:

# your code here
import pickle
mypickle = pickle.load( open( "../Data/users-partition.pickle" ) )


# (2) Count the number of posts from each user partition
#
# Count the number of posts from group 0, 1, ..., 6, plus the number of posts from users who are not in any partition. Assign users who are not in any partition to the group 7.
#
# Put the results of this step into a pair RDD `(group_id, count)` that is sorted by key.

# In[8]:

# your code here

def help1(x):
    uid = x[0]
    if uid in mypickle:
        return (mypickle[uid], 1)
    return (7,1)

result = usertweets.map(lambda x: help1(x))              .reduceByKey(lambda a, b: a + b)              .sortByKey()


# (3) Print the post count using the `print_post_count` function we provided.
#
# It should print
#
# ```
# Group 0 posted 81 tweets
# Group 1 posted 199 tweets
# Group 2 posted 45 tweets
# Group 3 posted 313 tweets
# Group 4 posted 86 tweets
# Group 5 posted 221 tweets
# Group 6 posted 400 tweets
# Group 7 posted 798 tweets
# ```

# In[9]:

def print_post_count(counts):
    for group_id, count in counts:
        print 'Group %d posted %d tweets' % (group_id, count)


# In[10]:

# your code here
print_post_count(result.collect())


# # Part 3:  Tokens that are relatively popular in each user partition

# In this step, we are going to find tokens that are relatively popular in each user partition.
#
# We define the number of mentions of a token $t$ in a specific user partition $k$ as the number of users from the user partition $k$ that ever mentioned the token $t$ in their tweets. Note that even if some users might mention a token $t$ multiple times or in multiple tweets, a user will contribute at most 1 to the counter of the token $t$.
#
# Please make sure that the number of mentions of a token is equal to the number of users who mentioned this token but NOT the number of tweets that mentioned this token.
#
# Let $N_t^k$ be the number of mentions of the token $t$ in the user partition $k$. Let $N_t^{all} = \sum_{i=0}^7 N_t^{i}$ be the number of total mentions of the token $t$.
#
# We define the relative popularity of a token $t$ in a user partition $k$ as the log ratio between $N_t^k$ and $N_t^{all}$, i.e.
#
# \begin{equation}
# p_t^k = \log \frac{C_t^k}{C_t^{all}}.
# \end{equation}
#
#
# You can compute the relative popularity by calling the function `get_rel_popularity`.

# (0) Load the tweet tokenizer.

# In[11]:

# %load happyfuntokenizing.py
#!/usr/bin/env python

"""
    This code implements a basic, Twitter-aware tokenizer.
    
    A tokenizer is a function that splits a string of text into words. In
    Python terms, we map string and unicode objects into lists of unicode
    objects.
    
    There is not a single right way to do tokenizing. The best method
    depends on the application.  This tokenizer is designed to be flexible
    and this easy to adapt to new domains and tasks.  The basic logic is
    this:
    
    1. The tuple regex_strings defines a list of regular expression
    strings.
    
    2. The regex_strings strings are put, in order, into a compiled
    regular expression object called word_re.
    
    3. The tokenization is done by word_re.findall(s), where s is the
    user-supplied string, inside the tokenize() method of the class
    Tokenizer.
    
    4. When instantiating Tokenizer objects, there is a single option:
    preserve_case.  By default, it is set to True. If it is set to
    False, then the tokenizer will downcase everything except for
    emoticons.
    
    The __main__ method illustrates by tokenizing a few examples.
    
    I've also included a Tokenizer method tokenize_random_tweet(). If the
    twitter library is installed (http://code.google.com/p/python-twitter/)
    and Twitter is cooperating, then it should tokenize a random
    English-language tweet.
    
    
    Julaiti Alafate:
    I modified the regex strings to extract URLs in tweets.
    """

__author__ = "Christopher Potts"
__copyright__ = "Copyright 2011, Christopher Potts"
__credits__ = []
__license__ = "Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License: http://creativecommons.org/licenses/by-nc-sa/3.0/"
__version__ = "1.0"
__maintainer__ = "Christopher Potts"
__email__ = "See the author's website"

######################################################################

import re
import htmlentitydefs

######################################################################
# The following strings are components in the regular expression
# that is used for tokenizing. It's important that phone_number
# appears first in the final regex (since it can contain whitespace).
# It also could matter that tags comes after emoticons, due to the
# possibility of having text like
#
#     <:| and some text >:)
#
# Most imporatantly, the final element should always be last, since it
# does a last ditch whitespace-based tokenization of whatever is left.

# This particular element is used in a couple ways, so we define it
# with a name:
emoticon_string = r"""
    (?:
    [<>]?
    [:;=8]                     # eyes
    [\-o\*\']?                 # optional nose
    [\)\]\(\[dDpP/\:\}\{@\|\\] # mouth
    |
    [\)\]\(\[dDpP/\:\}\{@\|\\] # mouth
    [\-o\*\']?                 # optional nose
    [:;=8]                     # eyes
    [<>]?
    )"""

# The components of the tokenizer:
regex_strings = (
                 # Phone numbers:
                 r"""
                     (?:
                     (?:            # (international)
                     \+?[01]
                     [\-\s.]*
                     )?
                     (?:            # (area code)
                     [\(]?
                     \d{3}
                     [\-\s.\)]*
                     )?
                     \d{3}          # exchange
                     [\-\s.]*
                     \d{4}          # base
                     )"""
                 ,
                 # URLs:
                 r"""http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"""
                 ,
                 # Emoticons:
                 emoticon_string
                 ,
                 # HTML tags:
                 r"""<[^>]+>"""
                 ,
                 # Twitter username:
                 r"""(?:@[\w_]+)"""
                 ,
                 # Twitter hashtags:
                 r"""(?:\#+[\w_]+[\w\'_\-]*[\w_]+)"""
                 ,
                 # Remaining word types:
                 r"""
                     (?:[a-z][a-z'\-_]+[a-z])       # Words with apostrophes or dashes.
                     |
                     (?:[+\-]?\d+[,/.:-]\d+[+\-]?)  # Numbers, including fractions, decimals.
                     |
                     (?:[\w_]+)                     # Words without apostrophes or dashes.
                     |
                     (?:\.(?:\s*\.){1,})            # Ellipsis dots.
                     |
                     (?:\S)                         # Everything else that isn't whitespace.
                     """
                 )

######################################################################
# This is the core tokenizing regex:

word_re = re.compile(r"""(%s)""" % "|".join(regex_strings), re.VERBOSE | re.I | re.UNICODE)

# The emoticon string gets its own regex so that we can preserve case for them as needed:
emoticon_re = re.compile(regex_strings[1], re.VERBOSE | re.I | re.UNICODE)

# These are for regularizing HTML entities to Unicode:
html_entity_digit_re = re.compile(r"&#\d+;")
html_entity_alpha_re = re.compile(r"&\w+;")
amp = "&amp;"

######################################################################

class Tokenizer:
    def __init__(self, preserve_case=False):
        self.preserve_case = preserve_case
    
    def tokenize(self, s):
        """
            Argument: s -- any string or unicode object
            Value: a tokenize list of strings; conatenating this list returns the original string if preserve_case=False
            """
        # Try to ensure unicode:
        try:
            s = unicode(s)
        except UnicodeDecodeError:
            s = str(s).encode('string_escape')
            s = unicode(s)
        # Fix HTML character entitites:
        s = self.__html2unicode(s)
        # Tokenize:
        words = word_re.findall(s)
        # Possible alter the case, but avoid changing emoticons like :D into :d:
        if not self.preserve_case:
            words = map((lambda x : x if emoticon_re.search(x) else x.lower()), words)
        return words

    def tokenize_random_tweet(self):
        """
            If the twitter library is installed and a twitter connection
            can be established, then tokenize a random tweet.
            """
        try:
            import twitter
        except ImportError:
            print "Apologies. The random tweet functionality requires the Python twitter library: http://code.google.com/p/python-twitter/"
        from random import shuffle
        api = twitter.Api()
        tweets = api.GetPublicTimeline()
        if tweets:
            for tweet in tweets:
                if tweet.user.lang == 'en':
                    return self.tokenize(tweet.text)
        else:
            raise Exception("Apologies. I couldn't get Twitter to give me a public English-language tweet. Perhaps try again")

def __html2unicode(self, s):
    """
        Internal metod that seeks to replace all the HTML entities in
        s with their corresponding unicode characters.
        """
            # First the digits:
            ents = set(html_entity_digit_re.findall(s))
                if len(ents) > 0:
                    for ent in ents:
                        entnum = ent[2:-1]
                            try:
                                entnum = int(entnum)
                                    s = s.replace(ent, unichr(entnum))
                                        except:
                                            pass
                                                # Now the alpha versions:
                                                ents = set(html_entity_alpha_re.findall(s))
                                                    ents = filter((lambda x : x != amp), ents)
                                                        for ent in ents:
                                                            entname = ent[1:-1]
                                                                try:
                                                                    s = s.replace(ent, unichr(htmlentitydefs.name2codepoint[entname]))
                                                                        except:
                                                                            pass
                                                                                s = s.replace(amp, " and ")
                                                                                    return s


# In[12]:

from math import log

tok = Tokenizer(preserve_case=False)

def get_rel_popularity(c_k, c_all):
    return log(1.0 * c_k / c_all) / log(2)


def print_tokens(tokens, gid = None):
    group_name = "overall"
    if gid is not None:
        group_name = "group %d" % gid
    print '=' * 5 + ' ' + group_name + ' ' + '=' * 5
    for t, n in tokens:
        print "%s\t%.4f" % (t.encode('utf-8'), n)
    print


# (1) Tokenize the tweets using the tokenizer we provided above named `tok`. Count the number of mentions for each tokens regardless of specific user group.
#
# Call `print_count` function to show how many different tokens we have.
#
# It should print
# ```
# Number of elements: 8949
# ```

# In[13]:

# your code here
mytokens = usertweets.flatMap(lambda x:tok.tokenize(x[1].encode('utf-8'))).distinct()
print_count(mytokens)


# (2) Tokens that are mentioned by too few users are usually not very interesting. So we want to only keep tokens that are mentioned by at least 100 users. Please filter out tokens that don't meet this requirement.
#
# Call `print_count` function to show how many different tokens we have after the filtering.
#
# Call `print_tokens` function to show top 20 most frequent tokens.
#
# It should print
# ```
# Number of elements: 44
# ===== overall =====
# :	1388.0000
# rt	1237.0000
# .	826.0000
# …	673.0000
# the	623.0000
# trump	582.0000
# to	499.0000
# ,	489.0000
# a	404.0000
# is	376.0000
# in	297.0000
# of	292.0000
# and	288.0000
# for	281.0000
# !	269.0000
# ?	210.0000
# on	195.0000
# i	192.0000
# you	191.0000
# this	190.0000
# ```

# In[14]:


# your code here

inter_usertweets = usertweets.map(lambda x:(x[0], set(tok.tokenize(x[1].encode('utf-8')))))                     .reduceByKey(lambda a, b : a.union(b))                     .mapValues(lambda x: list(x))                     .cache()

tokens = inter_usertweets                     .flatMap(lambda x: x[1])                     .map(lambda word: (word, 1))                     .reduceByKey(lambda a, b: a + b)                     .filter(lambda x:x[1] >= 100)                     .sortBy(lambda x: x[1], False)                     .cache()

#print tokens.take(5)

print_count(tokens)
print_tokens(tokens.take(20))

#flatMap(lambda x:tok.tokenize(x[1]))


# (3) For all tokens that are mentioned by at least 100 users, compute their relative popularity in each user group. Then print the top 10 tokens with highest relative popularity in each user group. In case two tokens have same relative popularity, break the tie by printing the alphabetically smaller one.
#
# **Hint:** Let the relative popularity of a token $t$ be $p$. The order of the items will be satisfied by sorting them using (-p, t) as the key.
#
# It should print
# ```
# ===== group 0 =====
# ...	-3.5648
# at	-3.5983
# hillary	-4.0875
# i	-4.1255
# bernie	-4.1699
# not	-4.2479
# https	-4.2695
# he	-4.2801
# in	-4.3074
# are	-4.3646
#
# ===== group 1 =====
# #demdebate	-2.4391
# -	-2.6202
# &	-2.7472
# amp	-2.7472
# clinton	-2.7570
# ;	-2.7980
# sanders	-2.8838
# ?	-2.9069
# in	-2.9664
# if	-3.0138
#
# ===== group 2 =====
# are	-4.6865
# and	-4.7105
# bernie	-4.7549
# at	-4.7682
# sanders	-4.9542
# that	-5.0224
# in	-5.0444
# donald	-5.0618
# a	-5.0732
# #demdebate	-5.1396
#
# ===== group 3 =====
# #demdebate	-1.3847
# bernie	-1.8480
# sanders	-2.1887
# of	-2.2356
# that	-2.3785
# the	-2.4376
# …	-2.4403
# clinton	-2.4467
# hillary	-2.4594
# be	-2.5465
#
# ===== group 4 =====
# hillary	-3.7395
# sanders	-3.9542
# of	-4.0199
# clinton	-4.0790
# at	-4.1832
# in	-4.2143
# a	-4.2659
# on	-4.2854
# .	-4.3681
# the	-4.4251
#
# ===== group 5 =====
# cruz	-2.3861
# he	-2.6280
# are	-2.7796
# will	-2.7829
# the	-2.8568
# is	-2.8822
# for	-2.9250
# that	-2.9349
# of	-2.9804
# this	-2.9849
#
# ===== group 6 =====
# @realdonaldtrump	-1.1520
# cruz	-1.4532
# https	-1.5222
# !	-1.5479
# not	-1.8904
# …	-1.9269
# will	-2.0124
# it	-2.0345
# this	-2.1104
# to	-2.1685
#
# ===== group 7 =====
# donald	-0.6422
# ...	-0.7922
# sanders	-1.0282
# trump	-1.1296
# bernie	-1.2106
# -	-1.2253
# you	-1.2376
# clinton	-1.2511
# if	-1.2880
# i	-1.2996
# ```

# In[15]:

# your code here

dic = tokens.collectAsMap()

def help4(uid):
    if uid in mypickle:
        groupid = mypickle[uid]
    else:
        groupid = 7
    return groupid

def getKey(item):
    return item[1][1]

def largest10(A):
    B = sorted(A, key=getKey, reverse=True)
    res = []
    for i in range(10):
        res.append(B[i][1])
    return res


interresults = inter_usertweets                     .flatMapValues(lambda x: x)                     .filter(lambda x: x[1] in dic)                     .map(lambda x: ((help4(x[0]), x[1]), 1))                     .reduceByKey(lambda a, b: a + b)                     .map(lambda x: (x[0][0], (x[0][1], get_rel_popularity(x[1], dic[x[0][1]]))))                     .partitionBy(8)                     .glom()                     .collect()

#results = interresults.map(lambda x: largest10(x)).collect()
#print results.take(2)

for i in range(8):
    temp = sc.parallelize(interresults[i]).map(lambda x:x[1])              .sortBy(lambda x: (-x[1], x[0])) 
    print_tokens(temp.take(10), i)


# (4) (optional, not for grading) The users partition is generated by a machine learning algorithm that tries to group the users by their political preferences. Three of the user groups are showing supports to Bernie Sanders, Ted Cruz, and Donald Trump. 
# 
# If your program looks okay on the local test data, you can try it on the larger input by submitting your program to the homework server. Observe the output of your program to larger input files, can you guess the partition IDs of the three groups mentioned above based on your output?

# In[16]:

# Change the values of the following three items to your guesses
users_support = [
                 (-1, "Bernie Sanders"),
                 (-1, "Ted Cruz"),
                 (-1, "Donald Trump")
                 ]

#for gid, candidate in users_support:
#    print "Users from group %d are most likely to support %s." % (gid, candidate)

