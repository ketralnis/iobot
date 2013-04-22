from iobot.plugins import TextPlugin
from iobot.plugins.decorators import plugin_command

class Echo(TextPlugin):
    @plugin_command
    def echo(self, conn, event):
        conn.private_message(event.destination, "%s" % event.command_params)

Plugin = Echo
