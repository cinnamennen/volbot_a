#!/usr/bin/env python


"""dirtytalk.py - Package dirty talk into pickle objects"""

import cPickle


def main():
    dirtytalk = set(['I need you right now.',
                'I get so turned on just thinking about the last time we made love.',
                "I feel so weak and turned on at the same time when I'm in your arms.",
                "I want to give you the best oral sex you've ever had.",
                "I just want to be used by you tonight. Can I be your personal toy?",
                "I can't wait until we're both alone so that I can blow your mind.",
                "I want to tie you up later and have my way with you.",
                "Feeling you on top of me and in control is the hottest thing ever!",
                "I was thinking about you last night before I went to sleep...",
                "I love how you look at me when we're together, it's so hot!",
                "Just lie back and let me take care of business.",
                "I love feeling you in my hands!",
                "Keeping going, keep going!",
                "I love how you taste.",
                "Don't stop, it feels so good!",
                "You dominating me is such a turn on.",
                "I want you to take control of me!",
                "Stop talking and just do me!",
                "I never want you to stop, it feels so good.",
                "I want you to finish wherever you like."])

    with open('dirtytalk.txt', 'w') as f:
        cPickle.dump(dirtytalk, f)

if __name__ == '__main__':
    main()
