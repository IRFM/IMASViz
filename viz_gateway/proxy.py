# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The reverse proxy, and the one route every request takes.

One route of the Starlette app answers every request, and one small pair comes
before it. A browser that opens the gateway has no token to name, so
`GET /login` offers a one-field form and `POST /login` checks it against the
catalog -- a token nobody holds is refused *by name*, in the words the catalog
says, with a 401 the page prints. The token that is held is written as the
`imasviz_token` cookie (`HttpOnly`), and the session continues on it: the
proxy route accepts the cookie it accepted all along, so a browser logs in once
and a script keeps the header. Then the proxy answers the request: the token
is asked of the request, the user resolved from the catalog, the base resolved
from the pool of local instances or the URL a remote user holds, and the
method, path and body forwarded, the hop-by-hop headers of the two sides kept
apart. The answer comes straight back: the event stream of an agent turn is
streamed as it arrives, the JSON of a gesture is answered whole, and a refusal
the backend names is the one the gateway prints, unaltered.

The `x-imasviz-user` header the gateway adds names the user a request came in
for, so the backend (and a log it keeps) can tell them apart even where the two
sides share one `127.0.0.1`.
"""

import html as _html
import json as _json

import httpx
from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse, Response, StreamingResponse
from starlette.routing import Route

_HOP_BY_HOP = {
    'host', 'content-length', 'connection', 'keep-alive',
    'proxy-authenticate', 'proxy-authorization', 'te', 'trailers',
    'transfer-encoding', 'upgrade', 'accept-encoding',
}
_STRIP_FROM_RESPONSE = {
    'content-length', 'content-encoding', 'transfer-encoding',
    'connection', 'keep-alive',
}


def _responseHeaders(headers):
    """The headers of the backend's answer, the framing of its wire stripped.

    `content-length` and `content-encoding` are recomputed (or absent) by this
    gateway when it answers, and a body that has been decoded already must not
    wear the header of the one it came from. `content-type` is kept: it is what
    the page reads to say `text/event-stream` and `application/json` apart.
    """
    return {name: value for name, value in headers.items()
            if name.lower() not in _STRIP_FROM_RESPONSE}


def extractToken(request):
    """The bearer token of a request, from its Authorization or its cookie.

    Either `Authorization: Bearer <token>` or an `imasviz_token` cookie. An
    `Authorization` that is not a bearer is ignored for the cookie, so a page
    that sets the header but no cookie and a header that spells nothing are
    both refused as having no token.
    """
    auth = request.headers.get('authorization', '')
    if auth.lower().startswith('bearer '):
        return auth.split(' ', 1)[1].strip()
    return request.cookies.get('imasviz_token')


async def _proxy(request, baseUrl, user):
    """The request to `baseUrl`, and its answer, as this gateway answers it.

    An event stream comes down as it is written; whatever else is read whole
    and returned. The two sides' headers are kept apart: what goes to the
    backend is what the client asked for minus the hop-by-hop, and what comes
    back is what the backend sent minus the framing of its wire.
    """
    url = baseUrl.rstrip('/') + request.url.path
    if request.url.query:
        url += '?' + request.url.query
    headers = {name: value for name, value in request.headers.items()
               if name.lower() not in _HOP_BY_HOP}
    headers['x-imasviz-user'] = user
    body = await request.body()

    client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=None),
                               follow_redirects=False)
    try:
        prepared = client.build_request(request.method, url, headers=headers,
                                        content=body if body else None)
        response = await client.send(prepared, stream=True)
    except Exception:
        await client.aclose()
        raise
    kind = (response.headers.get('content-type') or '').lower()

    if 'text/event-stream' in kind:
        headersOut = _responseHeaders(response.headers)

        async def stream():
            try:
                async for chunk in response.aiter_raw():
                    yield chunk
            finally:
                await response.aclose()
                await client.aclose()
        return StreamingResponse(stream(), status_code=response.status_code,
                                 media_type='text/event-stream',
                                 headers=headersOut)

    content = await response.aread()
    await response.aclose()
    await client.aclose()
    return Response(content, status_code=response.status_code,
                    media_type=response.headers.get('content-type')
                    or 'application/octet-stream',
                    headers=_responseHeaders(response.headers))


LOGIN_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IMASViz gateway</title>
<style>
body { font-family: sans-serif; background: #101418; color: #dde3e8; display: grid; place-items: center; margin: 0; min-height: 100vh; }
form { background: #1a2129; border-radius: 10px; padding: 2rem 2.3rem; box-shadow: 0 8px 32px rgba(0,0,0,.5); min-width: 24rem; }
h1 { margin: 0 0 .25rem; font-size: 1.3rem; font-weight: 600; }
.sub { margin: 0 0 1.2rem; color: #8fa1ad; font-size: .85rem; line-height: 1.5; }
label { display: block; font-size: .85rem; color: #8fa1ad; margin-bottom: .3rem; }
input[type=password] { width: 100%; box-sizing: border-box; padding: .55rem .7rem; font-size: 1rem; border-radius: 6px; border: 1px solid #39434d; background: #101418; color: #dde3e8; }
button { margin-top: 1.1rem; width: 100%; padding: .6rem; font-size: 1rem; border: 0; border-radius: 6px; background: #59a8c1; color: #0b0e12; font-weight: 600; cursor: pointer; }
.error { background: #3a1d21; border: 1px solid #7c3a40; color: #f0b6ba; border-radius: 6px; padding: .6rem .8rem; font-size: .85rem; margin-bottom: 1rem; white-space: pre-wrap; }
</style>
</head>
<body>
<form method="post" action="/login">
<h1>IMASViz gateway</h1>
<p class="sub">Name your token -- the one the gateway issued to you. It decides
which instance this session is served from, and nothing else.</p>
{error}
<label for="token">Token</label>
<input type="password" id="token" name="token" autofocus autocomplete="off" required>
<button type="submit">In</button>
</form>
</body>
</html>"""


def _loginPage(error=''):
    """The login page, and the refusal in it when the token was not held."""
    slot = '<div class="error">%s</div>' % _html.escape(error) if error else ''
    return LOGIN_PAGE.replace('{error}', slot)


async def _login(request, store):
    """The one entry a browser has: `GET /login` offers the form, `POST /login`
    checks it.

    The token comes from the form (what a browser sends), from a JSON body
    (what a script sends), or nowhere (refused as having none). On a token the
    catalog holds it is written as the `imasviz_token` cookie and the session
    continues on it; on one it does not, the words of the catalog's refusal are
    the page's, with a 401.
    """
    if request.method == 'GET':
        return Response(_loginPage(), media_type='text/html')
    body = await request.body()
    ctype = (request.headers.get('content-type') or '').lower()
    token = None
    if 'application/json' in ctype:
        try:
            data = _json.loads(body or b'{}')
        except Exception:
            data = None
        if isinstance(data, dict) and isinstance(data.get('token'), str):
            token = data['token']
    elif body:
        form = await request.form()
        value = form.get('token')
        if value is not None:
            token = str(value)
    try:
        store.entryFor(token)
    except ValueError as exc:
        return Response(_loginPage(str(exc)), status_code=401,
                        media_type='text/html')
    response = RedirectResponse('/', status_code=302)
    response.set_cookie('imasviz_token', str(token).strip(),
                        httponly=True, path='/', samesite='lax')
    return response


def buildApp(store, pool):
    """One Starlette app, the login pair and the route, the asks in order.

    The login pair comes first: a browser arrives with no token, so opening
    the gateway is where it is offered. The proxy route answers everything
    else: the token asked of the request, the user resolved from the catalog
    (refused by name when it is not), the base resolved from the pool of local
    instances or the URL a remote user holds (refused by name when it does not
    come up), and then the request the one this gateway proxies. Nothing here
    reaches a widget -- the one that reaches them is the pool, in the child
    process of the local instance.
    """

    async def handler(request):
        if (request.method == 'GET'
                and extractToken(request) is None
                and request.url.path in ('/', '/index.html')):
            return RedirectResponse('/login', status_code=302)
        token = extractToken(request)
        try:
            user, entry = store.entryFor(token)
        except ValueError as exc:
            return JSONResponse({'error': str(exc)}, status_code=401)
        if entry['kind'] == 'local':
            try:
                base = pool.ensure(user, entry)
            except ValueError as exc:
                return JSONResponse({'error': str(exc)}, status_code=503)
            pool.touch(user)
        else:
            base = entry['url']
        return await _proxy(request, base, user)

    async def login(request):
        # A bare (non-`request_response`) route expects the endpoint to
        # answer the `Response` itself, so the coroutine of `_login` is
        # awaited on its way out.
        return await _login(request, store)

    return Starlette(routes=[
        Route("/login", login, methods=['GET', 'POST']),
        Route("/{path:path}", handler,
              methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD',
                       'OPTIONS']),
    ])
