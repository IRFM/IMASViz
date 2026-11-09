# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The routes the page talks to: the agent streamed, the gestures answered.

One Starlette application, one `WebSession`. Every route is refused by name
where it cannot answer -- a refusal is a value the page prints, in the words
the application names, and never a silence the user has to guess at.

The agent's turn is a stream, not a reply: `POST /api/agent` answers a
`text/event-stream`, and the lines of the transcript come down as the loop
writes them, the images at the end. The loop itself runs on a thread of its
own (the LLM call takes seconds and the page must stay responsive while it
does), and the line it feeds into a queue is drained by the page -- the
same signal-into-worker pattern the REPL runs, read from the socket instead
of the console.

Every gesture of the core is answered by `POST /api/tool` through the
session's `callGesture`, which is the same call the agent makes: a named
refusal reads the same in the JSON the page shows and in the transcript a
turn leaves. Nothing here reaches the widgets directly -- the one that
reaches them is the `GuiDispatcher`, on the GUI thread.
"""

import base64
import json
import os
import queue
import threading

from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

_HERE = os.path.dirname(os.path.abspath(__file__))
_INDEX = os.path.join(_HERE, 'static', 'index.html')


def _default(o):
    """One value of a gesture's answer, made JSON.

    An array becomes its list, a scalar its number, a byte string its
    base64; whatever still cannot be told is told as it is named. The
    core's answers are mostly plain, but `get_signal` is the one that reads
    raw arrays, so the page gets the shape it drew, not a type error.
    """
    import numpy as np
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (bytes, bytearray)):
        return base64.b64encode(o).decode('ascii')
    return str(o)


def _jsonable(value):
    try:
        return json.loads(json.dumps(value, default=_default))
    except (TypeError, ValueError):
        return value if isinstance(value, str) else str(value)


def buildApp(session):
    """The one Starlette app of one `WebSession`, with every route.

    Each handler closes over the session the app was built for: one page,
    one session, the same bookkeeping the application sees on screen, which
    is the answer the tools panel and the *Windows* menu read.
    """
    # ---------------------------------------------------------------- the page

    async def index(request):
        if not os.path.isfile(_INDEX):
            return JSONResponse(
                {'error': 'the page is not where it is named: %s' % _INDEX},
                status_code=500)
        with open(_INDEX, 'r', encoding='utf-8') as f:
            return Response(f.read(), media_type='text/html; charset=utf-8')

    # ------------------------------------------------------------------- health

    async def health(request):
        cases = _jsonable(session.dispatcher.call(session.core.list_cases))
        return JSONResponse({
            'ok': True,
            'version': _version(),
            'llm': session.llmFields(),
            'turns': len(session.turns),
            'cases': cases,
        })

    # -------------------------------------------------------------------- tools

    async def tools(request):
        from imasviz.VizAgent.tools import TOOLS
        return JSONResponse({
            'tools': [{
                'name': one['function']['name'],
                'description': one['function']['description'],
                'parameters': one['function']['parameters'],
            } for one in TOOLS],
        })

    # -------------------------------------------------------------------- agent

    async def runAgent(request):
        body = await request.json()
        prompt = (body or {}).get('prompt') or ''
        if not prompt.strip():
            return JSONResponse(
                {'error': 'no prompt: name what to ask.'}, status_code=400)

        out = queue.Queue()

        def worker():
            try:
                record = session.runTurn(prompt, onLine=lambda line: out.put(('line', line)))
                out.put(('done', record))
            except Exception as e:
                out.put(('error', str(e)))

        threading.Thread(target=worker, daemon=True).start()

        def stream():
            yield _sse('begin', {'prompt': prompt, 'turn': len(session.turns) + 1})
            while True:
                kind, payload = out.get()
                if kind == 'line':
                    yield _sse('line', {'text': payload})
                elif kind == 'done':
                    yield _sse('done', _turnEvent(payload))
                    break
                else:
                    yield _sse('done', {'error': payload})
                    break

        return StreamingResponse(
            stream(), media_type='text/event-stream',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

    async def stopAgent(request):
        session.stop()
        return JSONResponse({'stop': 'asked; the loop stops at the next turn'})

    # --------------------------------------------------------------------- tool

    async def tool(request):
        body = await request.json()
        name = (body or {}).get('name')
        args = (body or {}).get('args') or {}
        if not name:
            return JSONResponse(
                {'error': 'no gesture name: name one from /api/tools.'},
                status_code=400)
        answer = session.callGesture(name, args)
        if answer['error'] is not None:
            return JSONResponse(answer, status_code=400)
        return JSONResponse({'name': name, 'result': _jsonable(answer['result'])})

    # -------------------------------------------------------------------- turns

    async def turnList(request):
        return JSONResponse({'turns': [_turnSummary(one) for one in session.turns]})

    async def turnOne(request):
        number = _turnNumber(request)
        record = next((one for one in session.turns if one['n'] == number), None)
        if record is None:
            return JSONResponse(
                {'error': 'no such turn: this session holds %d.'
                          % len(session.turns)}, status_code=404)
        return JSONResponse(record)

    async def shot(request):
        number = _turnNumber(request)
        record = next((one for one in session.turns if one['n'] == number), None)
        name = request.path_params['name']
        if record is None or name not in record['image_files']:
            return JSONResponse(
                {'error': 'no such image on turn %s: it holds %s'
                          % (number, record and record['image_files'] or [])},
                status_code=404)
        path = os.path.join(record['dir'], name)
        if not os.path.isfile(path):
            return JSONResponse({'error': 'the image is not on disk: %s' % name},
                                status_code=404)
        with open(path, 'rb') as f:
            return Response(f.read(), media_type='image/png')

    # ------------------------------------------------------------------ reports

    async def reportList(request):
        # The names the reports folder holds, by name: whatever turn or
        # session wrote them (the page fills its section from this at
        # load and after every request, because the folder is where a
        # report either is or is not -- and the page names that folder,
        # so a report the user asked for that is not among these names
        # is one a tool did not write there). A subdirectory is not a
        # report: the listing keeps the files. The empty list while the
        # folder does not exist yet -- the state before the core's first
        # write, and the one a test points the session at a fresh HOME
        # for.
        folder = session.reportsFolder()
        names = [name for name in sorted(session.reportsOnDisk())
                 if name.endswith('.html')
                 and os.path.isfile(os.path.join(folder, name))]
        return JSONResponse({'folder': folder, 'reports': names})

    async def report(request):
        name = request.path_params['name']
        if os.sep in name or '/' in name or '\\' in name or name.startswith('.'):
            return JSONResponse(
                {'error': 'a report name is a file, not a place: name one.'},
                status_code=400)
        base = session.reportsFolder()
        path = os.path.realpath(os.path.join(base, name))
        if not path.startswith(base + os.sep) or not os.path.isfile(path):
            return JSONResponse(
                {'error': 'no such report: %r (the folder holds the ones '
                          'the core wrote).' % name}, status_code=404)
        with open(path, 'r', encoding='utf-8') as f:
            return Response(f.read(), media_type='text/html; charset=utf-8')

    # --------------------------------------------------------------------- /llm

    async def llmGet(request):
        return JSONResponse(session.llmFields())

    async def llmSet(request):
        body = await request.json()
        field = (body or {}).get('field')
        value = (body or {}).get('value')
        if field is None or value is None:
            return JSONResponse(
                {'error': 'name the field and its value: {field, value}.'},
                status_code=400)
        try:
            setLlmField(session, field, value)
        except ValueError as e:
            return JSONResponse({'error': str(e)}, status_code=400)
        return JSONResponse(session.llmFields())

    return Starlette(routes=[
        Route('/', index),
        Route('/api/health', health, methods=['GET']),
        Route('/api/tools', tools, methods=['GET']),
        Route('/api/agent', runAgent, methods=['POST']),
        Route('/api/agent/stop', stopAgent, methods=['POST']),
        Route('/api/tool', tool, methods=['POST']),
        Route('/api/turns', turnList, methods=['GET']),
        Route('/api/turns/{n}', turnOne, methods=['GET']),
        Route('/api/turns/{n}/shots/{name}', shot, methods=['GET']),
        Route('/api/reports', reportList, methods=['GET']),
        Route('/api/reports/{name}', report, methods=['GET']),
        Route('/api/llm', llmGet, methods=['GET']),
        Route('/api/llm', llmSet, methods=['POST']),
    ])


# --------------------------------------------------------------------- helpers

def _version():
    try:
        from imasviz.VizUtils import QVizGlobalValues
        return QVizGlobalValues.IMAS_VIZ_VERSION
    except Exception:
        return 'unknown'


def _turnNumber(request):
    raw = request.path_params['n']
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ValueError('turn %r is not a number' % raw)


def _turnEvent(record):
    """The `done` event: what the page renders, and where the history holds it.

    `reports` is the record's own: the names the reports folder did not
    hold before the turn and holds after it -- the page fills the Reports
    section from it, the way it fills the images from `images`."""
    return {'turn': record['n'],
            'prompt': record['prompt'],
            'error': record['error'],
            'dir': record['dir'],
            'refusals': record['refusals'],
            'images': record['images'],
            # The address of every picture of this turn -- the page's
            # Focus and Screenshot buttons take that name to focus_window
            # and get_screenshot.
            'image_windows': record.get('image_windows', []),
            'reports': record.get('reports') or []}


def _turnSummary(record):
    """One line of the turn list, with the pictures and their addresses.

    `image_windows` is what the page rebuilds its gallery from on load:
    every picture of every turn, with the name the buttons send to
    `focus_window` and `get_screenshot` -- the pictures are on disk under
    the turn's `dir`, and `/api/turns/{n}/shots/{name}` serves them.
    """
    return {'n': record['n'],
            'prompt': record['prompt'],
            'error': record['error'],
            'image_files': record['image_files'],
            'image_windows': record.get('image_windows', []),
            'reports': record.get('reports') or [],
            'dir': record['dir']}


def _sse(event, payload):
    """One line of the stream, in the shape the page parses: `event:` and
    a single `data:` line holding JSON -- so a newline in a transcript
    line cannot split the block the reader is between."""
    return 'event: %s\ndata: %s\n\n' % (event, json.dumps(payload))


def setLlmField(session, field, value):
    """Set one of the /llm fields, on the session and, for the three the
    GUI reads too, in the one preferences file it and the REPL share.

    The rules are the REPL's, imported rather than recopied: a field the
    client does not answer, an endpoint that is not an http URL, and each
    number it rejects, are refused by name.
    """
    from imasviz.VizUtils import QVizPreferences
    from viz_cli.commands import LLM_FIELDS, LLM_FILE_FIELDS

    if field not in LLM_FIELDS:
        raise ValueError(
            'this client does not answer the field "%s": its fields are %s.'
            % (field, ', '.join(LLM_FIELDS)))

    if field == 'endpoint':
        if not value.startswith(('http://', 'https://')):
            raise ValueError('%r is not an endpoint: name it as '
                             'http://host:port/v1.' % value)
        persist = LLM_FILE_FIELDS['endpoint']
        QVizPreferences.persist(**{persist: value})
        setattr(QVizPreferences, persist, value)
        session.client.apply()
    elif field == 'model':
        kept = '' if value == 'auto' else value
        persist = LLM_FILE_FIELDS['model']
        QVizPreferences.persist(**{persist: kept})
        setattr(QVizPreferences, persist, kept)
        session.client.apply()
    elif field == 'key':
        persist = LLM_FILE_FIELDS['key']
        QVizPreferences.persist(**{persist: value})
        setattr(QVizPreferences, persist, value)
        session.client.apply()
    elif field == 'max_turns':
        number = _number(field, value, min=1)
        session.max_turns = number
    elif field == 'temperature':
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError('%r is not a temperature: name it as a number.'
                             % value)
        if not 0.0 <= number <= 2.0:
            raise ValueError('%s is outside 0 to 2, the range the endpoints '
                             'here take.' % value)
        session.client.temperature = number
    elif field == 'max_tokens':
        session.client.max_tokens = _number(field, value, min=1)


def _number(field, value, min=1):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError('%r is not a number for %s: name it as an integer.'
                         % (value, field))
    if number < min:
        raise ValueError('%s is outside the range the loop takes: %d and up.'
                         % (value, min))
    return number
