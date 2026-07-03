# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import logging
import signal
import threading
import urllib.parse
from time import sleep
from urllib.parse import urlencode

import flask
import telebot
from flask import request
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOauthError
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from commands import cmd_stop, cmd_start, inline_handler
from localization import L10n
from settings import Settings
from storage import storage
from utils.logging import get_logger_stream_handler, logger
from utils.spotify import build_oauth_context, build_spotify_client
from utils.webserver import WebServer

logger.debug("Initializing telebot..")

telebot.apihelper.ENABLE_MIDDLEWARE = True
if Settings.TELEGRAM_PROXY:
    telebot.apihelper.proxy = {
        'http': Settings.TELEGRAM_PROXY,
        'https': Settings.TELEGRAM_PROXY
    }

telebot.logger.setLevel(level=logging.DEBUG if Settings.DEBUG_TELEBOT else logging.INFO)
telebot.logger.propagate = False

for handler in list(telebot.logger.handlers):
    telebot.logger.removeHandler(handler)

telebot.logger.addHandler(get_logger_stream_handler())

bot = telebot.TeleBot(
    Settings.BOT_TOKEN,
    threaded=True,
    skip_pending=Settings.BOT_SKIP_PENDING,
    num_threads=Settings.BOT_WORKER_THREADS,
)
ws = WebServer()
shutdown_event = threading.Event()


def _redirect_url(base_url, params):
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode(params)}"


def _auth_error_redirect(error_reason, error_code, error_description=""):
    params = {
        "error": "webapp_error",
        "webapp": Settings.APP_NAME.lower(),
        "error_reason": error_reason,
        "error_code": error_code,
        "error_description": error_description,
    }
    return flask.redirect(_redirect_url(Settings.WEB_AUTH_ERROR_REDIRECT_URL, params))


def create_app():
    app = ws.get_app()

    def auth_callback():
        code = request.args.get('code')
        state = request.args.get('state')

        if not code or not state:
            return _auth_error_redirect(
                "auth_problems",
                "A1",
                "Wrong parameters were passed. Please try again.",
            )

        oauth_context = build_oauth_context()

        try:
            oauth_data = oauth_context.get_access_token(
                code=code,
                as_dict=True,
                check_cache=False,
            )
        except SpotifyOauthError as err:
            err_desc = err.error_description or ""
            logger.debug(f"{err.error}: {err_desc}")

            if err_desc == "Authorization code expired":
                return _auth_error_redirect(
                    "SpotifyOauthError",
                    "A2",
                    "Authorization code expired",
                )

            if err_desc == "Invalid authorization code":
                return _auth_error_redirect(
                    "SpotifyOauthError",
                    "A3",
                    "Invalid authorization code",
                )

            return _auth_error_redirect("SpotifyOauthError", "A4", "Auth Problems")
        except Exception:
            logger.error("Unexpected Spotify auth error.", exc_info=True)
            return _auth_error_redirect("", "A5", "Auth Problems")

        client = storage.get_client_by_key(key=state)
        if not client:
            return _auth_error_redirect(
                "client_not_found",
                "A6",
                "Client Not Found",
            )

        client['spotify_token_info'] = oauth_data
        storage.save_client(client)

        sp = build_spotify_client(auth_manager=oauth_context)

        try:
            client['user_info'] = sp.get_me()
            storage.save_client(client)

            sp.current_user_playing_track()
            sp.current_user_recently_played(limit=1)
        except SpotifyException as err:
            msg = err.msg

            if 'User not registered in the Developer Dashboard' in msg:
                try:
                    reply_markup = InlineKeyboardMarkup()
                    reply_markup.row(
                        InlineKeyboardButton(
                            'Написать разработчику',
                            url=f'https://t.me/PichuginAssistantBot?start=SpotifyTrackBot',
                        )
                    )

                    bot.send_message(chat_id=client.id, text=L10n.get('linked_whitelist'), reply_markup=reply_markup)
                except Exception:
                    logger.debug("Failed to send whitelist message.", exc_info=True)

                return _auth_error_redirect(
                    "SpotifyException",
                    "A7",
                    "The user must be whitelisted by the developer",
                )

            if 'Spotify is unavailable in this country' in msg:
                return _auth_error_redirect("SpotifyException", "A10")

            logger.debug('SpotifyException', exc_info=True)
            return _auth_error_redirect("SpotifyException", "A8")
        except Exception:
            logger.debug('Exception, step A9', exc_info=True)
            return _auth_error_redirect("Exception", "A9")

        try:
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton('Попробовать', switch_inline_query=' '))
            bot.send_message(chat_id=client.id, text=L10n.get('linked'), reply_markup=markup)
        except Exception:
            logger.debug("Failed to send Spotify linked message.", exc_info=True)

        return flask.redirect(Settings.WEB_AUTH_SUCCESS_REDIRECT_URL)

    app.add_url_rule("/callback", "auth_callback", auth_callback,
                     methods=Settings.WEB_ALLOWED_HTTP_METHODS)

    return app


def webserver_daemon():
    app = create_app()

    logger.info("SpotifyTrackBot successfully initialized!")
    logger.info(f"Listen {Settings.WEB_HOST}:{Settings.WEB_PORT}")

    app.run(
        host=Settings.WEB_HOST,
        port=Settings.WEB_PORT,
        debug=Settings.DEBUG_FLASK,
        ssl_context=None,
        threaded=True,
        use_reloader=False,
    )


def bot_polling():
    while not shutdown_event.is_set():
        try:
            me = bot.get_me()
            logger.info(f"Logged as {me.first_name} (@{me.username}).")
            logger.info("Starting bot polling.")
            bot.infinity_polling(
                timeout=Settings.BOT_TIMEOUT,
                interval=Settings.BOT_INTERVAL,
                long_polling_timeout=Settings.BOT_LONG_POLLING_TIMEOUT,
                skip_pending=Settings.BOT_SKIP_PENDING,
                allowed_updates=Settings.BOT_ALLOWED_UPDATES,
            )
        except Exception:
            if shutdown_event.is_set():
                break
            logger.error(
                f"Bot polling failed, restarting in {Settings.BOT_RESTART_DELAY} sec.",
                exc_info=True,
            )
        finally:
            bot.stop_polling()

        if not shutdown_event.is_set():
            sleep(Settings.BOT_RESTART_DELAY)

    logger.info("Bot polling loop stopped.")


@bot.middleware_handler(update_types=['message'])
def middleware_handler_message(bot_instance, message):
    try:
        text = message.text or ""
        args = text.split()
        cmd = None

        if message.entities:
            for entity in message.entities:
                if entity.type == 'bot_command':
                    cmd = text[entity.offset + 1:entity.offset + entity.length]

                    if '@' in cmd:
                        cmd = cmd.split('@')[0]

                    if args:
                        del args[0]
                    break

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


@bot.message_handler(commands=['start'])
def start(message):
    text, markup = cmd_start(client=message.client, user=message.from_user)
    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.message_handler(commands=['stop', 'logout'])
def stop(message):
    text, markup = cmd_stop(client=message.client, user=message.from_user)
    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.inline_handler(func=None)
def inline(inline_query):
    inline_handler(inline_query=inline_query, bot=bot)


@bot.callback_query_handler(func=None)
def cqh(call):
    try:
        if not call.data:
            return telebot.CancelUpdate()

        parsed_data = {
            key: value[0]
            for key, value in urllib.parse.parse_qs(call.data, keep_blank_values=True).items()
        }

        track_id = parsed_data.get('track_id')
        if not track_id:
            return telebot.CancelUpdate()

        try:
            likes = int(parsed_data.get('like') or 1)
        except ValueError:
            likes = 1

        if likes < 1:
            likes = 1

        likes_new = likes + 1
        likes_text = f'{likes} ❤️'

        reply_markup = InlineKeyboardMarkup()
        reply_markup.row(
            InlineKeyboardButton(
                likes_text,
                callback_data=f'like={likes_new}&track_id={track_id}',
            )
        )
        reply_markup.row(
            InlineKeyboardButton('🔍 Другие сервисы', url=f'https://song.link/s/{track_id}'),
            InlineKeyboardButton('💚 Spotify', url=f'https://open.spotify.com/track/{track_id}'),
        )

        bot.edit_message_reply_markup(inline_message_id=call.inline_message_id, reply_markup=reply_markup)
        bot.answer_callback_query(callback_query_id=call.id, text='❤️ Like!')
    except Exception:
        logger.error('callback handler err', exc_info=True)
        return telebot.CancelUpdate()


def _start_thread(name, target):
    thread = threading.Thread(target=target, name=name, daemon=True)
    thread.start()
    return thread


def _shutdown(signum=None, frame=None):
    if not shutdown_event.is_set():
        logger.info("Shutting down..")
        shutdown_event.set()
        bot.stop_polling()


def _install_signal_handlers():
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _shutdown)
        except (ValueError, OSError):
            logger.debug(f"Signal {sig} handler was not installed.", exc_info=True)


def main():
    _install_signal_handlers()

    threads = [
        _start_thread("BotThread", bot_polling),
        _start_thread("WebThread", webserver_daemon),
    ]

    while not shutdown_event.is_set():
        dead_threads = [thread.name for thread in threads if not thread.is_alive()]
        if dead_threads:
            logger.error(f"Critical thread stopped: {', '.join(dead_threads)}")
            shutdown_event.set()
            return 1

        shutdown_event.wait(Settings.MAIN_THREAD_HEALTHCHECK_INTERVAL)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
