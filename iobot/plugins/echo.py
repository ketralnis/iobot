from iobot.plugins.decorators import plugin_command

class Echo(object):
    @plugin_command
    def echo(self, conn, event):
        conn.reply(event, event.command_params_raw)

Plugin = Echo
