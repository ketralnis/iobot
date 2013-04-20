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

class IrcEvent(object):
    """
    tries to guess and populate something from an ircd statement
    """
    EVENT_PATTERN = re.compile((r'^(:(?P<prefix>((?P<nick>[^!]+)!'
            r'(?P<user>[^@]+)@(?P<host>[^ ]+)|[^ ]+)) )?'
            r'((?P<numeric>[0-9]{3})|(?P<command>[^ ]+))'
            r'( (?P<destination>[^:][^ ]*))?( :(?P<text>.*)|'
            r' (?P<parameters>.*))?$'))
    COMMAND_REGEX = (r'^{}(?P<command>[^ ]*)'
            r'( (?P<params>.*))?$')

    def __init__(self, bot, raw=None):
        self._bot = bot
        self.raw = raw
        self.type = None
        self.origin = None
        self.destination = None
        self.text = None
        self.parameters = []
        self.parameters_raw = None
        self.command = None
        self.command_params = None
        if raw:
            self._parse()

    def __repr__(self):
        return ('<IrcEvent object: %s %s>' % (self.type, self.destination))

    def _parse(self):
        if self.raw[-2:] == '\r\n':
            line = self.raw[:-2]
        else:
            line = self.raw
        m = self.EVENT_PATTERN.match(line)
        self.origin = m.group('prefix')
        self.type = m.group('command') or m.group('numeric')
        self.destination = m.group('destination')
        self.nick = m.group('nick')
        self.user = m.group('user')
        self.host = m.group('host')
        self.text = m.group('text')
        self.parameters_raw = m.group('parameters')
        self.parameters = (self.parameters_raw.split() if
                self.parameters_raw else [])

        if self.type == 'PRIVMSG':
            self._parse_command()

    def _parse_command(self):
        regex = self.COMMAND_REGEX.format(self._bot.char)
        m = re.match(regex, self.text)
        if m:
            self.command = m.group('command')
            self.command_params = m.group('params')

    def reply(self, text):
        self._bot.private_message(self.destination, text)

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
        self._commands = dict()
        self._connected = False
        # used for parsing out nicks later, just wanted to compile it once
        # server protocol gorp
        self._irc_proto = {
            'PRIVMSG' : IrcProtoCmd(self._p_privmsg),
            'PING'    : IrcProtoCmd(self._p_ping),
            'JOIN'    : IrcProtoCmd(self._p_afterjoin),
            '401'     : IrcProtoCmd(self._p_nochan),
            '001'     : IrcProtoCmd(self._p_welcome),
            'KICK'    : IrcProtoCmd(self._p_afterkick),
            'PART'    : IrcProtoCmd(self._p_afterpart)
            }
        # build our user command list
        self.cmds = dict()

        self._initial_chans = initial_chans
        self._on_ready = on_ready

        # finally, connect.
        self._connect()

    def set_nick(self, nick):
        self._write("NICK %s\r\n" % nick)

    def set_user(self, username, real_name):
        self._write("USER %s 0 * :%s\r\n" % (username, real_name))

    def join_channel(self, *channels):
        for c in channels:
            self._write("JOIN :%s\r\n" % c)

    def part_channel(self, *channels):
        for c in channels:
            self._write("PART :%s\r\n" % c)

    def private_message(self, dest, msg):
        """
        sends a message to a chan or user
        """
        self._write("PRIVMSG {} :{}\r\n".format(dest, msg))

    def kick(self, channel, user, comment=None):
        kick_str = "KICK {} {}".format(channel, user)
        if comment:
            kick_str += " :{}".format(comment)
        kick_str += "\r\n"
        self._write(kick_str)

    def hook(self, cmd, hook_f):
        """
        allows easy hooking of any raw irc protocol statement.  These will be
        executed after the initial protocol parsing occurs.  Plugins can use this
        to extend their reach lower into the protocol.
        """
        assert( cmd in self._irc_proto )
        self._irc_proto[cmd].hooks.add(hook_f)

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
                self._commands[cmd] = plugin

            self._plugins[plugin_name] = plugin_cls

    def unload_plugin(self, plugin_name):
        plugin_cls = self._plugins[plugin_name]
        for cmd in self._commands.keys():
            plugin = self._commands[cmd]
            if isinstance(plugin, plugin_cls):
                del self._commands[cmd]
        del self._plugins[plugin_name]

    def load_plugin(self, plugin_name):
        plugin_path = os.path.join(os.path.split(__file__)[0], 'plugins/')
        module_info = imp.find_module(plugin_name, [plugin_path])
        module = imp.load_module(plugin_name, *module_info)
        return module.Plugin

    def _connect(self):
        logger.info('Connecting...')
        _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self._stream = IOStream(_sock)
        self._stream.connect((self.host, self.port), self._after_connect)

    def _after_connect(self):
        logger.info('Connected!')
        self.set_nick(self.nick)
        self.set_user('iobot', 'iobot')

        self._next()

    def _write(self, line):
        logger.debug('Writing: %s' % line)
        self._stream.write(line)

    def _next(self):
        # go back on the loop looking for the next line of input
        self._stream.read_until('\r\n', self._incoming)

    def _incoming(self, line):
        logger.debug('Read: %s' % line)
        event = self._parse_line(line)
        self._process_hooks(event)
        self._process_plugins(event)
        self._next()

    def _parse_line(self, line):
        return IrcEvent(self, line)

    def _process_hooks(self, event):
        print event.type
        print event.destination
        print event.text
        print event.parameters
        if event.type in self._irc_proto:
            self._irc_proto[event.type](event)

    def _process_plugins(self, event):
        """ parses a completed ircEvent for module hooks """
        try:
            plugin = self._commands.get(event.command) if event.command else None
        except KeyError:
            # plugin does not exist
            pass

        try:
            if plugin:
                plugin_method = getattr(plugin, event.command)
                plugin_method(event)
        except:
            doc = "usage: %s %s" % (event.command, plugin_method.__doc__)
            event.reply(doc)

    def _p_welcome(self, event):
        if self._initial_chans:
            for c in self._initial_chans: self.join_channel(c)
            del self._initial_chans
        if self._on_ready:
            self._on_ready()

    def _p_ping(self, event):
        # One ping only, please
        logger.info('Recieved PING %s' % event.origin)
        self._write("PONG %s\r\n" % event.text)

    def _p_privmsg(self, event):
        # :nod!~nod@crunchy.bueno.land PRIVMSG #xx :hi
        pass

    def _p_afterjoin(self, event):
        self.chans.add(event.text)

    def _p_nochan(self, event):
        # :senor.crunchybueno.com 401 nodnc  #xx :No such nick/channel
        if event.parameters[0] in self.chans:
            self.chans.remove(event.parameters[0])

    def _p_afterpart(self, event):
        pass

    def _p_afterkick(self, event):
        self._p_afterpart(self, event)

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

