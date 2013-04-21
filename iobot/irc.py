import socket

from tornado.iostream import IOStream

from iobot.event import IrcEvent
from iobot.user import IrcUser
from iobot.logging import create_logger

EOL = '\r\n'

class IrcConnection(object):
    def __init__(self, bot, server_name, host, port, nick, user,
            realname, channels=None):
        self.bot = bot
        self.server_name = server_name
        self.host = host
        self.port = port
        self.nick = nick
        self.user = user
        self.realname = realname
        self.initial_channels = set(channels) if channels else set()

        self._protocol_events = dict()
        self.channels = dict()
        self.users = dict()
        self.logger = create_logger(__name__)
        self.init_protocol_events()

    def init_protocol_events(self):
        self._protocol_events = {
            'PRIVMSG' : self.on_privmsg,
            'PING'    : self.on_ping,
            'JOIN'    : self.on_afterjoin,
            '401'     : self.on_nochan,
            '001'     : self.on_welcome,
            'KICK'    : self.on_afterkick,
            'PART'    : self.on_afterpart,
            '353'     : self.on_afternames,
            'NICK'    : self.on_afternick
        }

    def connect(self, reconnecting=False):
        self.logger.info('CONNECTING...')
        _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self._stream = IOStream(_sock)
        self._stream.connect((self.host, self.port), self._register)

    def _register(self):
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

    def set_nick(self, nick):
        self.logger.info('SETTING NICK: %s' % nick)
        self.write_raw('NICK %s' % nick)

    def join_channel(self, *channels):
        self.logger.info('JOINING CHANNEL(S): %s' % channels)
        chan_def = ','.join(channels)
        self.write_raw('JOIN %s' % chan_def)

    def part_channel(self, channel):
        self.logger.info('PARTING CHANNEL: %s' % channel)
        self.write_raw('PART :%s' % channel)

    def private_message(self, destination, message):
        self.logger.info('SENDING PRIVMSG<%s>: %s' % (destination, message))
        self.write_raw('PRIVMSG %s :%s' % (destination, message))

    def kick(self, channel, user, comment=None):
        self.logger.info('KICKING<%s> %s' % (channel, user))
        kick_str = 'KICK %s %s' % (channel, user)
        if comment:
            kick_str += ' :%s' % comment
        self.write_raw(kick_str)

    def write_raw(self, line):
        line.replace(EOL, '')
        self.logger.debug('WRITE RAW: %s' % line)
        self._stream.write(line + EOL)

    def read_raw(self, line):
        self.logger.debug('READ RAW: %s' % line)
        cmd_char = self.bot.cmd_char
        event = IrcEvent(cmd_char, line)
        self.handle(event)
        self.bot.process_plugins(self, event)
        self._next()

    def handle(self, event):
        if event.type in self._protocol_events:
            self._protocol_events[event.type](event)

    def _next(self):
        self._stream.read_until(EOL, self.read_raw)

    def on_welcome(self, event):
        self.logger.info('[%s] RECIEVED RPL_WELCOME' % self.server_name)
        if self.initial_channels:
            self.join_channel(*self.initial_channels)

    def on_ping(self, event):
        # One ping only, please
        self.logger.info('[%s] RECIEVED PING' % self.server_name)
        self.write_raw("PONG %s\r\n" % event.text)

    def on_privmsg(self, event):
        # :nod!~nod@crunchy.bueno.land PRIVMSG #xx :hi
        self.logger.info('[%s] RECIEVED PRIVMSG' % self.server_name)
        pass

    def on_afternick(self, event):
        self.logger.info('[%s] RECIEVED NICK' % self.server_name)
        new_nick = event.text
        if event.nick == self.nick:
            self.nick = new_nick
        else:
            old_nick = event.nick
            self.user_change_nick(old_nick, new_nick)

    def on_afterjoin(self, event):
        self.logger.info('[%s] RECIEVED JOIN' % self.server_name)
        self.add_channel(event.text)

    def on_afternames(self, event):
        self.logger.info('[%s] RECIEVED NAMES' % self.server_name)
        nick_chan, nicks_raw = event.parameters_raw.split(':')
        nicks = nicks_raw.split()
        if '@' in nick_chan:
            channel = nick_chan.split('@')[-1].strip()
        elif '=' in nick_chan:
            channel = nick_chan.split('=')[-1].strip()
        else:
            raise Exception
        for nr in nicks:
            nick = nr if nr[0] != '@' and nr[0] != '+' else nr[1:]
            user = IrcUser(nick)
            self.add_user(channel, user)

    def on_nochan(self, event):
        self.logger.info('[%s] RECIEVED ERR_NOSUCHCHANNEL' %
                self.server_name)
        # :senor.crunchybueno.com 401 nodnc  #xx :No such nick/channel
        self.remove_channel(event.parameters[0])

    def on_afterpart(self, event):
        self.logger.info('[%s] RECIEVED PART' % self.server_name)
        if event.nick == self.nick:
            self.logger.info('IOBot parted from %s' % event.destination)
            self.remove_channel(event.destination)

    def on_afterkick(self, event):
        self.logger.info('[%s] RECIEVED KICK' % self.server_name)
        if event.parameters[0] == self.nick:
            self.logger.warn('IOBot was KICKed from %s' % event.destination)
            self.remove_channel(event.destination)
