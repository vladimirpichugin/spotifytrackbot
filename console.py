# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import datetime
import time

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

import main
from utils import logger


def console_thread():
    while True:
        try:
            try:
                cmd_args = input().split(' ')
            except (EOFError, UnicodeDecodeError):
                continue

            cmd = cmd_args[0]
            if not cmd:
                continue

            if cmd == "help":
                logger.info("Commands: help")
            else:
                logger.info("Command not found :C")
        except:
            logger.error("Exception in console", exc_info=True)
