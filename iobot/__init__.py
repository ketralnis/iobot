from tornado.ioloop import IOLoop

from iobot.bot import IOBot
from iobot.plugins import CommandRegister, TextPlugin

def run_bot(config, loglevel):
    ib = IOBot(
        host = 'irc.ponychat.net',
        nick = 'iobot-tron',
        char = '$',
        owner = 'TronPaul',
        port = 6667,
        initial_chans = ['#iobot-test'],
        loglevel = loglevel
        )

    IOLoop.instance().start()
