from functools import update_wrapper

def plugin_command(f):
    """ marks an attribute for identifying a plugin method as a command """
    f.cmd = True
    return f

def admin_command(f):
    def wrapper_func(self, conn, event):
        if event.nick != conn.owner:
            channel = event.destination
            nick = event.nick
            conn.private_message(channel, ('Error: Insufficent '
                    'priveleges for %s' % nick))
            return
        return f(self, conn, event)
    return update_wrapper(wrapper_func, f)
