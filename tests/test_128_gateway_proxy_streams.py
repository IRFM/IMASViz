# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The gateway's reverse proxy: the one route, the asks it answers in order.

A real backend stub served by uvicorn on a real loopback socket is what the
gateway proxies to, so the whole path is the one the production `viz_web`
takes: a request in, a bearer token, an entry the catalog resolves (refused by
name when it does not), the base it reaches, and the answer that comes back.
The agent's event stream is the one that must arrive as it is written, and the
token is the one that says which user this request is for, or the refusal that
names it.
"""

import asyncio
import socket
import threading
import time

import pytest
import uvicorn

from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from viz_gateway.proxy import buildApp
from viz_gateway.spawner import Pool
from viz_gateway.userstore import UserStore


def _freePort():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def _stubApp():
    """The shape of the `viz_web` backend, minus the Qt: health, the agent
    stream, the page, and one route that says back the user it was told."""

    async def health(request):
        return JSONResponse({'ok': True, 'who': 'stub'})

    async def agent(request):
        async def events():
            yield 'event: begin\ndata: {}\n\n'
            yield 'event: line\ndata: {"text":"one"}\n\n'
            yield 'event: line\ndata: {"text":"two"}\n\n'
        return StreamingResponse(events(), media_type='text/event-stream')

    async def index(request):
        return Response('<html>stub</html>', media_type='text/html')

    async def echoUser(request):
        return Response(request.headers.get('x-imasviz-user', ''),
                        media_type='text/plain')

    return Starlette(routes=[
        Route('/api/health', health),
        Route('/api/agent', agent, methods=['POST']),
        Route('/echo-user', echoUser),
        Route('/', index),
    ])


@pytest.fixture(scope='module')
def stubBackend():
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

    thread = threading.Thread(target=_serve, daemon=True,
                              name='gateway-test-stub')
    thread.start()
    deadline = time.time() + 8
    while not uv.started and time.time() < deadline:
        time.sleep(0.05)
    if not uv.started:
        raise RuntimeError('the stub backend did not start on port %s' % port)
    yield 'http://127.0.0.1:%d' % port
    uv.should_exit = True
    thread.join(timeout=4)


@pytest.fixture
def proxy(stubBackend, tmp_path):
    store = UserStore(str(tmp_path / 'gateway'))
    token = store.issue('alice', 'remote', url=stubBackend)
    # A pool a remote user never touches: its asks are not the ones a test here makes.
    pool = Pool(maxUsers=2, spawn=lambda *a, **k: None,
                health=lambda *a: None)
    client = TestClient(buildApp(store, pool), base_url='http://gateway')
    return client, token


def test_health_is_proxied_whole(proxy):
    client, token = proxy
    answer = client.get('/api/health',
                        headers={'authorization': 'Bearer %s' % token})
    assert answer.status_code == 200
    assert answer.json() == {'ok': True, 'who': 'stub'}


def test_the_agent_event_stream_is_passed_through(proxy):
    client, token = proxy
    answer = client.post('/api/agent', json={'prompt': 'x'},
                         headers={'authorization': 'Bearer %s' % token})
    assert answer.status_code == 200
    assert answer.headers['content-type'].startswith('text/event-stream')
    body = answer.text
    assert 'event: begin' in body
    # The two transcript lines, in the order the stub wrote them.
    assert body.index('"one"') < body.index('"two"')


def test_the_gateway_names_the_user_to_the_backend(proxy):
    client, token = proxy
    answer = client.get('/echo-user',
                        headers={'authorization': 'Bearer %s' % token})
    assert answer.status_code == 200
    assert answer.text.strip() == 'alice'


def test_the_page_is_reached(proxy):
    client, token = proxy
    answer = client.get('/', headers={'authorization': 'Bearer %s' % token})
    assert answer.status_code == 200
    assert 'stub' in answer.text


def test_a_request_with_no_token_is_refused_by_name(proxy):
    client, _token = proxy
    answer = client.get('/api/health')
    assert answer.status_code == 401
    assert 'no token' in answer.json()['error']


def test_an_unknown_token_is_refused_naming_what_it_holds(proxy):
    client, _token = proxy
    answer = client.get('/api/health', headers={'authorization': 'Bearer no-such'})
    assert answer.status_code == 401
    error = answer.json()['error']
    assert 'no-such' in error
    assert '"alice"' in error  # names the user the catalog does hold