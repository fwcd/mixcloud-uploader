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
            if self.path == callback_endpoint:
                url = urlparse(self.path)
                query = parse_qs(url.query)

                nonlocal oauth_code
                oauth_code = query['code']

                self.send_response(200)
                self.server.shutdown()
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
        raise ValueError('No OAuth code received!')

    print('==> Requesting OAuth access token')
    response = requests.get(f'https://www.mixcloud.com/oauth/authorize?client_id={client_id}&redirect_uri={quote_plus(redirect_uri)}&client_secret={client_secret}&code={oauth_code}')
    response_fields = parse_qs(response.text)

    return response_fields['access_token']
