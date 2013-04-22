from logging import getLogger,StreamHandler, Formatter, DEBUG

def create_logger(connection):
    logger = getLogger(connection.server_name)
    logger.propagate = False
    logger.setLevel(connection.bot.loglevel)
    del logger.handlers[:]
    handler = StreamHandler()
    handler.setFormatter(Formatter(connection.log_format))
    logger.addHandler(handler)
    return logger
