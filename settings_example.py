# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>


class Settings:
    APP_NAME = 'SpotifyTrackBot'
    APP_VERSION = '1.1'

    DEBUG = True
    DEBUG_TELEBOT = False
    WERKZEUG_LOGS = False
    DEBUG_FLASK = False

    BOT_TOKEN = ''
    BOT_WORKER_THREADS = 4
    BOT_TIMEOUT = 10
    BOT_INTERVAL = 3
    BOT_LONG_POLLING_TIMEOUT = 20
    BOT_RESTART_DELAY = 10
    BOT_SKIP_PENDING = False
    BOT_ALLOWED_UPDATES = ['message', 'inline_query', 'callback_query']
    TELEGRAM_PROXY = ''

    SPOTIFY_CLIENT_ID = ''
    SPOTIFY_CLIENT_SECRET = ''

    SPOTIFY_AUTHORIZE_URI = 'https://accounts.spotify.com/authorize'
    SPOTIFY_REDIRECT_URI = 'https://pichug.in/api/spotifytrackbot/callback'
    SPOTIFY_SCOPE = ['user-read-currently-playing', 'user-read-recently-played']
    SPOTIFY_OAUTH_SALT = ''
    SPOTIFY_MARKET = 'TR'
    SPOTIFY_RECENTLY_PLAYED_LIMIT = 9
    SPOTIFY_REQUESTS_TIMEOUT = 5
    SPOTIFY_RETRIES = 3
    SPOTIFY_STATUS_RETRIES = 3
    SPOTIFY_BACKOFF_FACTOR = 0.3
    SPOTIFY_PROXY = ''

    WEB_HOST = '0.0.0.0'
    WEB_PORT = 80
    WEB_ALLOWED_HTTP_METHODS = ['OPTIONS', 'HEAD', 'GET', 'POST']
    WEB_CONTENT_TYPE = 'text/html; charset=utf-8'
    WEB_AUTH_ERROR_REDIRECT_URL = 'https://pichug.in/blank'
    WEB_AUTH_SUCCESS_REDIRECT_URL = 'https://pichug.in/blank?webapp=spotifytrackbot&msg=spotify_authorized'

    L10N_RU_FILE = 'L10n/ru.json'

    MONGO = ''
    MONGO_DATABASE = 'spotifytrackbot'
    COLLECTIONS = {
        'clients': 'clients'
    }
    MONGO_SERVER_SELECTION_TIMEOUT_MS = 5000

    MAIN_THREAD_HEALTHCHECK_INTERVAL = 5
