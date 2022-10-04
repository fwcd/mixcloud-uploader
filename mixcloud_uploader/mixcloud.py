import contextlib
import time
import requests
import webbrowser

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, quote_plus
from pathlib import Path
from tracklist.model import Tracklist
from threading import Thread
from typing import Optional

class Mixcloud:
    """A wrapper around the Mixcloud API."""

    API_BASE_URL = 'https://api.mixcloud.com'

    def __init__(self, access_token: str):
        self.access_token = access_token
    
    def request(self, method: str, endpoint: str, query: Optional[dict[str, str]]=None, files: Optional[dict]=None, data: Optional[dict]=None) -> requests.Response:
        """Performs an authenticated request against the API."""
        query = dict(query or {}, access_token=self.access_token)
        encoded_query = '&'.join(f'{quote_plus(k)}={quote_plus(v)}' for k, v in query.items())
        url = f'{Mixcloud.API_BASE_URL}{endpoint}?{encoded_query}'
        return requests.request(method, url, files=files, data=data)
    
    def cloudcasts(self, user: str='me') -> dict:
        """Fetches the given user's mixes."""
        return self.request('GET', f'/{user}/cloudcasts').json()
    
    def upload(
        self,
        audio_file_path: Path,
        name: str,
        artwork_path: Optional[Path]=None,
        description: Optional[str]=None,
        tags: Optional[list[str]]=None,
        tracks: Optional[Tracklist]=None,
    ):
        """Uploads a mix."""
        with open(audio_file_path, 'rb') as audio_file:
            with (open(artwork_path, 'rb') if artwork_path else contextlib.nullcontext()) as artwork_file:
                response = self.request(
                    'POST', '/upload/',
                    files={k: v for k, v in [
                        ('mp3', audio_file),
                        ('picture', artwork_file),
                    ] if v},
                    data={k: v for k, v in [
                        ('name', name),
                        ('description', description),
                        *((f'tags-{i}-tag', tag) for i, tag in enumerate(tags or [])),
                        *(section for i, track in enumerate(tracks.entries if tracks else []) for section in [
                            (f'sections-{i}-artist', track.artist),
                            (f'sections-{i}-song', track.title),
                            (f'sections-{i}-start_time', track.start_seconds),
                        ]),
                    ] if v}
                )
                response.raise_for_status()
                return response.json()
    
def authenticate_via_browser(client_id: str, client_secret: str) -> str:
    """Obtains an OAuth2 access token by authenticating via the browser."""

    callback_endpoint = '/callback'
    oauth_code = None

    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlparse(self.path)

            if url.path == callback_endpoint:
                query = parse_qs(url.query)

                if 'code' in query:
                    nonlocal oauth_code
                    oauth_code = query['code'][0]

                    def shutdown_soon():
                        time.sleep(1)
                        self.server.shutdown()

                    Thread(target=shutdown_soon).start()

                self.send_response(200)
            else:
                self.send_response(404)

    server = HTTPServer(('127.0.0.1', 0), RequestHandler)
    redirect_uri = f'http://localhost:{server.server_port}{callback_endpoint}'

    def launch_browser():
        # We delay execution to make sure that the server is actually running by then
        time.sleep(1)
        webbrowser.open(f'https://www.mixcloud.com/oauth/authorize?client_id={client_id}&redirect_uri={quote_plus(redirect_uri)}')

    print('==> Launching browser for authentication...')
    Thread(target=launch_browser).start()

    print('==> Waiting for callback...')
    server.serve_forever()

    if not oauth_code:
        raise RuntimeError('No OAuth code received!')

    print(f'==> Got code {oauth_code}, requesting OAuth access token...')
    access_token_url = f'https://www.mixcloud.com/oauth/access_token?client_id={client_id}&redirect_uri={quote_plus(redirect_uri)}&client_secret={client_secret}&code={oauth_code}'
    response = requests.get(access_token_url)
    response_fields = response.json()

    if 'access_token' in response_fields:
        return response_fields['access_token']
    else:
        raise RuntimeError(f'Could not fetch access token: {response.text}')
