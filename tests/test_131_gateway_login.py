# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The login pair, and the one a browser arrives through.

The proxy route assumes a token is already named; a browser has none, so the
gateway offers it. These tests pin that path: `GET /` with no token is handed
the login page, `POST /login` checks the form against the catalog (refused by
name, in the catalog's own words, when the token is not held), and the token
that is held is written as the `imasviz_token` cookie, which the proxy route
then carries the session on -- the last test drives that with a real backend
served by uvicorn, the same shape `test_128` uses.
"""

import asyncio
import socket
import threading
import time

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient
import pytest

from viz_gateway.proxy import buildApp
from viz_gateway.spawner import Pool
from viz_gateway.userstore import UserStore


def _freePort():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def _stubApp():
    async def health(request):
        return JSONResponse({'ok': True, 'who': 'stub'})
    return Starlette(routes=[Route('/api/health', health)])


@pytest.fixture
def client(tmp_path):
    """One gateway app: the catalog, a pool a remote user never touches, and
    a remote user pointing at the stub -- the login path only needs the
    catalog, and the one proxy test needs the stub behind it."""
    port = _freePort()
    config = uvicorn.Config(_stubApp(), host='127.0.0.1', port=port,
                            log_level='error')
    uv = uvicorn.Server(config)
    uv.install_signal_handlers = lambda: None

    def _serve():
        try:
            asyncio.run(uv.serve())
        except Exception:  # torn down at the end of the module
            pass

    thread = threading.Thread(target=_serve, daemon=True, name='login-stub')
    thread.start()
    deadline = time.time() + 8
    while not uv.started and time.time() < deadline:
        time.sleep(0.05)
    if not uv.started:
        raise RuntimeError('the stub backend did not start on port %s' % port)

    store = UserStore(str(tmp_path / 'gateway'))
    token = store.issue('alice', 'remote',
                        url='http://127.0.0.1:%d' % port)
    pool = Pool(maxUsers=2, spawn=lambda *a: None, health=lambda *a: None)
    return TestClient(buildApp(store, pool), base_url='http://gateway'), token


def test_opening_the_gateway_with_no_token_offers_the_login(client):
    client, _token = client
    answer = client.get('/', follow_redirects=False)
    assert answer.status_code == 302
    assert answer.headers['location'] == '/login'


def test_the_login_page_is_a_one_field_form(client):
    client, _token = client
    answer = client.get('/login')
    assert answer.status_code == 200
    assert 'text/html' in answer.headers['content-type']
    assert 'name="token"' in answer.text
    assert 'action="/login"' in answer.text


def test_login_with_a_token_the_catalog_does_not_hold_is_refused_by_name(client):
    client, _token = client
    answer = client.post('/login', data={'token': 'no-such-token-at-all'})
    assert answer.status_code == 401
    text = answer.text
    assert 'unknown token' in text
    assert 'no-such-token-at-all' in text
    # names the user the catalog does hold (its quotes are HTML-escaped to
    # &quot; in the page, so ask the bare name)
    assert 'alice' in text


def test_login_with_no_token_is_refused(client):
    client, _token = client
    answer = client.post('/login', data={})
    assert answer.status_code == 401
    assert 'no token' in answer.text


def test_login_with_the_right_token_sets_the_cookie_and_redirects(client):
    client, token = client
    answer = client.post('/login', data={'token': token},
                         follow_redirects=False)
    assert answer.status_code == 302
    assert answer.headers['location'] == '/'
    cookie = ', '.join(answer.headers.get_list('set-cookie'))
    assert 'imasviz_token=' in cookie
    assert 'httponly' in cookie.lower()
    assert 'path=/' in cookie.lower()


def test_login_accepts_a_json_body_too(client):
    """A script can log in without a form: `{"token": "..."}` gets the same
    cookie as the page does."""
    client, token = client
    answer = client.post('/login', json={'token': token},
                         follow_redirects=False)
    assert answer.status_code == 302
    cookie = ', '.join(answer.headers.get_list('set-cookie'))
    assert 'imasviz_token=' in cookie


def test_after_login_the_cookie_carries_the_session_to_the_backend(client):
    client, token = client
    login = client.post('/login', data={'token': token},
                        follow_redirects=False)
    cookie = ', '.join(login.headers.get_list('set-cookie'))
    name, _, value = cookie.partition(';')[0].partition('=')
    assert name == 'imasviz_token'
    answer = client.get('/api/health',
                        headers={'cookie': 'imasviz_token=%s' % value})
    assert answer.status_code == 200
    assert answer.json() == {'ok': True, 'who': 'stub'}
