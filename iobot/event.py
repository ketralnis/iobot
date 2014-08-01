import re

class IrcEvent(object):
    EVENT_PATTERN = re.compile((r'^(:(?P<prefix>((?P<nick>[^!]+)!'
            r'(?P<user>[^@]+)@(?P<host>[^ ]+)|[^ ]+)) )?'
            r'((?P<numeric>[0-9]{3})|(?P<command>[^ ]+))'
            r'( (?P<destination>[^:][^ ]*))?( :(?P<text>.*)|'
            r' (?P<parameters>.*))?$'))

    COMMAND_REGEX = re.compile(r'^(?P<target>[^ ]+): ?(?P<command>[^ ]*)'
            r'( (?P<params>.*))?$')

    def __init__(self, my_nick, raw=None):
        self.raw = raw

        self.my_nick = my_nick
        self.type = None
        self.origin = None
        self.destination = None
        self.text = None
        self.parameters = []
        self.parameters_raw = None
        self.command = None
        self.command_params = None
        self.command_params_raw = None
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
        command = m.group('command')
        self.type = command.upper() if command else m.group('numeric')
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
        if self.type in ['JOIN', 'PART'] and not self.destination:
            # rescue bad JOINS/PARTS a la gamesurge
            # :iobot!iobot@host.name.com JOIN :#iobot-test
            self.destination = self.text

    def _parse_command(self):
        m = self.COMMAND_REGEX.match(self.text)
        if m and m.group('target') in (self.my_nick, 'all'):
            self.command = m.group('command')
            params_raw = m.group('params')
            self.command_params_raw = params_raw or ''
            self.command_params = params_raw.split() if params_raw else []
