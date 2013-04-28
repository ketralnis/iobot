from unittest import TestCase

class TestIrcEvent(TestCase):
    def makeOne(self, line, cmd_char=';'):
        from iobot.event import IrcEvent
        return IrcEvent(';', line)

    def test_parse_privmsg(self):
        e = self.makeOne((':bot!bot@host.name.com'
                ' PRIVMSG #bot :beep'))
        self.assertEqual(e.origin, 'bot!bot@host.name.com')
        self.assertEqual(e.nick, 'bot')
        self.assertEqual(e.user, 'bot')
        self.assertEqual(e.host, 'host.name.com')
        self.assertEqual(e.text, 'beep')
        self.assertEqual(e.destination, '#bot')
        self.assertEqual(e.type, 'PRIVMSG')
        self.assertTrue(e.command is None)
        self.assertTrue(e.command_params is None)
        self.assertTrue(e.command_params_raw is None)

    def test_parse_privmsg_command(self):
        e = self.makeOne((':bot!bot@host.name.com'
                ' PRIVMSG #bot :;beep'))
        self.assertEqual(e.origin, 'bot!bot@host.name.com')
        self.assertEqual(e.nick, 'bot')
        self.assertEqual(e.user, 'bot')
        self.assertEqual(e.host, 'host.name.com')
        self.assertEqual(e.text, ';beep')
        self.assertEqual(e.destination, '#bot')
        self.assertEqual(e.type, 'PRIVMSG')
        self.assertEqual(e.command, 'beep')
        self.assertEqual(e.command_params, [])
        self.assertEqual(e.command_params_raw, '')

    def test_parse_privmsg_command_with_params(self):
        e = self.makeOne((':bot!bot@host.name.com'
                ' PRIVMSG #bot :;beep bep boop'))
        self.assertEqual(e.origin, 'bot!bot@host.name.com')
        self.assertEqual(e.nick, 'bot')
        self.assertEqual(e.user, 'bot')
        self.assertEqual(e.host, 'host.name.com')
        self.assertEqual(e.text, ';beep bep boop')
        self.assertEqual(e.destination, '#bot')
        self.assertEqual(e.type, 'PRIVMSG')
        self.assertEqual(e.command, 'beep')
        self.assertEqual(e.command_params, ['bep', 'boop'])
        self.assertEqual(e.command_params_raw, 'bep boop')

    def test_parse_join(self):
        e = self.makeOne((':bot!bot@host.name.com'
            ' JOIN :#brahtobot'))
        self.assertEqual(e.origin, 'bot!bot@host.name.com')
        self.assertEqual(e.nick, 'bot')
        self.assertEqual(e.user, 'bot')
        self.assertEqual(e.host, 'host.name.com')
        self.assertEqual(e.text, '#brahtobot')
        self.assertEqual(e.destination, '#brahtobot')
        self.assertEqual(e.type, 'JOIN')
        self.assertTrue(e.command is None)
        self.assertTrue(e.command_params is None)
        self.assertTrue(e.command_params_raw is None)

    def test_parse_gamesurge_join(self):
        e = self.makeOne((':bot!bot@host.name.com'
            ' JOIN #brahtobot'))
        self.assertEqual(e.origin, 'bot!bot@host.name.com')
        self.assertEqual(e.nick, 'bot')
        self.assertEqual(e.user, 'bot')
        self.assertEqual(e.host, 'host.name.com')
        self.assertTrue(e.text is None)
        self.assertEqual(e.destination, '#brahtobot')
        self.assertEqual(e.type, 'JOIN')
        self.assertTrue(e.command is None)
        self.assertTrue(e.command_params is None)
        self.assertTrue(e.command_params_raw is None)
