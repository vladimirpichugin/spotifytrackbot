import spotipy


class MySpotify(spotipy.Spotify):
    def get_me(self):
        return self._get(
            "me"
        )

    def current_user_playing_track(self):
        return self._get(
            "me/player/currently-playing",
            market="TR"
        )

    def current_user_recently_played(self, limit=50, after=None, before=None):
        return self._get(
            "me/player/recently-played",
            limit=limit,
            after=None,
            before=None,
            market="TR"
        )
