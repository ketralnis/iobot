from tornado.ioloop import IOLoop

from iobot.bot import IOBot
from iobot.config import read_config
from iobot.plugins import CommandRegister, TextPlugin

def run_bot(config_path, loglevel):
    config = read_config(config_path)
    servers = config['servers']
    prefix = config['core']['prefix']
    nick = config['core']['nick']
    user = config['core']['user']
    realname = config['core']['realname']
    ib = IOBot(
        servers,
        prefix,
        nick,
        user,
        realname,
        loglevel
        )

    IOLoop.instance().start()
