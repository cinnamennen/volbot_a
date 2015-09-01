import cPickle
import praw

try:
    with open('curses.txt', 'r') as f:
        curses = cPickle.load(f)
except:
    curses = set()

r = praw.Reddit(user_agent='Curse Scraper')

posts = r.get_subreddit('traditionalcurses').get_hot(limit=100)

for post in posts:
    curse = post.title
    if curse not in curses:
        print curse
        curses.add(curse)

with open('curses.txt', 'w') as f:
    cPickle.dump(curses, f)
