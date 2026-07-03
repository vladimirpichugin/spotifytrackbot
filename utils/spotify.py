import spotipy
from spotipy import MemoryCacheHandler
from spotipy.oauth2 import SpotifyOAuth

import settings
from settings import Settings


def get_scope():
    return " ".join(Settings.SPOTIFY_SCOPE)


def build_oauth_context(token_info=None):
    cache_handler = MemoryCacheHandler(token_info=token_info) if token_info else MemoryCacheHandler()

    if Settings.SPOTIFY_PROXY:
        proxies = {
            'http': Settings.SPOTIFY_PROXY,
            'https': Settings.SPOTIFY_PROXY
        }
    else:
        proxies = None

    return SpotifyOAuth(
        client_id=Settings.SPOTIFY_CLIENT_ID,
        client_secret=Settings.SPOTIFY_CLIENT_SECRET,
        redirect_uri=Settings.SPOTIFY_REDIRECT_URI,
        scope=get_scope(),
        show_dialog=False,
        open_browser=False,
        cache_handler=cache_handler,
        proxies=proxies,
        requests_timeout=Settings.SPOTIFY_REQUESTS_TIMEOUT,
    )


def build_spotify_client(auth_manager):
    if Settings.SPOTIFY_PROXY:
        proxies = {
            'http': Settings.SPOTIFY_PROXY,
            'https': Settings.SPOTIFY_PROXY
        }
    else:
        proxies = None

    return MySpotify(
        auth_manager=auth_manager,
        proxies=proxies,
        requests_timeout=Settings.SPOTIFY_REQUESTS_TIMEOUT,
        retries=Settings.SPOTIFY_RETRIES,
        status_retries=Settings.SPOTIFY_STATUS_RETRIES,
        backoff_factor=Settings.SPOTIFY_BACKOFF_FACTOR,
    )


class MySpotify(spotipy.Spotify):
    def get_me(self):
        return self._get(
            "me"
        )

    def current_user_playing_track(self):
        return self._get(
            "me/player/currently-playing",
            market=Settings.SPOTIFY_MARKET
        )

    def current_user_recently_played(self, limit=50, after=None, before=None):
        return self._get(
            "me/player/recently-played",
            limit=limit,
            after=after,
            before=before,
            market=Settings.SPOTIFY_MARKET
        )
