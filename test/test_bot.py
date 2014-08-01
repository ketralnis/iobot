from unittest import TestCase

class TestIOBot(TestCase):
    def setUp(self):
        from iobot.bot import IOBot
        self.bot = IOBot({}, ';', 'bot', 'bot', 'bot')

    def test_create_connection(self):
        pass

    def test_add_plugin_empty_plugin(self):
        # cannot unittest higher plugin methods in isolation
        class EmptyPlugin(object):
            pass
        bot = self.bot
        bot.add_plugin('empty_plugin', EmptyPlugin)
        self.assertEqual(len(bot._plugins), 1)
        self.assertEqual(bot._plugins['empty_plugin'], EmptyPlugin)
        self.assertEqual(len(bot._commands), 0)
        self.assertEqual(len(bot._hooks), 0)

    def test_add_plugin_simple_plugin(self):
        from iobot.plugins.decorators import plugin_command, plugin_hook
        class SimplePlugin(object):
            @plugin_command
            def my_command(self, *args, **kwargs):
                pass

            @plugin_hook
            def on_join(self, *args, **kwargs):
                pass
        bot = self.bot
        bot.add_plugin('simple_plugin', SimplePlugin)
        self.assertEqual(len(bot._plugins), 1)
        self.assertEqual(bot._plugins['simple_plugin'], SimplePlugin)
        self.assertEqual(len(bot._commands), 1)
        self.assertEqual(len(bot._hooks), 1)
        self.assertTrue('my_command' in bot._commands)
        self.assertTrue(isinstance(bot._commands['my_command'], SimplePlugin))
        self.assertTrue('JOIN' in bot._hooks)
        self.assertEqual(len(bot._hooks['JOIN']), 1)
        self.assertTrue(isinstance(bot._hooks['JOIN'][0], SimplePlugin))
