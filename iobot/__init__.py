from tornado.ioloop import IOLoop

from iobot.bot import IOBot
from iobot.plugins import CommandRegister, TextPlugin

def run_bot(config_path, loglevel):
    servers = {'ponychat': {
        'host': 'irc.ponychat.net',
        'port': 6667,
        'channels': ['#iobot-test']
        }
    }
    cmd_char = '$'
    nick = 'iobot-tron'
    user = 'iobot'
    realname = 'iobot'
    ib = IOBot(
        servers,
        cmd_char,
        nick,
        user,
        realname
        )

    ib.register_plugins(['echo'])

    IOLoop.instance().start()
