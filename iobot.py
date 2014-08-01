#!/usr/bin/env python
import argparse
import os
from iobot import run_bot

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Tornado driven IRC bot')
    parser.add_argument('--config', help='iobot config', default='iobot.conf')
    args = parser.parse_args()
    config_path = os.path.join(os.getcwd(), args.config)
    run_bot(config_path)
