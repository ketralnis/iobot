import traceback
from iobot.plugins.decorators import admin_command

class AdminPlugin(object):
    @admin_command
    def load(self, conn, event):
        admin_name = event.command_params[0]
        try:
            conn.bot.load_plugin(admin_name)
        except Exception:
            conn.reply_with_nick(event, 'Error loading %s' % admin_name)
            tb = traceback.format_exc()
            conn.logger.error('Error loading %s: %s' % (admin_name, tb))
        else:
            conn.reply(event, 'Loaded %s' % admin_name)
            conn.logger.info('%s loaded %s' % (event.nick, admin_name))

    @admin_command
    def unload(self, conn, event):
        admin_name = event.command_params[0]
        try:
            conn.bot.unload_plugin(admin_name)
        except KeyError:
            conn.reply_with_nick(event, '%s is not loaded' % admin_name)
            conn.logger.info('Error unloading %s: Plugin not loaded')
        else:
            conn.reply(event, 'Unloaded %s' % admin_name)
            conn.logger.info('%s unloaded %s' % (event.nick, admin_name))

    @admin_command
    def reload(self, conn, event):
        admin_name = event.command_params[0]
        try:
            conn.bot.reload_plugin(admin_name)
        except KeyError:
            conn.reply_with_nick(event, '%s is not loaded' % admin_name)
        except Exception:
            conn.reply_with_nick(event, 'Error reloading %s' % admin_name)
            tb = traceback.format_exc()
            conn.logger.error('Error reloading %s: %s' % (admin_name, tb))
        else:
            conn.reply(event, 'Reloaded %s' % admin_name)
            conn.logger.info('%s reloaded %s' % (event.nick, admin_name))

    @admin_command
    def part(self, conn, event):
        channel = event.command_params[0]
        conn.part_channel(channel)

    @admin_command
    def join(self, conn, event):
        channel = event.command_params[0]
        conn.join_channel(channel)

    @admin_command
    def nick(self, conn, event):
        nick = event.command_params[0]
        conn.set_nick(nick)

Plugin = AdminPlugin
