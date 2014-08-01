import socket

from tornado.iostream import IOStream
from tornado.iostream import SSLIOStream

from iobot.event import IrcEvent
from iobot.user import IrcUser
from logging import getLogger

class IrcError(Exception):
    pass

EOL = '\r\n'

class IrcConnection(object):
    def __init__(self, bot, server_name, address, port, nick, user,
            realname, owner, channels=None, password=None, ssl=None):
        self.bot = bot
        self.server_name = server_name
        self.owner = owner
        self.address = address
        self.port = port
        self.nick = nick
        self.user = user
        self.password = password
        self.ssl = ssl
        self.realname = realname
        self.initial_channels = set(channels) if channels else set()

        self.logger = getLogger(__name__)

        self._protocol_events = dict()
        self.channels = dict()
        self.users = dict()
        self.init_protocol_events()

    def init_protocol_events(self):
        self._protocol_events = {
            'PRIVMSG' : self.on_privmsg,
            'PING'    : self.on_ping,
            'JOIN'    : self.on_join,
            '401'     : self.on_nochan,
            '001'     : self.on_welcome,
            'KICK'    : self.on_kick,
            'PART'    : self.on_part,
            '353'     : self.on_names,
            'NICK'    : self.on_nick
        }

    def connect(self, reconnecting=False):
        self.logger.info('CONNECTING...')
        _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)

        if self.ssl is None:
            self._stream = IOStream(_sock)
        elif self.ssl is True:
            self._stream = SSLIOStream(_sock)
        else:
            self._stream = SSLIOStream(_sock, ssl_options=self.ssl)

        self._stream.connect((self.address, self.port), self._register)

    def _register(self):
        self.logger.info('CONNECTED')

        if self.password:
            # TODO need to check for error responses
            self.authenticate()

        self.set_nick(self.nick)
        self.write_raw('USER %s 0 * :%s' % (self.user, self.realname))

        self._next()

    def add_channel(self, channel):
        self.channels[channel] = []

    def remove_channel(self, channel):
        del self.channels[channel]

    def add_user(self, channel, user):
        self.channels[channel].append(user)
        self.users[user.nick] = user

    def remove_user(self, channel, user):
        self.channels[channels].remove(user)
        del self.users[user.nick]

    def user_change_nick(self, old_nick, new_nick):
        user = self.users.pop(old_nick)
        user.nick = new_nick
        self.users[new_nick] = user

    def authenticate(self):
        self.logger.info("Authenticating (%s)", self.password)
        self.write_raw('PASS %s' % self.password)

    def set_nick(self, nick):
        if not nick:
            raise IrcError('Cannot set empty nick')
        self.logger.info('SETTING NICK {nick: %s}' % nick)
        self.write_raw('NICK %s' % nick)

    def join_channel(self, *channels):
        if not all([c for c in channels]):
            raise IrcError('Empty channel')
        self.logger.info('JOINING CHANNEL(S): {channels: %s}' % repr(channels))
        chan_def = ','.join(channels)
        self.write_raw('JOIN %s' % chan_def)

    def part_channel(self, *channels):
        if not all([c for c in channels]):
            raise IrcError('Empty channel')
        self.logger.info('PARTING CHANNEL: {channels: %s}' % repr(channels))
        chan_def = ','.join(channels)
        self.write_raw('PART :%s' % chan_def)

    def private_message(self, destination, message):
        if not message:
            raise IrcError('Cannot send empty message')
        if not destination:
            raise IrcError('Cannot send to empty destination')
        self.logger.info('SENDING PRIVMSG: {destination: %s, message: %s}' % (destination, message))
        self.write_raw('PRIVMSG %s :%s' % (destination, message))

    def reply(self, event, message):
        if event.destination and event.destination != self.nick:
            destination = event.destination
        else:
            destination = event.nick
        self.private_message(destination, message)

    def reply_with_nick(self, event, message):
        if event.destination:
            message = '%s: %s' % (event.nick, message)
        self.reply(event, message)

    def kick(self, channel, user, comment=None):
        if not channel:
            raise IrcError('Cannot kick from empty channel')
        if not user:
            raise IrcError('Cannot kick empty player')
        self.logger.info('KICKING {channel: %s, user: %s}' % (channel, user))
        kick_str = 'KICK %s %s' % (channel, user)
        if comment:
            kick_str += ' :%s' % comment
        self.write_raw(kick_str)

    def write_raw(self, line):
        line.replace(EOL, '')
        self.logger.debug('WRITE RAW: {line: %s}' % line)
        self._stream.write(line + EOL)

    def read_raw(self, line):
        self.logger.debug('READ RAW: {line: %s}' % line.replace(EOL, ''))
        event = IrcEvent(self.nick, line)
        self.handle(event)
        self.bot.process_hooks(self, event)
        self.bot.process_plugins(self, event)
        self._next()

    def handle(self, event):
        if event.type in self._protocol_events:
            self._protocol_events[event.type](event)

    def _next(self):
        self._stream.read_until(EOL, self.read_raw)

    def on_welcome(self, event):
        self.logger.info('RECIEVED RPL_WELCOME')
        if self.initial_channels:
            self.join_channel(*self.initial_channels)

    def on_ping(self, event):
        # One ping only, please
        self.logger.info('RECIEVED PING')
        self.write_raw("PONG %s\r\n" % event.text)

    def on_privmsg(self, event):
        # :nod!~nod@crunchy.bueno.land PRIVMSG #xx :hi
        self.logger.info('RECIEVED PRIVMSG {destination: %s,'
                ' message: %s}' % (event.destination, event.text))
        pass

    def on_nick(self, event):
        old_nick = event.nick
        new_nick = event.text
        self.logger.info('RECIEVED NICK {old_nick: %s, new_nick: %s}' %
                (old_nick, new_nick))
        if event.nick == self.nick:
            self.nick = new_nick
        else:
            self.user_change_nick(old_nick, new_nick)

    def on_join(self, event):
        channel = event.destination
        nick = event.nick
        self.logger.info('RECIEVED JOIN {channel: %s, nick: %s}' % (channel, nick))
        if self.nick == nick:
            self.add_channel(channel)
        else:
            self.add_user(channel, IrcUser(nick))

    def on_names(self, event):
        nick_chan, nicks_raw = event.parameters_raw.split(':')
        nicks = nicks_raw.split()
        if '@' in nick_chan:
            channel = nick_chan.split('@')[-1].strip()
        elif '=' in nick_chan:
            channel = nick_chan.split('=')[-1].strip()
        else:
            raise Exception
        self.logger.info('RECIEVED NAMES {channel: %s, nick_count: %d}' % (
            channel, len(nicks)))
        for nr in nicks:
            if nr[0] == '@':
                nick = nr[1:]
            elif nr[0] == '+':
                nick = nr[1:]
            else:
                nick = nr
            user = IrcUser(nick)
            self.add_user(channel, user)

    def on_nochan(self, event):
        channel = event.parameters[0]
        self.logger.info('RECIEVED ERR_NOSUCHCHANNEL {channel: %s}' % channel)
        # :senor.crunchybueno.com 401 nodnc  #xx :No such nick/channel
        self.remove_channel(channel)

    def on_part(self, event):
        nick = event.nick
        channel = event.destination
        self.logger.info('RECIEVED PART {channel: %s, nick: %s}' % (channel,
            nick))
        if event.nick == self.nick:
            self.logger.info('IOBot parted from %s' % channel)
            self.remove_channel(channel)

    def on_kick(self, event):
        nick = event.parameters[0]
        channel = event.destination
        self.logger.info('RECIEVED KICK {channel: %s, nick: %s}' % (channel,
            nick))
        if event.parameters[0] == self.nick:
            self.logger.warning('IOBot was KICKed from %s' % channel)
            self.remove_channel(channel)
