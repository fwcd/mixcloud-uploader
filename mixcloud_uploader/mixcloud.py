import json
import time
import requests
import webbrowser

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, quote_plus
from threading import Thread

class Mixcloud:
    """A wrapper around the Mixcloud API."""

    def __init__(self, access_token: str):
        self.access_token = access_token

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
    response_fields = json.loads(response.text)

    if 'access_token' in response_fields:
        return response_fields['access_token']
    else:
        raise RuntimeError(f'Could not fetch access token: {response.text}')
