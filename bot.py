"""bot.py - Main module for running Volbot"""


# Python Standard Library
import cPickle
import random
import re
import sys
import traceback
from string import letters, digits, punctuation

# Third Party Libraries
import irc.bot
import markovify
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
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)

        self.channel = channel

        # initialize shakespearean generator
        with open('shake2.txt') as f:
            self.shakespeare = markovify.Text(f.read())

        self.ignored = set()

        # setup commands and triggers
        self.commands = {}
        self.triggers = []
        self.register_stuff()


    def on_nicknameinuse(self, conn, e):
        """Handle when our nickname is already taken"""
        conn.nick(conn.get_nickname() + "_")


    def on_welcome(self, conn, e):
        """Handle successful connection to IRC server"""
        conn.join(self.channel)


    def on_privmsg(self, conn, e):
        """Handle a private message"""
        # Just run PMs as commands
        msg = e.arguments[0]
        parts = msg.split(' ')
        self.do_command(e, e.source.nick, parts[0], parts[1:])


    def on_pubmsg(self, conn, e):
        """Handle a message in a channel"""
        msg = e.arguments[0]

        channel = e.target

        if e.source.nick in self.ignored:
            return

        try:
            # if message is a command addressed to us, handle it
            if msg.lower().startswith('!' + conn.get_nickname().lower()):
                parts = msg.split(' ')
                if len(parts) > 1:
                    self.do_command(e, channel, parts[1], parts[2:])
            else:
                # otherwise, check if the message matches any trigger patterns
                # also, add it to the chat log for volify
                flines = []
                with open('chatlog.txt', 'r') as f:
                    flines = f.read().splitlines()

                while len(flines) > 100000: # arbitrary 100,000 line storage limit
                    del flines[0]

                with open('chatlog.txt', 'w') as f:
                    flines.append(msg)
                    try:
                        f.write('\n'.join(flines))
                    except UnicodeEncodeError:
                        del flines[-1]
                        f.write('\n'.join(flines))
                

                for pattern, handler in self.triggers:
                    if pattern.match(msg):
                        handler(e.source.nick, channel, msg)
        except UnicodeEncodeError:
            print "UnicodeEncodeError"
        except UnicodeDecodeError:
            print "UnicodeDecodeError"

    @Trigger(r"^[0-9\+\-/\*\(\)\s\.%]+$")
    def on_calc(self, sender, channel, msg):
        """Trigger handler for calculations"""
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
                self.privmsg(channel, '%s: %s' % (link, title))
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

    @Command("volify", EVERYONE)
    def cmd_volify(self, sender, channel, cmd, args):
        """volify\nSee what we really sound like."""
        volify = ''
        with open('chatlog.txt') as f:
            volify = markovify.Text(f.read())
        self.privmsg(channel, volify.make_short_sentence(500))
            


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
            chan = self.channels[target]

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




    def register_stuff(self):
        """Automatically find and store command/trigger handlers"""

        # enumerate all properties of this object
        for attr in dir(self):
            obj = getattr(self, attr)

            # check if each property is a command or trigger handler
            # if so, store it in the appropriate place
            if hasattr(obj, "cmd_label"):
                label = getattr(obj, "cmd_label")
                print 'registered %s' % label
                self.commands[label.lower()] = obj
            elif hasattr(obj, "trigger_pattern"):
                pattern = getattr(obj, "trigger_pattern")
                print 'registered %s' % pattern
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
                self.connection.privmsg(target, line.decode('utf-8'))
                line = word

        if len(line) > 0:
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
