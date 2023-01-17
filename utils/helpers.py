# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import hashlib
import threading
from urllib.parse import urlencode

from settings import Settings


def run_threaded(name, func):
    job_thread = threading.Thread(target=func)
    job_thread.setName(f'{name}Thread')
    job_thread.start()


def gen_state(client_id) -> str:
    state = ' {up} '.join(str(_) for _ in [client_id, Settings.SPOTIFY_OAUTH_SALT])
    state = state.encode('utf-8')
    state = hashlib.sha256(state).hexdigest()

    return state


def get_auth_url(state) -> str:
    params = {
        'client_id': Settings.SPOTIFY_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': Settings.SPOTIFY_REDIRECT_URI,
        'state': state
    }

    params_str = urlencode(params)

    params_str += '&scope=' + '+'.join(Settings.SPOTIFY_SCOPE)

    url = Settings.SPOTIFY_AUTHORIZE_URI + '?' + params_str

    return url
