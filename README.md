python requirements: flask, tweepy

To run:

python top10.py to start the flask service on 127.0.0.1:5000

open top10.html in a web browser and press the go button!

I’m storing tweets with the following in mind:

It’s important to us to basically know how many times a tweet has appeared in every minute from 1...n before the current time, so the data structures on the backend are as follows:

- A deque with a dictionaries of tweet id -> count for how many tweets of that id showed up during each minute.  Each dictionary is stored at index 1..n where the index is how many minutes before the current time it showed up.  Basically at each index there’s a bucket full of tweets that occurred during that minute and how often they occurred.
- The best data structure to find the “best n” items is a heap, so I’m using a heap to keep track of the actual count of occurences of tweets in the rolling window.  Each heap node holds on to the tweet id, number of occurences, text and author.  The heap is sorted by number of occurences, so we can easily get the x most popular tweets.
- I have an additional map of tweet id -> reference of node in heap to facilitate quickly finding the appropriate nodes to modify counts and/or remove the nodes when needed.

There’s a thread that spawns that every 60 seconds removes a bucket from the deque (the oldest one) and adds an empty bucket to the front.  Basically, every minute we rotate the deque and drop the oldest bucket, which should have items that are no longer within n minutes.  Once we do this, we also have to remove / decrement the appropriate nodes in the heap, which the map of tweet id -> reference to node makes easy.  If subtracting the amount of occurences in the bucket for the oldest minute leaves the node with 0 occurrences in the heap, we can delete the node and reheapify.

Next there’s a simple flask app to serve the data and provide two simple REST endpoints for starting up the service and retrieving the top N tweets.

