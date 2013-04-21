import re

class IrcEvent(object):
    EVENT_PATTERN = re.compile((r'^(:(?P<prefix>((?P<nick>[^!]+)!'
            r'(?P<user>[^@]+)@(?P<host>[^ ]+)|[^ ]+)) )?'
            r'((?P<numeric>[0-9]{3})|(?P<command>[^ ]+))'
            r'( (?P<destination>[^:][^ ]*))?( :(?P<text>.*)|'
            r' (?P<parameters>.*))?$'))
    COMMAND_REGEX = (r'^{}(?P<command>[^ ]*)'
            r'( (?P<params>.*))?$')

    def __init__(self, cmd_char, raw):
        self.cmd_char = cmd_char
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
        regex = self.COMMAND_REGEX.format(re.escape(self.cmd_char))
        m = re.match(regex, self.text)
        if m:
            self.command = m.group('command')
            self.command_params = m.group('params')
