#! /usr/bin/env python
#
# Example program using irc.bot.
#
# Joel Rosdahl <joel@rosdahl.net>
from typing import Optional
import time
import random
import analysis
from analysis import TextAnalysis
from threading import Timer, Thread

"""A simple example bot.
This is an example bot that uses the SingleServerIRCBot class from
irc.bot.  The bot enters a channel and listens for commands in
private messages and channel traffic.  Commands in channel messages
are given by prefixing the text by the bot name followed by a colon.
It also responds to DCC CHAT invitations and echos data sent in such
sessions.
The known commands are:
    stats -- Prints some channel information.
    disconnect -- Disconnect the bot.  The bot will try to reconnect
                  after 60 seconds.
    die -- Let the bot cease to exist.
    dcc -- Let the bot invite you to a DCC CHAT connection.
"""
import inspect
import re
import traceback
import enum
import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr

INITIAL_WAIT = 35
TIMEOUT_MAX = 30

class State(enum.Enum):
    START = 1
    INITIAL_OUTREACH_1 = 2
    SECONDARY_OUTREACH_1 = 3
    GIVEUP_FRUSTRATED_1 = 4
    INQUIRY_1 = 5
    INQUIRY_REPLY_1 = 6
    OUTREACH_REPLY_2 = 7
    INQUIRY_2 = 8
    GIVEUP_FRUSTRATED_2 = 9
    INQUIRY_REPLY_2 = 10
    END = 11

inquiry_words = {'how', 'what', 'why', '?'}

greeting_words = {'hi', 'hello', 'howdy', 'hey', 'yo', 'hiya'}

greeting_states = {State.START, State.INITIAL_OUTREACH_1, State.SECONDARY_OUTREACH_1}

reply_states = {State.OUTREACH_REPLY_2, State.INQUIRY_REPLY_1, State.INQUIRY_REPLY_2}

inquiry_states = {State.INQUIRY_1, State.INQUIRY_2}

frustrated_phrases = [
    "Fine, we don't have to chat :(",
    "Alright, well, two can play this game",
    "You could at least say bye if you don't want to talk :/"
]

inquiry_phrases = [
    "I'm doing well!",
    "I'm fine, thanks for asking :)",
    "I've been alright :)"
]

bot_phrases = {
    State.INITIAL_OUTREACH_1 : ['Hi', 'Hello!', 'Hey!'],
    State.SECONDARY_OUTREACH_1 : ['Hello? Anyone there?', 'Hellooooooo?', 'I said hi >:('],
    State.GIVEUP_FRUSTRATED_1 : frustrated_phrases,
    State.GIVEUP_FRUSTRATED_2 : frustrated_phrases,
    State.OUTREACH_REPLY_2 : ['Hi back at ya!', 'Well hello there!', 'Hi!!', 'Hello! :)'],
    State.INQUIRY_1 : ["What's going on?", "How are you doing today?", "What's poppin?", "How's it going?"],
    State.INQUIRY_2 : ["How about you?", "How are YOU doing?", "And yourself?"],
    State.INQUIRY_REPLY_1 : inquiry_phrases,
    State.INQUIRY_REPLY_2 : inquiry_phrases    
}

adjacency = {
    State.START : {
        'timeout' : State.INITIAL_OUTREACH_1,
        'success' : State.INITIAL_OUTREACH_1
    },
    State.INITIAL_OUTREACH_1 : {
        'timeout' : State.SECONDARY_OUTREACH_1,
        'success' : State.OUTREACH_REPLY_2
    },
    State.SECONDARY_OUTREACH_1 : {
        'timeout' : State.GIVEUP_FRUSTRATED_1,
        'success' : State.OUTREACH_REPLY_2
    },
    State.OUTREACH_REPLY_2 : {
        'timeout' : State.GIVEUP_FRUSTRATED_2,
        'success' : State.INQUIRY_1
    },
    State.INQUIRY_1 : {
        'timeout' : State.GIVEUP_FRUSTRATED_1,
        'success' : State.INQUIRY_REPLY_2
    },
    State.INQUIRY_REPLY_2 : {
        'timeout' : State.GIVEUP_FRUSTRATED_1,
        'success' : State.INQUIRY_2
    },
    State.INQUIRY_2 : {
        'timeout' : State.GIVEUP_FRUSTRATED_2,
        'success' : State.INQUIRY_REPLY_1
    },
    State.INQUIRY_REPLY_1 : {
        'timeout' : State.GIVEUP_FRUSTRATED_2, #idk ab this one
        'success' : State.END
    },
    State.GIVEUP_FRUSTRATED_1 : {
        'timeout' : State.END,
        'success' : State.END
    },
    State.GIVEUP_FRUSTRATED_2 : {
        'timeout' : State.END,
        'success' : State.END
    },
    State.END : {
        'timeout' : State.END,
        'success' : State.END
    }
}

class TestBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667):
        nickname = nickname[:16]
        if nickname[-4:] != '-bot':
            if len(nickname) > 12:
                nickname = nickname[:12]
            nickname += '-bot'
        
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.join_message = None
        self.timer: Optional[Timer] = Timer(INITIAL_WAIT, self.handle_timeout)
        self.timer.start()
        self.timeout_message = None
        self.total_positivity = 0
        self.total_negativity = 0
        self.total_objectivity = 0
        self.state = State.START
        self.converser = None

    def on_join(self, connection, events):
        c = self.connection

        user: str = events.source
        if user.startswith(c.get_nickname()) and self.join_message is not None:
            c.privmsg(self.channel, self.join_message)

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_privmsg(self, c, e):
        self.do_command(e, e.arguments[0])

    def on_pubmsg(self, c, e):
        a = e.arguments[0].split(":", 1)
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(
                self.connection.get_nickname()
        ):
            self.do_command(e, a[1].strip())
        return

    def on_dccmsg(self, c, e):
        # non-chat DCC messages are raw bytes; decode as text
        text = e.arguments[0].decode('utf-8')
        c.privmsg("You said: " + text)

    def on_dccchat(self, c, e):
        if len(e.arguments) != 2:
            return
        args = e.arguments[1].split()
        if len(args) == 4:
            try:
                address = ip_numstr_to_quad(args[2])
                port = int(args[3])
            except ValueError:
                return
            self.dcc_connect(address, port)

    def notice_lines(self, target: str, text: str):
        c = self.connection

        for line in text.split('\n'):
            c.privmsg(target, line)

    def reset_state(self):
        self.state = State.START
        self.set_timeout(INITIAL_WAIT)
        self.converser = None

    def select_reply(self):
        state_phrases = bot_phrases[self.state]
        phrase = state_phrases[random.randint(0, len(state_phrases) - 1)]
        return phrase

    def msg_user(self, msg):
        c = self.connection
        channel = self.channel

        if self.converser is None:
            users = [
                user
                for chname, chobj in self.channels.items()
                for user in sorted(chobj.users())
                if user != c.get_nickname()
            ]
            self.converser = users[random.randint(0, len(users) - 1)]
        
        c.privmsg(channel, self.converser + ': ' + msg)

    def do_command(self, e, cmd: str):

        nick = e.source.nick
        c = self.connection
        channel = self.channel

        if self.converser is not None:
            if nick != self.converser:
                return
        else:
            self.converser = nick

        cmd = cmd.strip()

        if self.timer is not None:
            self.timer.cancel()

        time.sleep(random.randint(1, 3))

        self.advance_state(cmd)

        if cmd == "die":
            self.msg_user("That's pretty dark, but whatever")
            self.die()
        elif cmd == "forget":
            self.state = State.START
            self.set_timeout()
        elif cmd == "participants":
            for chname, chobj in self.channels.items():
                c.privmsg(self.channel, 'Participants in channel are:')
                users = sorted(chobj.users())
                c.privmsg(self.channel, ", ".join(users))
        else:
            self.handle_action()

    def advance_state(self, cmd):
        channel = self.channel
        c = self.connection

        self.state = adjacency[self.state]['success']

    def handle_action(self):
        channel = self.channel
        c = self.connection

        if self.state == State.INQUIRY_REPLY_2:
            self.set_timeout()
            return

        self.state = adjacency[self.state]['success']
        if self.state == State.END:
            self.reset_state()
            return
        phrase = self.select_reply()
        self.msg_user(phrase)
        
        if self.state == State.INQUIRY_REPLY_2:
            self.state = adjacency[self.state]['success']
            phrase = self.select_reply()
            time.sleep(random.randint(1, 3))
            self.msg_user(phrase)

        if self.state == State.INQUIRY_REPLY_1:
            self.state = adjacency[self.state]['success']

        if self.state == State.END:
            self.reset_state()
        else:
            self.set_timeout()

    def set_timeout(self, custom=TIMEOUT_MAX):
        self.timer = Timer(custom, self.handle_timeout)
        self.timer.start()

    def handle_timeout(self):
        channel = self.channel
        c = self.connection

        self.state = adjacency[self.state]['timeout']
        phrase = self.select_reply()
        self.msg_user(phrase)
        if self.state == State.GIVEUP_FRUSTRATED_1 or self.state == State.GIVEUP_FRUSTRATED_2:
            self.state = State.END

        if self.state != State.END and \
                (self.state != State.GIVEUP_FRUSTRATED_1 or self.state != State.GIVEUP_FRUSTRATED_2):
            self.set_timeout()
        elif self.state == State.END:
            self.reset_state()


def main():
    import sys

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

    bot = TestBot(channel, nickname, server, port)
    bot.start()


if __name__ == "__main__":
    main()
