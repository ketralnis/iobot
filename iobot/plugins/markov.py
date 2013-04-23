from iobot.plugins.decorators import plugin_command, plugin_hook
QUERY_REGEX = r'^(?P<nick>{})[,:] (?<message>.*)$'

class MarkovPlugin(object):
    @plugin_command
    def braininfo(self, connection, event):
        connection.reply(event, self.get_brain_info())

    @plugin_hook
    def on_privmsg(self, connection, event):
        m = match(QUERY_REGEX.format(connection.nick), event.text)
        if m:
            message = m.group('message')
            reply = load_reply(event.nick, message)
            connection.reply(event, reply)
        else:
            learn_message(event.text)

    def get_brain_info(self):
        return 'I have no brain'

    def learn_message(self, message):
        pass

    def load_reply(self, nick, message):
        return ''

Plugin = MarkovPlugin
