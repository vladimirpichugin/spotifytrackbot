# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import os
import pathlib
import logging

from settings import Settings


def init_logger():
    l = logging.getLogger('spotifytrackbot')
    l.setLevel(logging.DEBUG if Settings.DEBUG else logging.INFO)
    l.propagate = False

    for handler in list(l.handlers):
        l.removeHandler(handler)

    stream_handler = get_logger_stream_handler()
    stream_handler.setLevel(level=logging.DEBUG if Settings.DEBUG else logging.INFO)

    l.addHandler(stream_handler)

    return l


def get_logger_formatter(
        f=u'%(pathname)s:%(lineno)d\n[%(asctime)s] %(levelname)-6s %(threadName)-14s: %(message)s'):
    return logging.Formatter(
        fmt=f,
        datefmt='%d.%m.%y %H:%M:%S')


def get_logger_stream_handler():
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(get_logger_formatter(u'[%(asctime)s] %(levelname)-6s %(threadName)-14s: %(message)s'))

    return stream_handler


logger = init_logger()
logger.debug("Initializing logger..")
