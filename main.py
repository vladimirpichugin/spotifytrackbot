# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import logging
from time import sleep

from flask import request

import telebot

from spotipy import MemoryCacheHandler
from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyOauthError

import urllib.parse

from utils import WebServer
from utils import MySpotify
from utils import get_logger_file_handler, get_logger_stream_handler
from commands import *

logger.debug("Initializing telebot..")

telebot.apihelper.ENABLE_MIDDLEWARE = True

telebot.logger.removeHandler(telebot.logger.handlers[0])
telebot.logger.setLevel(level=logging.DEBUG if Settings.DEBUG_TELEBOT else logging.INFO)

telebot.logger.addHandler(get_logger_file_handler())
telebot.logger.addHandler(get_logger_stream_handler())

bot = telebot.TeleBot(Settings.BOT_TOKEN)
ws = WebServer()


def webserver_daemon():
    app = ws.get_app()

    logger.info("SpotifyTrackBot successfully initialized!")

    logger.info(f"Listen {Settings.WEB_HOST}:{Settings.WEB_PORT}")

    @app.route("/", methods=Settings.WEB_ALLOWED_HTTP_METHODS)
    def index():
        return ws.ok("App {} v{}. Author: {}.".format(Settings.APP_NAME, Settings.APP_VERSION, Settings.APP_AUTHOR), 200)

    @app.route("/spotifytrackbot", methods=Settings.WEB_ALLOWED_HTTP_METHODS)
    @app.route("/spotifytrackbot/", methods=Settings.WEB_ALLOWED_HTTP_METHODS)
    def auth():
        code = request.args.get('code')
        state = request.args.get('state')

        if not code or not state:
            return ws.failed("Wrong parameters were passed. Please try again.", 400)

        oauth_context = SpotifyOAuth(
            client_id=Settings.SPOTIFY_CLIENT_ID,
            client_secret=Settings.SPOTIFY_CLIENT_SECRET,
            redirect_uri=Settings.SPOTIFY_REDIRECT_URI,
            show_dialog=False,
            open_browser=False,
            cache_handler=MemoryCacheHandler()
        )

        try:
            oauth_data = oauth_context.get_access_token(
                code=code,
                as_dict=True,
                check_cache=False
            )
        except SpotifyOauthError as err:
            err_desc = err.error_description

            logger.debug(f"{err.error}: {err.error_description}")

            if err_desc == "Authorization code expired":
                return ws.failed(f"Authorize bot again.", 400)

            if err_desc == "Invalid authorization code":
                return ws.failed("Bad Request", 400)

            return ws.failed("Auth Problems", 400)
        except:
            return ws.failed("Auth Problems", 500)

        client = storage.get_client_by_key(key=state)
        if not client:
            return ws.failed("Wrong parameters were passed. Please try again.", 400)

        sp = MySpotify(auth_manager=oauth_context)

        try:
            client['user_info'] = sp.get_me()
            sp.current_user_playing_track()
            sp.current_user_recently_played(limit=1)
        except:
            return ws.failed("Wrong parameters were passed. Please try again.", 400)

        client['spotify_token_info'] = oauth_data
        storage.save_client(client)

        return ws.ok("Spotify authorized. You can close this page.", 200)

    app.run(
        host=Settings.WEB_HOST,
        port=Settings.WEB_PORT,
        debug=Settings.DEBUG_FLASK,
        ssl_context=None
    )


def bot_polling():
    try:
        while True:
            try:
                me = bot.get_me()
                logger.info(f"Logged as {me.first_name} (@{me.username}).")
                logger.info("Starting bot polling.")
                bot.enable_save_next_step_handlers(delay=3)
                bot.load_next_step_handlers()
                bot.polling(none_stop=True, interval=Settings.BOT_INTERVAL, timeout=Settings.BOT_TIMEOUT)
            except:
                logger.error(f"Bot polling failed, restarting in {Settings.BOT_TIMEOUT} sec.", exc_info=True)
                bot.stop_polling()
                sleep(Settings.BOT_TIMEOUT)
            else:
                bot.stop_polling()
                logger.info("Bot polling loop finished.")
                break
    except:
        logger.error("Bot polling loop crashed.", exc_info=True)


@bot.middleware_handler(update_types=['message'])
def middleware_handler_message(bot_instance, message):
    try:
        cmd, args = None, message.text.split(' ')

        if message.entities:
            for entity in message.entities:
                if entity.type == 'bot_command':
                    cmd = message.text[entity.offset + 1:entity.length + 1]

                    if '@' in cmd:
                        cmd = cmd.split('@')[0]

                    del args[0]

        text_args = ' '.join(args)
    except (IndexError, AttributeError):
        args = []
        cmd = None
        text_args = ''

    message.args = args
    message.text_args = text_args
    message.cmd = cmd

    client = storage.get_client(message.from_user)
    message.client = client

    storage.save_client(client, message.from_user)


@bot.message_handler(commands=['logout'])
def logout(message):
    text, markup = cmd_logout(client=message.client, user=message.from_user)
    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.message_handler(commands=['start'])
def start(message):
    text, markup = cmd_start(client=message.client, user=message.from_user)
    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.inline_handler(func=None)
def inline(inline_query):
    inline_handler(inline_query=inline_query, bot=bot)
