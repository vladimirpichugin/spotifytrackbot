# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import logging
from time import sleep

import flask
from flask import request

import telebot

from spotipy import MemoryCacheHandler
from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyOauthError
from spotipy.exceptions import SpotifyException

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
        d = 'https://pichug.in/login?error=webapp_error&webapp=spotifytrackbot'

        code = request.args.get('code')
        state = request.args.get('state')

        if not code or not state:
            #return ws.failed("Wrong parameters were passed. Please try again.", 400)
            return flask.redirect(f'{d}&error_reason=auth_problems&error_code=A1&error_description=Wrong parameters were passed. Please try again.')

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

                return flask.redirect(
                    f'{d}&error_reason=SpotifyOauthError&error_code=A2&error_description=Authorization code expired')

            if err_desc == "Invalid authorization code":
                return flask.redirect(
                    f'{d}&error_reason=SpotifyOauthError&error_code=A3&error_description=Invalid authorization code')

            return flask.redirect(
                    f'{d}&error_reason=SpotifyOauthError&error_code=A4&error_description=Auth Problems')
        except:
            return flask.redirect(
                    f'{d}&error_reason=&error_code=A5&error_description=Auth Problems')

        client = storage.get_client_by_key(key=state)
        if not client:
            return flask.redirect(
                    f'{d}&error_reason=client_not_found&error_code=A6&error_description=Client Not Found')

        client['spotify_token_info'] = oauth_data
        storage.save_client(client)

        sp = MySpotify(auth_manager=oauth_context)

        try:
            user_info = sp.get_me()
            client['user_info'] = user_info

            sp.current_user_playing_track()
            sp.current_user_recently_played(limit=1)
        except SpotifyException as err:
            msg = err.msg

            if 'User not registered in the Developer Dashboard' in msg:
                try:
                    bot.send_message(chat_id=client.id, text=L10n.get('linked_whitelist'))
                except:
                    pass

                return flask.redirect(
                    f'{d}&error_reason=SpotifyException&error_code=A7&error_description=The user must be whitelisted by the developer')

            if 'Spotify is unavailable in this country' in msg:
                return flask.redirect(
                    f'{d}&error_reason=SpotifyException&error_code=A10&error_description=')


            logger.debug('SpotifyException', exc_info=True)
            return flask.redirect(
                    f'{d}&error_reason=SpotifyException&error_code=A8&error_description=')
        except Exception:
            logger.debug('Exception, step A9', exc_info=True)
            return flask.redirect(
                    f'{d}&error_reason=Exception&error_code=A9&error_description=')

        try:
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton('Try now', switch_inline_query=' ')
            )
            bot.send_message(chat_id=client.id, text=L10n.get('linked'), reply_markup=markup)
        except:
            pass

        return flask.redirect(
            'https://pichug.in/blank?webapp=spotifytrackbot&msg=spotify_authorized')

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
                bot.polling(non_stop=True, interval=Settings.BOT_INTERVAL, timeout=Settings.BOT_TIMEOUT)
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


@bot.callback_query_handler(func=None)
def cqh(call):
    try:
        call_data = call.data
        if not call_data:
            return telebot.CancelUpdate()

        parsed_data = urllib.parse.parse_qs(call_data)
        for key, value in parsed_data.items():
            value = value[0]
            if value == 'y':
                value = True
            if value == 'n':
                value = False
            parsed_data[key] = value

        track_id = parsed_data.get('track_id')
        if not track_id:
            return telebot.CancelUpdate()

        likes = parsed_data.get('like', 0)
        if not likes:
            likes = 1
        if not likes.isdigit():
            likes = 1
        likes = int(likes)
        if likes < 0:
            likes = 1

        likes_new = likes + 1
        likes = f'❤️ {likes} like' if likes == 1 else f'❤️ {likes} likes'

        reply_markup = InlineKeyboardMarkup()
        reply_markup.row(
            InlineKeyboardButton(likes,
                                 callback_data=f'like={likes_new}&track_id={track_id}')
        )
        reply_markup.row(
            InlineKeyboardButton('🔍 Find Song', url=f'https://song.link/s/{track_id}'),
            InlineKeyboardButton('💚 Spotify', url=f'https://open.spotify.com/track/{track_id}')
        )

        bot.edit_message_reply_markup(inline_message_id=call.inline_message_id, reply_markup=reply_markup)

        bot.answer_callback_query(callback_query_id=call.id, text='❤️ Like!')
    except:
        logger.error('callback handler err', exc_info=True)
        return telebot.CancelUpdate()
