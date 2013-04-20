#!/usr/bin/env python
from tornado.ioloop import IOLoop

from iobot.bot import IOBot
from iobot.plugins import CommandRegister, TextPlugin

def main():
    ib = IOBot(
        host = 'irc.ponychat.net',
        nick = 'iobot-tron',
        char = '$',
        owner = 'TronPaul',
        port = 6667,
        initial_chans = ['#iobot-test'],
        )

    ib.register_plugins(['echo','stock'])

    IOLoop.instance().start()

if __name__ == '__main__':
    main()

