#!/usr/bin/env python
import re
import socket
import imp
import os
import logging

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream

from iobot.plugins import CommandRegister, TextPlugin

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class IrcProtoCmd(object):
    def __init__(self, actn):
        self.hooks = set()
        self.actn = actn

    def __call__(self, irc):
        self.actn(irc)
        for h in self.hooks:
            h(irc)

renick = re.compile("^(\w*?)!")

class IrcObj(object):
    """
    tries to guess and populate something from an ircd statement
    """

    def __init__(self, line, bot):
        self.text = self.server_cmd = self.chan = self.nick = None
        self._bot = bot
        self.line = line
        self.command = None
        self.command_args = None
        self._parse_line(line)

    def __repr__(self):
        return ('<IrcObj object with line: \'%s\' and command: \'%s\'>' %
                (self.line, self.command))

    def _parse_line(self, line):
        if not line.startswith(":"):
            # PING most likely
            stoks = line.split()
            self.server_cmd = stoks[0].upper()
            return

        # :senor.crunchybueno.com 401 nodnc  #xx :No such nick/channel
        # :nod!~nod@crunchy.bueno.land PRIVMSG xyz :hi

        tokens = line[1:].split(":")
        if not tokens: return

        stoks = tokens[0].split()

        # find originator
        nick = renick.findall(stoks[0])
        if len(nick) == 1:
            self.nick = nick[0]
        stoks = stoks[1:] # strip off server tok

        self.server_cmd = stoks[0].upper()
        stoks = stoks[1:]

        # save off remaining tokens
        self.stoks = stoks

    def say(self, text, dest=None):
        self._bot.say(dest or self.chan, text)

    def error(self, text, dest=None):
        self.say(dest or self.chan, "error: %s" % text)

class IOBot(object):
    def __init__(
            self,
            host,
            nick = 'hircules',
            port = 6667,
            char = '@',
            owner = 'owner',
            initial_chans = None,
            on_ready = None,
            ):
        """
        create an irc bot instance.
        @params
        initial_chans: None or list of strings representing channels to join
        """
        self.nick = nick
        self.chans = set() # chans we're a member of
        self.owner = owner
        self.host = host
        self.port = port
        self.char = char
        self._plugins = dict()
        self._connected = False
        # used for parsing out nicks later, just wanted to compile it once
        # server protocol gorp
        self._irc_proto = {
            'PRIVMSG' : IrcProtoCmd(self._p_privmsg),
            'PING'    : IrcProtoCmd(self._p_ping),
            'JOIN'    : IrcProtoCmd(self._p_afterjoin),
            '401'     : IrcProtoCmd(self._p_nochan),
            '001'     : IrcProtoCmd(self._p_welcome),
            }
        # build our user command list
        self.cmds = dict()

        self._initial_chans = initial_chans
        self._on_ready = on_ready

        # finally, connect.
        self._connect()

    def hook(self, cmd, hook_f):
        """
        allows easy hooking of any raw irc protocol statement.  These will be
        executed after the initial protocol parsing occurs.  Plugins can use this
        to extend their reach lower into the protocol.
        """
        assert( cmd in self._irc_proto )
        self._irc_proto[cmd].hooks.add(hook_f)

    def joinchan(self, chan):
        self._write("JOIN :%s\r\n" % chan)

    def say(self, chan, msg):
        """
        sends a message to a chan or user
        """
        self._write("PRIVMSG {} :{}\r\n".format(chan, msg))

    def load_plugin(self, plugin_name):
        plugin_path = os.path.join(os.path.split(__file__)[0], 'plugins/')
        module_info = imp.find_module(plugin_name, [plugin_path])
        module = imp.load_module(plugin_name, *module_info)
        return module.Plugin

    def register_plugins(self, plugin_names):
        """
        accepts an instance of Plugin to add to the callback chain
        """
        for plugin_name in plugin_names:
            # update to support custom paths?
            plugin_cls = self.load_plugin(plugin_name)
            plugin = plugin_cls()

            cmds = []
            for method in dir(plugin):
                if callable(getattr(plugin, method)) \
                    and hasattr(getattr(plugin, method), 'cmd'):
                    cmds.append(method)

            for cmd in cmds:
                self._plugins[cmd] = plugin

    def _connect(self):
        logger.info('Connecting...')
        _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self._stream = IOStream(_sock)
        self._stream.connect((self.host, self.port), self._after_connect)

    def _after_connect(self):
        logger.info('Connected!')
        self._write("NICK %s\r\n" % self.nick)
        self._write("USER %s 0 * :%s\r\n" % ("iobot", "iobot"))

        self._next()

    def _parse_line(self, line):
        irc = IrcObj(line, self)
        return irc

    def _p_welcome(self, irc):
        if self._initial_chans:
            for c in self._initial_chans: self.joinchan(c)
            del self._initial_chans
        if self._on_ready:
            self._on_ready()

    def _p_ping(self, irc):
        self._write("PONG %s\r\n" % irc.line[1])

    def _p_privmsg(self, irc):
        # :nod!~nod@crunchy.bueno.land PRIVMSG #xx :hi
        toks = irc.line[1:].split(':')[0].split()
        irc.chan = toks[-1] # should be last token after last :
        irc.text = irc.line[irc.line.find(':',1)+1:].strip()
        if irc.text and irc.text.startswith(self.char):
            text_split = irc.text.split()
            irc.command = text_split[0][1:]
            irc.command_args = ' '.join(text_split[1:])

    def _p_afterjoin(self, irc):
        toks = irc.line.strip().split(':')
        if irc.nick != self.nick:
            return # we don't care right now if others join
        irc.chan = toks[-1] # should be last token after last :
        self.chans.add(irc.chan)

    def _p_nochan(self, irc):
        # :senor.crunchybueno.com 401 nodnc  #xx :No such nick/channel
        toks = irc.line.strip().split(':')
        irc.chan = toks[1].strip().split()[-1]
        if irc.chan in self.chans: self.chans.remove(irc.chan)

    def _process_plugins(self, irc):
        """ parses a completed ircObj for module hooks """
        try:
            plugin = self._plugins.get(irc.command) if irc.command else None
        except KeyError:
            # plugin does not exist
            pass

        try:
            if plugin:
                plugin_method = getattr(plugin, irc.command)
                plugin_method(irc)
        except:
            doc = "usage: %s %s" % (irc.command, plugin_method.__doc__)
            irc.say(doc)

    def _process_hooks(self, irc):
        if irc.server_cmd in self._irc_proto:
            self._irc_proto[irc.server_cmd](irc)

    def _write(self, line):
        logger.debug('Writing: %s' % line)
        self._stream.write(line)

    def _next(self):
        # go back on the loop looking for the next line of input
        self._stream.read_until('\r\n', self._incoming)

    def _incoming(self, line):
        logger.debug('Read: %s' % line)
        irc = self._parse_line(line)
        self._process_hooks(irc)
        self._process_plugins(irc)
        self._next()

def main():
    ib = IOBot(
        host = 'irc.us.ponychat.net',
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

