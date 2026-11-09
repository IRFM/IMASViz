# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""Run one IMASViz session with its web service.

The construction is the one the MCP service already runs, in the order of
`QtVIZ_GUI.main()`: the preferences are read before the window (the theme is
one of them), the window is built, and **this** thread keeps the event loop --
`app.exec_()` -- because that is the thread every gesture is queued onto
through the `GuiDispatcher`, and a thread that does not own a widget must not
touch one. What changes over the MCP path is the transport: instead of the
`mcp` SDK's `streamable_http_app()` it is the Starlette app of `viz_web.server`
served by the same uvicorn, on the same daemon thread of its own event loop.

    python3 -m viz_web --port 8770                  # offscreen by default here (no display)
    python3 -m viz_web --host 0.0.0.0 --port 8771   # the interface and port, named

Then the browser is pointed at `http://127.0.0.1:8770`, and the page is the
REPL with a picture: the prompt runs the agent, its lines stream as they
come, and every request leaves what it drew -- one group per request in
the captures, closed until it is opened, the reports grouped the way
they are and named out of the folder they live in. The raw gestures are
the rarely used one, and so they sit in a closed section of the agent's
column, not in a column of their own.
"""

import argparse
import os
import signal
import sys
import threading
import time


def parseArguments(argv=None):
    """The command line of one web session."""
    parser = argparse.ArgumentParser(
        prog='viz_web',
        description='IMASViz driven from the browser, its window offscreen: '
                    'the agent and the raw gestures, its images on the page.')
    parser.add_argument('--host', default='127.0.0.1',
                        help='interface the web listens on (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8770,
                        help='port of the web (default: 8770)')
    parser.add_argument('--offscreen', action='store_true',
                        help='start with QT_QPA_PLATFORM=offscreen '
                             '(the point of the web: the IMASViz window keeps '
                             'off the screen)')
    parser.add_argument('--llm-url', dest='llm_url', default=None,
                        help='base URL of the local model, ending in /v1 '
                             '(default: the preferences\' AgentLLMEndpoint)')
    parser.add_argument('--llm-model', dest='llm_model', default=None,
                        help='model name to send (default: the preferences\' '
                             'AgentLLMModel, the endpoint\'s first '
                             '/v1/models entry when one is)')
    parser.add_argument('--llm-key', dest='llm_key', default=None,
                        help='API key for the endpoint (sent only when non-empty)')
    parser.add_argument('--max-turns', dest='max_turns', type=int, default=12,
                        help='the agent loop\'s turn limit (default: 12)')
    parser.add_argument('--shots', default=None,
                        help='directory the turns\' images and transcripts are '
                             'saved in (default: ~/.imasviz/web/shots)')
    return parser.parse_args(argv)


def buildClient(args):
    """The `Client` of this run: the LLM and its running parameters.

    The rule the REPL keeps -- an endpoint named without a model takes the
    endpoint's first `/v1/models` entry, a name sent the server does not
    hold is a refusal that costs a round-trip -- and without an endpoint the
    preferences stand, as in the in-app agent.
    """
    from imasviz.VizAgent.llm_client import LLMClient
    from viz_cli.session import Client

    client = LLMClient(endpoint=args.llm_url or None,
                       model=args.llm_model or None,
                       api_key=args.llm_key or None)
    if args.llm_model in (None, '') and args.llm_url:
        client.model = None
    return Client(client)


def buildSession(app, window, args):
    """The `WebSession` of this run: the core on the session's api, and the
    stack it drives, built on this thread -- the one that will keep the
    event loop, and the one every gesture is queued onto."""
    from imasviz.VizAgent.core import McpGuiCore
    from mcp_server.agent_mode import _apiOf
    from viz_web.web_session import WebSession

    shots = args.shots or os.path.expanduser('~/.imasviz/web/shots')
    core = McpGuiCore(main_window=window, api=_apiOf(window))
    return WebSession(app=app, window=window, core=core,
                      client=buildClient(args), shots_dir=shots,
                      max_turns=args.max_turns)


def serve(session, host, port):
    """The transport: one daemon thread, its own loop, its own socket.

    The same shape the MCP service runs on: uvicorn off the main thread,
    and the main thread left with the Qt event loop. The port's refusal is
    named, not swallowed."""
    from viz_web.server import buildApp
    import uvicorn

    config = uvicorn.Config(buildApp(session), host=host, port=port,
                            log_level='warning', lifespan='on')
    uv = uvicorn.Server(config)
    uv.install_signal_handlers = lambda: None
    threading.Thread(target=uv.run, name='viz-web-transport',
                     daemon=True).start()
    ready = time.time() + 8
    while not uv.started and time.time() < ready:
        time.sleep(0.05)
    if not uv.started:
        raise RuntimeError(
            'the web did not come up on %s:%s -- the port is held by another '
            'service, or the interface refused the bind.' % (host, port))
    return uv


def main(argv=None):
    """The entry: build the offscreen application, serve the web on its own
    thread, and keep the event loop on this one until it is closed."""
    args = parseArguments(argv)

    # Offscreen by default: the point of the web is that the IMASViz window
    # stays off the screen. Set before `buildApplication` builds the
    # `QApplication`, and only when there is no display to keep.
    if args.offscreen or not os.environ.get('DISPLAY'):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

    from imasviz.VizUtils import QVizGlobalOperations
    try:
        QVizGlobalOperations.checkEnvSettings()
    except SystemExit:
        raise ValueError(
            'the environment refused the session before any window: the line '
            'above names the variable it lacks. On this node the profile '
            'exports AL_VERSION, not IMAS_VERSION, so `module load '
            'IMAS-Python/2.3.0-…` before `python3 -m viz_web`, or start '
            'without VIZ_PRODUCTION=1.')

    from mcp_server.run import buildApplication
    app, window = buildApplication(
        args,
        banner='Welcome to Viz! The web is up on http://%s:%s.'
               % (args.host, args.port))
    session = buildSession(app, window, args)
    uv = serve(session, args.host, args.port)
    print('IMASViz web is up on http://%s:%s' % (args.host, args.port),
          flush=True)

    def _shutdown(*_args):
        """Ctrl+C takes the transport down first, then the session."""
        uv.should_exit = True
        window.close()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    code = app.exec_()
    from mcp_server.agent_mode import _settleWindow
    _settleWindow(window, app)
    return 0 if code is None else code
