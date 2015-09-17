#!/usr/bin/env python


"""curses.py - Fetch curses from reddit.com/r/traditionalcurses"""


import cPickle
import praw

def main():
    try:
        with open('curses.txt', 'r') as f:
            curses = cPickle.load(f)
    except:
        curses = set()

    r = praw.Reddit(user_agent='Curse Scraper for Volchat IRC Channel: for use by the University of Tennessee IRC Channel.')

    posts = r.get_subreddit('traditionalcurses').get_hot(limit=100)

    for post in posts:
        curse = post.title
        if curse not in curses:
            print curse
            curses.add(curse)

    badwords = ['reddit', 'traditionalcurses', 'upvote', 'downvote']
    bads = []
    for c in curses:
        for b in badwords:
            if b.lower() in c.lower():
                bads.append(c)
    [curses.remove(b) for b in bads]

    with open('curses.txt', 'w') as f:
        cPickle.dump(curses, f)

if __name__ == '__main__':
    main()
