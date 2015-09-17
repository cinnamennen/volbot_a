"""bot.py - Main module for running Volbot"""


# Python Standard Library
import collections
import cPickle
import random
import re
import sys
import time
import traceback
from string import letters, digits, punctuation

# Third Party Libraries
import irc.bot
import markovify
import pymongo
import requests
import urbandict # https://github.com/novel/py-urbandict
import wikipedia

OP_ONLY = 100
VOICE_ONLY = 50
EVERYONE = 0


class Command:
    """Decorator that automatically registers functions as command handlers"""

    def __init__(self, label, perms=OP_ONLY):
        self.label = label
        self.permissions = perms

    def __call__(self, func):
        func.cmd_label = self.label
        func.cmd_perms = self.permissions
        return func


class Trigger:
    """Decorator that automatically registers functions as trigger handlers"""

    def __init__(self, pattern):
        self.pattern = pattern

    def __call__(self, func):
        func.trigger_pattern = self.pattern
        return func


class VolBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667):
        self.log("Connecting to %s:%s as %s" % (server,port,nickname))
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)

        self.channel = channel

        # initialize shakespearean generator
        self.log("Loading shakespearean texts")
        with open('shake2.txt') as f:
            self.shakespeare = markovify.Text(f.read())

        # set up db
        self.log("Connecting to MongoDB")
        client = pymongo.MongoClient("localhost", 27017)
        self.db = client.irc

        # initialize volify markov thing
        self.log("Loading chat history for volify")
        self.load_volify()


        self.ignored = set(['volbot', 'stuessbot'])

        # setup commands and triggers
        self.commands = {}
        self.triggers = []
        self.register_stuff()


    def load_volify(self):
        messages = self.db.messages.find(
            {
                "nick": {"$ne": self._nickname},
                "message": {"$regex": "^[^!].*$"},
            },
            limit=10000, 
            sort=[("time", pymongo.DESCENDING)]
        ) # the idea is that it grabs the most recent 10,000 messages
        self.volify = markovify.Text('. '.join(doc['message'] for doc in messages))
        return messages.count()


    def on_nicknameinuse(self, conn, e):
        """Handle when our nickname is already taken"""
        conn.nick(conn.get_nickname() + "_")


    def on_welcome(self, conn, e):
        """Handle successful connection to IRC server"""
        self.log("Connected to IRC server.")
        conn.join(self.channel)


    def on_privmsg(self, conn, e):
        """Handle a private message"""
        # Just run PMs as commands
        msg = e.arguments[0]
        nick = e.source.nick
        parts = msg.split(' ')

        self.log_msg(nick, nick, msg)
        self.do_command(e, nick, parts[0], parts[1:])


    def on_pubmsg(self, conn, e):
        """Handle a message in a channel"""
        nick = e.source.nick
        msg = e.arguments[0]
        channel = e.target

        self.log_msg(channel, nick, msg)

        if nick in self.ignored:
            return

        try:
            # if message is a command addressed to us, handle it
            if re.match("^!%s\s" % self._nickname, msg):
                parts = msg.split(' ')
                if len(parts) > 1:
                    self.do_command(e, channel, parts[1], parts[2:])
            else:
                for pattern, handler in self.triggers:
                    if pattern.match(msg):
                        handler(nick, channel, msg)
        except UnicodeEncodeError:
            traceback.print_exc()
        except UnicodeDecodeError:
            traceback.print_exc()

    def log(self, msg):
        timestamp = time.strftime('%m-%d-%y %H:%M:%S')
        print '[%s] %s' % (timestamp, msg)
        
    def log_msg(self, chan, nick, msg):

        self.log('<%s> %s: %s' % (chan, nick, msg))

        self.db.messages.insert_one({
            "time": time.time(),
            "channel": chan,
            "nick": nick,
            "message": msg,
        })


    # disabled because people abuse too much
    # may re-enable if we can find a way to make it safe
    # @Trigger(r"^[0-9\+\-/\*\(\)\s\.%]+$")
    def on_calc(self, sender, channel, msg):
        """Trigger handler for calculations"""
        # require at least one number
        if re.match('^.*[0-9].*$', msg) is None:
            return
        try:
            result = self.privmsg(channel, str(eval(msg)))
        except:
            self.privmsg(channel, "no.")


    @Trigger(r"^.*\b[iI][rR][cC]\b.*$")
    def on_talks_about_irc(self, sender, channel, msg):
        """Trigger handler for when someone says IRC (based on inside joke)"""
        if random.randint(1,100) == 100:
            message = "\"" + msg + "\" -- " + sender
            self.privmsg(channel, message)


    @Trigger(r"^.*\b[a-zA-Z]{2}[a-zA-Z]+[bcdfgklmnprstvwxz]er\b.*$")
    def on_er(self, sender, channel, msg):
        if random.randint(1,100) == 100:
            er_words = re.findall(r"\b[a-zA-Z]{2}[a-zA-Z]+[bcdfgklmnprstvwxz]er\b", msg)
            word = random.choice(er_words)
            self.privmsg(channel, "%s? I hardly know 'er!" % word)


    @Trigger(r".*\bay+\b")
    def on_ayy(self, sender, channel, msg):
        """Trigger handler for ayy, lmao"""
        ayy = re.findall(r".*\bay+\b", msg)
        message = 'lma' + (ayy[0].count('y') - 1) * 'o'
        self.privmsg(channel, message)
        

    @Trigger("^.*$")
    def on_table_flip(self, sender, channel, msg):
        """Trigger handler for table flipping"""
        if u'\u253B' in msg:
            self.privmsg(channel, u"\u252C\u2500\u252C\u30CE(\xBA_\xBA\u30CE)")


    @Trigger(r"what are tho+se")
    def on_those(self, sender, channel, msg):
        """Trigger for what are those"""
        self.privmsg(channel, "WHAT ARE THOOOOOOOOOOSE")


    @Trigger(r"^.*https?://[^\s]+.*$")
    def on_link(self, sender, channel, msg):
        """Trigger handler for website links"""

        # find all links in the message
        links = re.findall(r"https?://[^\s]+", msg)
        for link in links:
            # scrape the title of the webpage and send it to the channel
            try:
                resp = requests.get(link).text
                title = re.search(r"<title>(.*)</title>", resp).groups()[0]
                okchars = letters + digits + punctuation + ' '
                title = ''.join(c for c in title if c in okchars).strip()
                self.privmsg(channel, '%s' % (title))
            except:
                pass


    @Command("curse", EVERYONE)
    def cmd_curse(self, sender, channel, cmd, args):
        """curse <nick>\nPut a curse on <nick>."""
        # default to sender if they didn't specify a target
        if len(args) > 0:
            victim = args[0]
        else:
            victim = sender

        # load curses
        with open('curses.txt', 'r') as f:
            curses = list(cPickle.load(f))

        # send a random curse
        self.privmsg(channel, "%s: %s" % (victim, random.choice(curses)))


    @Command("quit", OP_ONLY)
    def cmd_quit(self, sender, channel, cmd, args):
        """quit\nQuit."""
        self.privmsg(channel, "bye")
        self.die()


    @Command("ignore", OP_ONLY)
    def cmd_ignore(self, sender, channel, cmd, args):
        """ignore <nick>\nIgnore <nick>."""
        if len(args) > 0:
            self.ignored.add(args[0])


    @Command("unignore", OP_ONLY)
    def cmd_unignore(self, sender, channel, cmd, args):
        """unignore <nick>\nStop ignoring <nick>."""
        if len(args) > 0:
            self.ignored.remove(args[0])


    @Command("help", EVERYONE)
    def cmd_help(self, sender, channel, cmd, args):
        """You're already using it!"""
        # if no args, just list commands
        if len(args) == 0:
            cmds = self.commands.keys()
            cmds.sort()
            cmdlist = "commands: %s" % ', '.join(cmds)
            self.privmsg(channel, "Use help <command> to learn about a specific command.")
            self.privmsg(channel, cmdlist)
            return

        # otherwise, give help on that specific command
        helpcmd = args[0]
        if helpcmd.lower() in self.commands:
            docs = self.commands[helpcmd.lower()].__doc__
            self.privmsg(channel, docs)


    @Command("shakespeare", EVERYONE)
    def cmd_shakespeare(self, sender, channel, cmd, args):
        """shakespeare\nGenerate some classic literature.."""
        self.privmsg(channel, self.shakespeare.make_short_sentence(500))


    @Command("stats", EVERYONE)
    def cmd_stats(self, sender, channel, cmd, args):
        """stats [nick]\nPrint statistics for a nickname"""
        if len(args) > 0:
            nick = args[0]
        else:
            nick = sender

        nick_messages = self.db.messages.find({"nick": nick})
        all_messages = self.db.messages.find()
        nick_count = nick_messages.count()
        all_count = all_messages.count()
        percent = 100.0 * float(nick_count) / all_count

        def clean(word):
            return word.strip('.,?!/;:\'"').lower()

        counter = collections.Counter()
        for doc in nick_messages:
            counter.update([clean(word) for word in doc['message'].split()])
        # total number of words from user.
        wc = sum(counter.itervalues())
        stop = set([
            'ourselves', 'hers', 'between', 'yourself', 'but', 'again', 'there', 'about',
            'once', 'during', 'out', 'very', 'having', 'with', 'they', 'own', 'an', 'be',
            'some', 'for', 'do', 'its', 'yours', 'such', 'into', 'of', 'most', 'itself', 'other',
            'off', 'is', 's', 'am', 'or', 'who', 'as', 'from', 'him', 'each', 'the', 'themselves',
            'until', 'below', 'are', 'we', 'these', 'your', 'his', 'through', 'don', 'nor', 'me', 
            'were', 'her', 'more', 'himself', 'this', 'down', 'should', 'our', 'their', 'while', 
            'above', 'both', 'up', 'to', 'ours', 'had', 'she', 'all', 'no', 'when', 'at', 'any', 
            'before', 'them', 'same', 'and', 'been', 'have', 'in', 'will', 'on', 'does', 
            'yourselves', 'then', 'that', 'because', 'what', 'over', 'why', 'so', 'can', 'did',
            'not', 'now', 'under', 'he', 'you', 'herself', 'has', 'just', 'where', 'too', 'only',
            'myself', 'which', 'those', 'i', 'after', 'few', 'whom', 't', 'being', 'if', 'theirs',
            'my', 'against', 'a', 'by', 'doing', 'it', 'how', 'further', 'was', 'here', 'than'
        ])

        favorites = [(w,c) for w, c in counter.most_common() if w not in stop][:10]

        self.privmsg(channel, "%s sent %d messages of %d logged messages (%.2f%%)" % 
            (nick, nick_count, all_count, percent))
        self.privmsg(channel, "Used %d unique words. Favorites: %s" % (wc, ', '.join(
            "%s (%.2f%%)" % (w,(float(c)/wc)) for w,c in favorites
        )))


    @Command("volify", EVERYONE)
    def cmd_volify(self, sender, channel, cmd, args):
        """volify\nSee what we really sound like."""
        self.privmsg(channel, self.volify.make_short_sentence(500))


    @Command("rlvolify", OP_ONLY)
    def cmd_rlvolify(self, sender, channel, cmd, args):
        """rlvolify\nReload the chat logs for the volify command"""
        n = self.load_volify()
        self.privmsg(channel, "Reloaded corpus of %d messages." % n)


    @Command("insult", EVERYONE)
    def cmd_insult(self, sender, channel, cmd, args):
        """insult <nick>\nSay mean things to the user."""

        if len(args) > 0:
            victim = args[0]
        else:
            victim = sender

        insults = [
            "Fuck you, <nick>",
            "<nick> couldn't point out the Earth on a globe.",
            "<nick> couldn't pour water out of a boot if the instructions were written on the heel.",
            "\x01 bites thumb\x01\n<nick>: I do not bite my thumb at you sir; but I bite my thumb, sir.",
            "<nick> is a cotton-headed ninny muggins!",
            "<nick>: Your mother was a hamster, and your father smelt of elderberries!",
            "Hey <nick>, where did you get those clothes?At the.. toilet store?",
            "<nick> is at the top of the bell curve!",
        ]

        compliments = [
            "<nick> is the best!",
            "<nick> is the greatest!",
            ":)",
            "<nick> is awesome!",
            "<3 <nick>",
        ]

        if victim.lower() not in [self._nickname, 'joecon']:
            # can't say anything mean about the creator :P
            insult = random.choice(insults).replace('<nick>', victim)
            self.privmsg(channel, insult)
        else:
            insult = random.choice(compliments).replace('<nick>', victim)
            self.privmsg(channel, insult)


    @Command("tellmeabout", EVERYONE)
    def cmd_tellmeabout(self, sender, channel, cmd, args):
        """tellmeabout [thing]\nGet basic info on <thing>."""

	    #get the thing to search for
        if len(args) > 0:
            #Get total query
            query = " ".join(args)
        else:
            #otherwise get a random page
            random = wikipedia.random(400)
            query = random[0]

        try:
            #3 sentence limit. Can be extended later
            summary = wikipedia.summary(query, 3)
            summary = summary.replace('\n', ' ')
            self.privmsg(channel, summary)
        except wikipedia.exceptions.DisambiguationError as e:
            op_list = e.options
            message = "Try: %s" % "; ".join(op_list)
            self.privmsg(channel, message)
        except wikipedia.exceptions.WikipediaException:
            self.privmsg(channel, "Sorry, can't find that.")


    def do_command(self, e, target, cmd, args):
        """Find the appropriate command handler and call it"""
        nick = e.source.nick
        conn = self.connection

        # check if command exists
        if cmd.lower() in self.commands:
            # if so, look up and call the command handler
            handler = self.commands[cmd.lower()]
            
            chan = self.channels[self.channel]

            user_level = 0
            if chan.is_oper(nick):
                user_level = 100
            elif chan.is_voiced(nick):
                user_level = 50

            if user_level >= handler.cmd_perms:
                try:
                    handler(nick, target, cmd, args)
                except:
                    self.privmsg(target, "Oops. Internal error. Check my logs.")
                    traceback.print_exc()

            else:
                self.privmsg(target, "no way")
        else:
            # otherwise print an error message
            self.privmsg(target, "what?")


    @Command("ud", EVERYONE)
    def cmd_ud(self, sender, channel, cmd, args):
        """ud [word]\nLook up a word on Urban Dictionary."""

        if len(args) > 0:
            query = " ".join(args)
        else:
            query = urbandict.TermTypeRandom()

        try:
            result = urbandict.define(query)[0]
            resp = '%s\n"%s"' % (result['def'], result['example'].strip())

            self.privmsg(channel, result['word'])
            self.privmsg(channel, resp)
        except:
            self.privmsg(channel, "Sorry, can't find that.")

    @Command("last", EVERYONE)
    def cmd_last(self, sender, channel, cmd, args):
        """last [name] [num of messages]\nShow the last [num of messages] sent by [name]"""
        
        # make the default to be sender and 1
        if len(args) > 1:
            target = args[0]
            num = int(args[1])
        elif len(args) == 1:
            if re.search(r'\b\d+\b', args[0]):
                target = sender
                num = int(args[0])
            else:
                target = args[0]
                num = 1
        else:
            target = sender
            num = 1

        #impose a max number of messages
        if num > 10:
            num = 10
        elif num < 0:
            num = 1

        # handle the command being sent and not sending that message back
        if target == sender:
            num += 1

        # get messages
        message_list = []
        messages = self.db.messages.find({"nick": target}, limit=num, sort=[("time", pymongo.DESCENDING)])
        for doc in messages:
            message_list.append(doc['message'])

        if target == sender:
            del message_list[0]
        
        #prepend user
        for i in range(0, len(message_list)):
            message_list[i] = target + ": " + message_list[i]

        self.privmsg(channel, "\n".join(message_list))

        



    def register_stuff(self):
        """Automatically find and store command/trigger handlers"""

        # enumerate all properties of this object
        for attr in dir(self):
            obj = getattr(self, attr)

            # filter crap that claims to have any attr... (looking at you, pymongo)
            if hasattr(obj, "asdfhaosiuehcaiouhseoiufh"):
                continue

            # check if each property is a command or trigger handler
            # if so, store it in the appropriate place
            if hasattr(obj, "cmd_label"):
                label = getattr(obj, "cmd_label")
                self.log('registered command %s to %s()' % (label, obj.__name__))
                self.commands[label.lower()] = obj
            elif hasattr(obj, "trigger_pattern"):
                pattern = getattr(obj, "trigger_pattern")
                self.log('registered trigger %s to %s()' % (pattern, obj.__name__))
                self.triggers.append((re.compile(pattern), obj))


    def privmsg(self, target, msg):
        """Send a message to a target, split by newlines automatically"""
        lines = msg.split('\n')
        for line in lines:
            self.send_split(target, line)


    def send_split(self, target, text):
        """Send a single line to a target, splitting by maximum line length"""
        MAX_LEN = 400 # fuck it

        text = text.encode('utf-8')

        words = text.split(" ")
        parts = []

        for word in words:
            for i in xrange(0, len(word), MAX_LEN):
                parts.append(word[i:i+MAX_LEN])

        if len(parts) == 0:
            return

        line = parts[0]
        for word in parts[1:]:
            if len(line) + len(word) + 1 <= MAX_LEN:
                line += " " + word
            else:
                self.log_msg(target, self._nickname, line.decode('utf-8'))
                self.connection.privmsg(target, line.decode('utf-8'))
                line = word

        if len(line) > 0:
            self.log_msg(target, self._nickname, line.decode('utf-8'))
            self.connection.privmsg(target, line.decode('utf-8'))



def main():
    # get command line args
    if len(sys.argv) != 4:
        print("Usage: testbot <server[:port]> <channel> <nickname>")
        sys.exit(1)

    s = sys.argv[1].split(":", 1)
    server = s[0]
    if len(s) == 2:
        try:
            port = int(s[1])
        except ValueError:
            print("Error: Erroneous port.")
            sys.exit(1)
    else:
        port = 6667
    channel = sys.argv[2]
    nickname = sys.argv[3]

    # run the bot
    bot = VolBot(channel, nickname, server, port)
    bot.start()


if __name__ == "__main__":
    main()
