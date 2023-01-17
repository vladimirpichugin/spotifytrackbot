# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>


class Settings:
    APP_NAME = 'SpotifyTrackBot'
    APP_VERSION = '1.0'
    APP_AUTHOR = 'Vladimir Pichugin vladimir@pichug.in'

    DEBUG = True
    DEBUG_TELEBOT = False
    WERKZEUG_LOGS = False
    DEBUG_FLASK = False

    BOT_TOKEN = ''
    BOT_TIMEOUT = 10
    BOT_INTERVAL = 3

    SPOTIFY_CLIENT_ID = ''
    SPOTIFY_CLIENT_SECRET = ''
    SPOTIFY_AUTHORIZE_URI = 'https://accounts.spotify.com/authorize'
    SPOTIFY_REDIRECT_URI = 'http://localhost/spotifytrackbot'
    SPOTIFY_SCOPE = ['user-read-currently-playing', 'user-read-recently-played']
    SPOTIFY_OAUTH_SALT = ''

    WEB_HOST = 'localhost'
    WEB_PORT = 80
    WEB_ALLOWED_HTTP_METHODS = ['OPTIONS', 'HEAD', 'GET', 'POST']
    WEB_CONTENT_TYPE = 'text/html; charset=utf-8'
    WEB_HEADERS = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': '*',
        'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Cache-Control',
        'Content-Security-Policy': 'default-src \'self\'',
        'Content-Security-Policy-Report-Only': '',
        'X-Powered-By': 'SpotifyTrackBot',
        'X-App-Author': 'Vladimir Pichugin <vladimir@pichug.in>'
    }

    L10N_RU_FILE = 'L10n/ru.json'

    MONGO = ''
    MONGO_DATABASE = 'spotifytrackbot'
    COLLECTIONS = {
        'clients': 'clients',
        'songs': 'songs'
    }
