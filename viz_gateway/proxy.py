# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The reverse proxy, and the one route every request takes.

One route of the Starlette app answers every request. First it asks the catalog
what user the bearer token holds -- a token nobody holds is refused *by name*,
in the words the catalog says, with a 401 the page prints. Then it reaches the
user's backend -- the base of the local instance the pool started, or the URL a
remote user holds -- and forwards the method, path, and body, the hop-by-hop
headers of the two sides kept apart. The answer comes straight back: the
event stream of an agent turn is streamed as it arrives, the JSON of a gesture
is answered whole, and a refusal the backend names is the one the gateway
prints, unaltered.

The `x-imasviz-user` header the gateway adds names the user a request came in
for, so the backend (and a log it keeps) can tell them apart even where the two
sides share one `127.0.0.1`.
"""

import httpx
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response, StreamingResponse
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


def buildApp(store, pool):
    """One Starlette app, one route, the asks it answers in order.

    The token is asked of the request, the user resolved from the catalog
    (refused by name when it is not), the base resolved from the pool of local
    instances or the URL a remote user holds (refused by name when it does not
    come up), and then the request is the one this gateway proxies. Nothing
    here reaches a widget -- the one that reaches them is the pool, in the
    child process of the local instance.
    """

    async def handler(request):
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

    return Starlette(routes=[
        Route("/{path:path}", handler,
              methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD',
                       'OPTIONS']),
    ])
