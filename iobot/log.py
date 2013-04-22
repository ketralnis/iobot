from logging import getLogger,StreamHandler, Formatter, DEBUG

def create_logger(connection):
    logger = getLogger(connection.server_name)
    logger.propagate = False
    logger.setLevel(connection.bot.log_level)
    del logger.handlers[:]
    handler = StreamHandler()
    handler.setFormatter(Formatter(connection.log_format))
    logger.addHandler(handler)
    return logger
