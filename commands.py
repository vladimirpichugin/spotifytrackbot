# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import datetime
import uuid

from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOauthError
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InlineQueryResultAudio,
    InputTextMessageContent,
)

from localization import L10n
from settings import Settings
from storage import storage
from utils.helpers import gen_state, get_auth_url
from utils.logging import logger
from utils.spotify import build_oauth_context, build_spotify_client


def _text(key, **kwargs):
    value = L10n.get(key)
    if kwargs and value:
        return value.format(**kwargs)
    return value


def cmd_start(client, user):
    state = client.get('key')

    if not state:
        state = gen_state(client_id=user.id)
        client['key'] = state
        storage.save_client(client, user)

    markup = InlineKeyboardMarkup()
    if client.get('spotify_token_info'):
        text = L10n.get('linked')
        markup.row(InlineKeyboardButton(_text('button_try'), switch_inline_query=' '))
    else:
        text = L10n.get('start')
        markup.row(InlineKeyboardButton(_text('button_spotify_auth'), url=get_auth_url(state=state)))

    return text, markup


def cmd_stop(client, user):
    if client.get('spotify_token_info'):
        client['spotify_token_info'] = None

    storage.save_client(client, user)

    text = L10n.get('stop')
    _, markup = cmd_start(client, user)

    return text, markup


def _answer_auth_required(bot, inline_query, text=None):
    return bot.answer_inline_query(
        inline_query.id,
        [],
        is_personal=True,
        cache_time=5,
        switch_pm_text=text or _text('auth_required'),
        switch_pm_parameter='authenticate',
    )


def _refresh_spotify_token(client, spotify_token_info):
    oauth_context = build_oauth_context(token_info=spotify_token_info)

    try:
        token_info = oauth_context.validate_token(token_info=spotify_token_info)
        logger.debug(f'validate_token: {token_info}')
    except SpotifyOauthError as err:
        if err.error_description and 'revoked' in err.error_description:
            return oauth_context, None
        raise

    if token_info:
        oauth_context.cache_handler.save_token_to_cache(token_info)
        client['spotify_token_info'] = token_info
        storage.save_client(client)
        return oauth_context, token_info

    client['spotify_token_info'] = None
    storage.save_client(client)
    return oauth_context, None


def _track_buttons(track_id):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(_text('button_like'), callback_data=f'like=1&track_id={track_id}')
    )
    markup.row(
        InlineKeyboardButton(_text('button_spotify'), url=f'https://open.spotify.com/track/{track_id}'),
        InlineKeyboardButton(_text('button_other_service'), url=f'https://song.link/s/{track_id}'),
    )
    return markup


def _iter_tracks(now_playing, recently_played):
    seen_track_ids = set()

    if now_playing and now_playing.get('item'):
        track = now_playing.get('item')
        track_id = track.get('id')
        if track_id:
            seen_track_ids.add(track_id)
            yield track

    for item in recently_played.get('items', []):
        track = item.get('track') if item else None
        if not track:
            continue

        track_id = track.get('id')
        if not track_id or track_id in seen_track_ids:
            continue

        seen_track_ids.add(track_id)
        yield track


def _build_inline_result(track):
    track_id = track.get('id')
    name = track.get('name') or _text('unknown_track')
    artists = track.get('artists') or []
    performer = artists[0].get('name') if artists else _text('unknown_artist')
    duration_sec = int((track.get('duration_ms') or 0) / 1000)
    preview_url = track.get('preview_url')
    reply_markup = _track_buttons(track_id)

    if preview_url:
        return InlineQueryResultAudio(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f'spotify-audio:{track_id}')),
            title=name,
            audio_url=preview_url,
            reply_markup=reply_markup,
            audio_duration=duration_sec,
            performer=performer,
        )

    message_content = InputTextMessageContent(
        message_text=_text('inline_track_message', name=name, performer=performer)
    )
    return InlineQueryResultArticle(
        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f'spotify-article:{track_id}')),
        input_message_content=message_content,
        reply_markup=reply_markup,
        title=name,
        description=performer,
    )


def inline_handler(inline_query, bot):
    client = storage.get_client(inline_query.from_user)

    spotify_token_info = client.get('spotify_token_info')
    if not spotify_token_info:
        return _answer_auth_required(bot, inline_query)

    try:
        oauth_context, spotify_token_info = _refresh_spotify_token(client, spotify_token_info)
    except SpotifyOauthError:
        logger.error('Spotify token validation failed.', exc_info=True)
        return _answer_auth_required(bot, inline_query, text=_text('auth_token_revoked'))
    except Exception:
        logger.error('Unexpected token validation error.', exc_info=True)
        return _answer_auth_required(bot, inline_query)

    if not spotify_token_info:
        return _answer_auth_required(bot, inline_query, text=_text('auth_token_revoked'))

    sp = build_spotify_client(auth_manager=oauth_context)

    try:
        if not client.get('user_info'):
            logger.debug('User info updated.')
            client['user_info'] = sp.get_me()
            storage.save_client(client)

        now_playing = sp.current_user_playing_track()
        before_timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
        recently_played = sp.current_user_recently_played(
            limit=Settings.SPOTIFY_RECENTLY_PLAYED_LIMIT,
            before=before_timestamp,
        )
    except SpotifyException as err:
        logger.debug('Spotify API error while preparing inline query.', exc_info=True)
        if 'User not registered in the Developer Dashboard' in err.msg:
            return _answer_auth_required(bot, inline_query)
        return _answer_auth_required(bot, inline_query)
    except Exception:
        logger.error('Unexpected inline query error.', exc_info=True)
        return _answer_auth_required(bot, inline_query)

    results = [_build_inline_result(track) for track in _iter_tracks(now_playing, recently_played)]

    bot.answer_inline_query(
        inline_query.id,
        results,
        is_personal=True,
        cache_time=5,
    )
