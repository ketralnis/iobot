from functools import update_wrapper

def plugin_command(f):
    """ marks an attribute for identifying a plugin method as a command """
    f.cmd = True
    return f

class HookNameError(Exception):
    pass

def plugin_hook(f):
    f.hook = True
    if not f.func_name.startswith('on_'):
        raise HookNameError
    return f

def admin_command(f):
    def wrapper_func(self, conn, event):
        if event.nick not in conn.owners:
            channel = event.destination
            nick = event.nick
            conn.private_message(channel,
                                 'Error: Insufficient privileges for %s' % nick)
            return
        return f(self, conn, event)
    nf = update_wrapper(wrapper_func, f)
    return plugin_command(nf)
