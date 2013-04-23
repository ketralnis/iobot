from iobot.plugins import TextPlugin
from iobot.plugins.decorators import plugin_command

class Echo(TextPlugin):
    @plugin_command
    def echo(self, conn, event):
        conn.reply(event.command_params_raw)

Plugin = Echo
