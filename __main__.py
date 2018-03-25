# !/usr/bin/env python
import os

from bot.spybot import SpyBot

if __name__ == '__main__':
    token = os.getenv('SPYBOT_TOKEN', '').strip()
    if len(token) > 0:
        SpyBot(token).run()
    else:
        error = """Environment variable 'SPYBOT_TOKEN' is missing or empty.
        Use 'export SPYBOT_TOKEN=<TELEGRAM BOT TOKEN>' (Unix)
        or 'set SPYBOT_TOKEN=<TELEGRAM BOT TOKEN>' (Windows)
        to specify the bot token given to you by BotFather."""
        raise RuntimeError(error)
