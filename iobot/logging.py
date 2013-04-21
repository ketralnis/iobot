from __future__ import absolute_import

from logging import getLogger, StreamHandler, DEBUG

def create_logger(logger_name):
    logger = getLogger(logger_name)
    logger.setLevel(DEBUG)
    return logger
