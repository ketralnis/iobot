import imp
import os
from logging import DEBUG

from iobot.irc import IrcConnection

class IOBot(object):
    def __init__(self, servers, cmd_char, nick, user, realname, loglevel):
        """
        create an irc bot instance.
        @params
        initial_chans: None or list of strings representing channels to join
        """
        self.nick = nick
        self.user = user
        self.realname = realname
        self.cmd_char = cmd_char
        self._plugins = dict()
        self._commands = dict()
        # build our user command list
        self.cmds = dict()
        self.loglevel = loglevel

        for server_name, config in servers.items():
            conn = self.create_connection(server_name, config)
            conn.connect()

    def create_connection(self, server_name, config):
        address = config['address']
        port = config['port']
        channels = config.get('channels', [])
        owner = config['owner']
        return IrcConnection(self, server_name, address, port,
                self.nick, self.user, self.realname, owner,
                channels)

    def register_plugins(self, plugin_names):
        """
        accepts an instance of Plugin to add to the callback chain
        """
        for plugin_name in plugin_names:
            self.load_plugin(plugin_name)

    def unload_plugin(self, plugin_name):
        plugin_cls = self._plugins[plugin_name]
        for cmd in self._commands.keys():
            plugin = self._commands[cmd]
            if isinstance(plugin, plugin_cls):
                del self._commands[cmd]
        del self._plugins[plugin_name]

    def reload_plugin(self, plugin_name):
        if plugin_name not in self._plugins:
            raise KeyError
        self.load_plugin(plugin_name)

    def load_plugin(self, plugin_name):
        # update to support custom paths?
        plugin_module = self.load_module(plugin_name)
        plugin_cls = plugin_module.Plugin
        plugin = plugin_cls()

        cmds = []
        for method in dir(plugin):
            if callable(getattr(plugin, method)) \
                and hasattr(getattr(plugin, method), 'cmd'):
                cmds.append(method)

        for cmd in cmds:
            self._commands[cmd] = plugin

        self._plugins[plugin_name] = plugin_cls

    def load_module(self, plugin_name):
        # this will also reload a loaded module
        plugin_path = os.path.join(os.path.split(__file__)[0], 'plugins/')
        module_info = imp.find_module(plugin_name, [plugin_path])
        module = imp.load_module(plugin_name, *module_info)
        return module

    def process_plugins(self, connection, event):
        """ parses a completed ircEvent for module hooks """
        try:
            plugin = self._commands.get(event.command) if event.command else None
        except KeyError:
            # plugin does not exist
            pass

        if plugin and hasattr(plugin, event.command):
            plugin_method = getattr(plugin, event.command)
            try:
                plugin_method(connection, event)
            except Exception as e:
                connection.private_message(event.destination, str(e))
