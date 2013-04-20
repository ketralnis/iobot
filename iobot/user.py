class IrcUser(object):
    def __init__(self, nick, user=None, host=None):
        self.nick = nick
        self.user = user
        self.host = host

    def __repr__(self):
        return '<IrcUser %s>' % self.nick
