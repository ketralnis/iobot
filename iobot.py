#!/usr/bin/env python
import argparse
import logging
import os
from iobot import run_bot

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Tornado driven IRC bot')
    parser.add_argument('--level', help='Log level', default='INFO')
    args = parser.parse_args()
    loglevel = getattr(logging, args.level.upper(), None)
    config_path = os.path.join(os.getcwd(), 'iobot.conf')
    run_bot(config_path, loglevel)
