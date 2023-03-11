# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import os
import re
import datetime
import json
import uuid

from operator import itemgetter
from random import randint

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputTextMessageContent, InputMediaAudio, InlineQueryResultAudio, InlineQueryResultArticle

from spotipy import MemoryCacheHandler
from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyOauthError
from spotipy.exceptions import SpotifyException
from utils import MySpotify


from utils import get_auth_url, gen_state
from storage import *

from settings import Settings

from localization import L10n


def cmd_start(client, user):
    state = client.get('key')

    if not state:
        state = gen_state(client_id=user.id)
        client['key'] = state
        storage.save_client(client, user)

    if client.get('spotify_token_info'):
        text = L10n.get('linked')
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton('Try now', switch_inline_query=' ')
        )
    else:
        text = L10n.get('hello')
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton('🔑 Spotify', url=get_auth_url(state=state))
        )

    return text, markup


def cmd_logout(client, user):
    v = client.get('spotify_token_info', None)
    if v:
        client['spotify_token_info'] = None

    storage.save_client(client, user)

    text = L10n.get('logout')

    _, markup = cmd_start(client, user)

    return text, markup


def inline_handler(inline_query, bot):
    client = storage.get_client(inline_query.from_user)

    spotify_token_info = client.get('spotify_token_info')
    if not spotify_token_info:
        return bot.answer_inline_query(
            inline_query.id,
            [],
            is_personal=True,
            cache_time=1,
            switch_pm_text='Please authenticate',
            switch_pm_parameter='love'
        )

    cache_handler = MemoryCacheHandler(token_info=spotify_token_info)
    oauth_context = SpotifyOAuth(
        client_id=Settings.SPOTIFY_CLIENT_ID,
        client_secret=Settings.SPOTIFY_CLIENT_SECRET,
        redirect_uri=Settings.SPOTIFY_REDIRECT_URI,
        show_dialog=False,
        open_browser=False,
        cache_handler=cache_handler
    )

    validate_token = oauth_context.validate_token(token_info=spotify_token_info)
    if validate_token:
        cache_handler.save_token_to_cache(validate_token)

        client['spotify_token_info'] = validate_token
        storage.save_client(client)
    else:
        logger.debug(f'validate_token: {validate_token}')
        return bot.answer_inline_query(
            inline_query.id,
            [],
            is_personal=True,
            cache_time=1,
            switch_pm_text='Please authenticate',
            switch_pm_parameter='authenticate'
        )

    sp = MySpotify(auth_manager=oauth_context)

    if not client.get('user_info'):
        logger.debug('User info updated.')
        client['user_info'] = sp.get_me()
        storage.save_client(client)

    try:
        now_playing = sp.current_user_playing_track()

        before_dt = datetime.datetime.now()
        before_timestamp = int(before_dt.timestamp() * 1000)

        recently_played = sp.current_user_recently_played(limit=9, before=before_timestamp)
    except SpotifyException as err:
        logger.debug('err step A1', exc_info=True)
        msg = err.msg

        if 'User not registered in the Developer Dashboard' in msg:
            pass

        return bot.answer_inline_query(
            inline_query.id,
            [],
            is_personal=True,
            cache_time=1,
            switch_pm_text='Please authenticate',
            switch_pm_parameter='love'
        )
    except Exception:
        return bot.answer_inline_query(
            inline_query.id,
            [],
            is_personal=True,
            cache_time=1,
            switch_pm_text='Please authenticate',
            switch_pm_parameter='love'
        )

    items = recently_played.get('items')
    if now_playing and now_playing.get('item'):
        items.insert(0, {'track': now_playing.get('item')})

    lines = []
    for item in items:
        track = item.get('track')

        album = track.get('album')
        images = album.get('images')
        thumb_url = images[-1].get('url')

        track_id = track.get('id')
        name = track.get('name')

        artists = [artist.get('name') for artist in track.get('artists')]
        performer = ', '.join(artists)

        duration_ms = track.get('duration_ms')
        duration_sec = int(duration_ms / 1000)

        #link = track.get('external_urls').get('spotify')
        preview_url = track.get('preview_url')

        if preview_url:
            message_content = InputMediaAudio(
                thumb=thumb_url,
                title=name,
                performer=performer,
                duration=duration_sec,
                media=preview_url
            )

            reply_markup = InlineKeyboardMarkup()
            reply_markup.row(
                InlineKeyboardButton('❤️', callback_data=f'like=1&track_id={track_id}'),
                InlineKeyboardButton('Other', url=f'https://song.link/s/{track_id}'),
                InlineKeyboardButton('Spotify', url=f'https://open.spotify.com/track/{track_id}')
            )

            line = InlineQueryResultAudio(
                id=str(uuid.uuid4()),
                title=name,
                audio_url=preview_url,
                input_message_content=message_content,
                reply_markup=reply_markup,
                audio_duration=duration_sec,
                performer=performer
            )
        else:
            message_content = InputTextMessageContent(
                message_text=f'{name} - {performer}\n\nError: This song is not available :C'
            )

            reply_markup = InlineKeyboardMarkup()
            reply_markup.row(
                InlineKeyboardButton('❤️', callback_data=f'like=1&track_id={track_id}'),
                InlineKeyboardButton('Other', url=f'https://song.link/s/{track_id}'),
                InlineKeyboardButton('Spotify', url=f'https://open.spotify.com/track/{track_id}')
            )

            line = InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                input_message_content=message_content,
                reply_markup=reply_markup,
                title=name,
                description=performer,
                thumb_url=thumb_url
            )

        lines.append(line)

    bot.answer_inline_query(
        inline_query.id,
        lines,
        is_personal=True,
        cache_time=1
    )
