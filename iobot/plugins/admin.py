from iobot.plugins.decorators import plugin_command

class AdminPlugin(object):
    @plugin_command
    def load(self, conn, event):
        plugin_name = event.command_params[0]
        try:
            conn.bot.load_plugin(plugin_name)
        except Exception as e:
            conn.reply_with_nick(event, 'Error loading %s' % plugin_name)
            conn.logger.error('Error loading %s: %s' % (plugin_name, e))
        else:
            conn.reply(event, 'Loaded %s' % plugin_name)
            conn.logger.info('%s loaded %s' % (event.nick, plugin_name))

    @plugin_command
    def unload(self, conn, event):
        plugin_name = event.command_params[0]
        try:
            conn.bot.unload_plugin(plugin_name)
        except KeyError:
            conn.reply_with_nick(event, '%s is not loaded' % plugin_name)
            conn.logger.info('Error unloading %s: Plugin not loaded')
        else:
            conn.reply(event, 'Unloaded %s' % plugin_name)
            conn.logger.info('%s unloaded %s' % (event.nick, plugin_name))

    @plugin_command
    def reload(self, conn, event):
        plugin_name = event.command_params[0]
        try:
            conn.bot.reload_plugin(plugin_name)
        except KeyError:
            conn.reply_with_nick(event, '%s is not loaded' % plugin_name)
        except Exception as e:
            conn.reply_with_nick(event, 'Error reloading %s' % plugin_name)
            conn.logger.error('Error reloading %s: %s' % (plugin_name, e))
        else:
            conn.reply(event, 'Reloaded %s' % plugin_name)
            conn.logger.info('%s reloaded %s' % (event.nick, plugin_name))

    @plugin_command
    def part(self, conn, event):
        channel = event.command_params[0]
        conn.part_channel(channel)

    @plugin_command
    def join(self, conn, event):
        channel = event.command_params[0]
        conn.join_channel(channel)

    @plugin_command
    def nick(self, conn, event):
        nick = event.command_params[0]
        conn.set_nick(nick)

Plugin = AdminPlugin
