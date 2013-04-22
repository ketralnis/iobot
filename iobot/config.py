class ConfigParseError(Exception):
    pass

class ConfigParseWarning(Warning):
    pass

def read_config(file_path):
    with open(file_path) as fp:
        parents = []
        current = {}
        for i, line in enumerate(fp, 1):
            line = line.strip()
            if not line:
                continue
            if line == '}':
                if all(v is None for v in current.values()):
                    current = list(current.keys())
                try:
                    current = parents.pop()
                except IndexError:
                    raise ConfigParseError('Line %d' % i)
                continue

            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
            else:
                key, value = line, None

            if value == '{':
                if key in current:
                    raise Warning
                else:
                    current[key] = {}
                parents.append(current)
                current = current[key]
                continue

            if key in current:
                raise ConfigParseWarning('Duplicate key %s line %d' % (key, i))

            if value:
                value = interp_value(value)

            current[key] = value

        return current

def interp_value(value):
    i = as_int(value)
    if i is not None:
        return i
    f = as_float(value)
    if f is not None:
        return f
    b = as_bool(value)
    if b is not None:
        return b
    return value

def as_int(value):
    try:
        return int(value)
    except:
        return None

def as_float(value):
    try:
        return float(value)
    except:
        return None

def as_bool(value):
    v = value.title()
    if v == 'True':
        return True
    elif v == 'False':
        return False
    else:
        return None
