import logging
import sys, os.path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..'))

from unittest import TestCase

import mock
from tornado.testing import AsyncTestCase

from iobot import IOBot

def _patched_connect(self):
    """
    bypasses _connect on the object since we don't feel like patching all of
    socket.socket and IOStream, we're just going to fake those.
    """
    self._stream = mock.MagicMock()
    self._register()

class TestIrcConnection(AsyncTestCase):
    def irc_in(self, stat, txt):
        self.irc.read_raw(':faker.irc {} :{}\r\n'.format(stat, txt))

    def raw_irc_in(self, txt):
        self.irc.read_raw(txt)

    @mock.patch('iobot.irc.IrcConnection.connect', _patched_connect)
    def setUp(self):
        from iobot.irc import IrcConnection
        super(TestIrcConnection, self).setUp()
        bot = mock.Mock()
        self.irc = IrcConnection(bot, 'test', 'localhost', 6667,
                'testie', 'iobot', 'iobot', 'owner')
        self.irc.connect()
        assert self.irc._stream.write.called

    def test_set_nick(self):
        nick = 'testnick'
        self.irc.set_nick(nick)
        assert self.irc._stream.write.called_with("NICK {}".format(nick))

    def test_set_empty_nick(self):
        from iobot.irc import IrcError
        self.assertRaises(IrcError, self.irc.set_nick, '')

    def test_join(self):
        # testing these together
        chan = '#testchan'
        self.irc.join_channel(chan)
        assert self.irc._stream.write.called_with("JOIN :{}".format(chan))

    def test_join_empty_channel_name(self):
        from iobot.irc import IrcError
        self.assertRaises(IrcError, self.irc.join_channel, '')

    def test_part(self):
        # testing these together
        chan = '#testchan'
        self.irc.part_channel(chan)
        assert self.irc._stream.write.called_with("PART :{}".format(chan))

    def test_part_empty_channel_name(self):
        from iobot.irc import IrcError
        self.assertRaises(IrcError, self.irc.part_channel, '')

    def test_kick(self):
        chan = '#testchan'
        nick = 'nick'
        self.irc.kick(chan, nick)
        assert self.irc._stream.write.called_with("KICK {} {}".format(chan,
            nick))

    def test_priv_msg(self):
        chan, msg = "#hi", "i am the walrus"
        self.irc.private_message(chan, msg)
        self.irc._stream.write.assert_called_with(
                "PRIVMSG {} :{}\r\n".format(chan, msg)
                )

    def test_priv_msg_empty_message(self):
        from iobot.irc import IrcError
        self.assertRaises(IrcError, self.irc.private_message, '', '')

    def test_priv_msg_empty_destination(self):
        from iobot.irc import IrcError
        self.assertRaises(IrcError, self.irc.private_message, '', 'abc')

    def test_ping(self):
        # going to fake a PING from the server on this one
        #self.irc.hook('PING', lambda irc: self.stop(True))
        self.raw_irc_in('PING :12345\r\n')
        #assert self.wait()
        assert self.irc._stream.write.called

    def test_parse_join(self):
        chan = '#testchan'
        # fake irc response to our join
        self.raw_irc_in(
            ':{}!~{}@localhost JOIN :{}\r\n'.format(
                self.irc.nick,
                self.irc.nick,
                chan
                )
            )
        assert chan in self.irc.channels

    def test_parse_msg_to_unjoined(self):
        chan = "#hi"
        self.irc.channels[chan] = [] # fake join msg
        # :senor.crunchybueno.com 401 nodnc  #xx :No such nick/channel
        self.irc_in(
            "401 {} {}".format(self.irc.nick, chan),
            "No such nick/channel"
            )
        assert chan not in self.irc.channels
