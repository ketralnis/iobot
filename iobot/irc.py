import socket

from tornado.iostream import IOStream

from iobot.event import IrcEvent
from iobot.user import IrcUser
from iobot.log import create_logger

EOL = '\r\n'

class IrcConnection(object):
    def __init__(self, bot, server_name, address, port, nick, user,
            realname, channels=None):
        self.bot = bot
        self.server_name = server_name
        self.address = address
        self.port = port
        self.nick = nick
        self.user = user
        self.realname = realname
        self.initial_channels = set(channels) if channels else set()
        self.log_format = ('%(asctime)s - %(levelname)s in %(module)s '
                '[%(pathname)s:%(lineno)d]:\n%(message)s'.format(
                self.server_name))
        self.logger = create_logger(self)

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
        self._stream = IOStream(_sock)
        self._stream.connect((self.address, self.port), self._register)

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
        self.logger.debug('WRITE RAW:\n%s' % line)
        self._stream.write(line + EOL)

    def read_raw(self, line):
        self.logger.debug('READ RAW:\n%s' % line.replace(EOL, ''))
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
        self.logger.info('RECIEVED RPL_WELCOME')
        if self.initial_channels:
            self.join_channel(*self.initial_channels)

    def on_ping(self, event):
        # One ping only, please
        self.logger.info('RECIEVED PING')
        self.write_raw("PONG %s\r\n" % event.text)

    def on_privmsg(self, event):
        # :nod!~nod@crunchy.bueno.land PRIVMSG #xx :hi
        self.logger.info('RECIEVED PRIVMSG')
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
        channel = event.text or event.destination
        self.logger.info('RECIEVED JOIN {channel: %s}' % (channel))
        self.add_channel(channel)

    def on_names(self, event):
        self.logger.info('RECIEVED NAMES')
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
        self.logger.info('RECIEVED ERR_NOSUCHCHANNEL')
        # :senor.crunchybueno.com 401 nodnc  #xx :No such nick/channel
        self.remove_channel(event.parameters[0])

    def on_part(self, event):
        self.logger.info('RECIEVED PART')
        if event.nick == self.nick:
            self.logger.info('IOBot parted from %s' % event.destination)
            self.remove_channel(event.destination)

    def on_kick(self, event):
        self.logger.info('RECIEVED KICK')
        if event.parameters[0] == self.nick:
            self.logger.warn('IOBot was KICKed from %s' % event.destination)
            self.remove_channel(event.destination)
