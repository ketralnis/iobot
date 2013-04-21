#!/usr/bin/env python
import argparse
import logging
from iobot import run_bot

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Tornado driven IRC bot')
    parser.add_argument('--config', help='IOBot config file')
    parser.add_argument('--level', help='Log level', default='INFO')
    args = parser.parse_args()
    loglevel = getattr(logging, args.level.upper(), None)
    run_bot(None, loglevel)
