# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Run one IMASViz session with its MCP service.

The application stays the main program: the same construction order as
`QtVIZ_GUI.main()` (preferences, then theme, then the window), and the
window is shown. What is added is the tool service: `FastMCP` over the
official SDK's `streamable_http_app()`, served by uvicorn in a daemon
thread of its own event loop. The SDK answers tool calls from that
thread, and every tool routes through the `GuiDispatcher`, so the widget
tree is only ever touched from the GUI thread -- the layout chosen over
`qasync`: no foreign event loop around the Qt one, and the same
`Signal`-and-`Event` hand-off a `QThread` would use.

    python -m mcp_server --port 8765

and any MCP client pointed at `http://127.0.0.1:8765/mcp`, for example
in a Qwen Code configuration:

    { "mcpServers": { "imasviz": {
          "url": "http://127.0.0.1:8765/mcp" } } }

The refusal of the port is named, not swallowed.

One-shot agent mode, for a node without a display: the prompt after
`--agent` is asked of the in-app agent on a local model, and what it
drew is saved as PNGs (see `mcp_server/agent_mode.py`):

    python -m mcp_server --agent "Ouvre le cas …, trace …" \
        --llm-url http://127.0.0.1:8080/v1 \
        [--llm-model NAME] [--llm-key KEY] \
        [--max-turns 8] [--shots ./agent_shots]

It runs offscreen, exits 0 when the loop answered and 1 when it refused,
and serving the MCP service does not happen on that path.
"""

import argparse
import os
import signal
import sys
import threading
import time


def parseArguments(argv=None):
    """The command line of one session service."""
    parser = argparse.ArgumentParser(
        prog='mcp_server',
        description='IMASViz driven by name, over the official MCP SDK: '
                    'the application stays the main program and serves '
                    'its tools.')
    parser.add_argument('--host', default='127.0.0.1',
                        help='interface the /mcp endpoint listens on '
                             '(default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8765,
                        help='port of the /mcp endpoint (default: 8765)')
    parser.add_argument('--offscreen', action='store_true',
                        help='start with QT_QPA_PLATFORM=offscreen, for a '
                             'node without a display')
    parser.add_argument('--agent', default=None, metavar='PROMPT',
                        help='one-shot: run this prompt through the in-app '
                             'agent, offscreen, then save what it drew -- '
                             'no MCP service is served on this path '
                             '(see --llm-url, --shots)')
    parser.add_argument('--llm-url', dest='llm_url', default=None,
                        help='base URL of the local model, ending in /v1 '
                             '(default: the preferences\' '
                             'AgentLLMEndpoint, '
                             'http://127.0.0.1:11434/v1)')
    parser.add_argument('--llm-model', dest='llm_model', default=None,
                        help='model name to send (default: the '
                             'preferences\' AgentLLMModel when no '
                             '--llm-url is named, the endpoint\'s first '
                             '/v1/models entry when one is -- an empty '
                             'name forces the same)')
    parser.add_argument('--llm-key', dest='llm_key', default=None,
                        help='API key for the endpoint (sent only when '
                             'non-empty)')
    parser.add_argument('--max-turns', dest='max_turns', type=int,
                        default=8,
                        help='the agent loop\'s turn limit (default: 8)')
    parser.add_argument('--shots', default='agent_shots',
                        help='directory the agent\'s PNGs and its '
                             'transcript are saved in (default: '
                             'agent_shots, created if absent; a relative '
                             'path counts from the working directory)')
    return parser.parse_args(argv)


def buildApplication(args, banner=None):
    """The GUI, in the order of `QtVIZ_GUI.main()`.

    The preferences are read before the window (a theme is one of them,
    and a window built under the desktop's own palette paints its first
    frame in colours the user did not ask for); the window is shown so
    the service drives one the user can watch. `banner` is the line the
    log panel gets as a greeting: the one the MCP path says by default,
    or the one the caller spells (the agent path names its prompt and
    its output directory instead of a port that never opens).
    """
    from PySide6.QtWidgets import QApplication
    from imasviz.VizUtils import (QVizGlobalOperations, QVizPreferences)
    from imasviz.VizGUI.VizGuiCustomization import QVizStyle
    from imasviz.VizGUI.QtVIZ_GUI import QVizMainWindow
    import logging

    app = QApplication(['IMASViz'])
    QVizGlobalOperations.checkEnvSettings()
    QVizPreferences().build()
    QVizStyle.applyToApplication(app)
    window = QVizMainWindow()
    logging.getLogger('logPanel').info(
        banner or
        'Welcome to Viz! The MCP service is up on %s:%s.'
        % (args.host, args.port))
    window.show()
    return app, window


def serveTools(window, host, port):
    """The transport: one daemon thread, its own loop, its own socket."""
    from mcp_server.core import McpGuiCore
    from mcp_server.dispatcher import GuiDispatcher
    from mcp_server.tools import buildServer
    import uvicorn

    core = McpGuiCore(main_window=window)
    dispatcher = GuiDispatcher()
    server = buildServer(core, dispatcher, name='imasviz')

    config = uvicorn.Config(server.streamable_http_app(), host=host,
                            port=port, log_level='warning',
                            lifespan='on')
    uv = uvicorn.Server(config)
    uv.install_signal_handlers = lambda: None
    thread = threading.Thread(target=uv.run, name='mcp-transport',
                              daemon=True)
    thread.start()

    ready = time.time() + 8
    while not uv.started and time.time() < ready:
        time.sleep(0.05)
    if not uv.started:
        raise RuntimeError(
            'the MCP service did not start on %s:%s -- the port is held '
            'by another service, or the interface refused the bind'
            % (host, port))
    return uv


def main(argv=None):
    """The entry point: one prompt and its images, or the session and its
    service until the window closes."""
    args = parseArguments(argv)

    if args.agent is not None:
        # One-shot agent mode: offscreen by definition (a node without a
        # display is what it is for), and the refusal -- an empty prompt,
        # an endpoint that will not answer, a snapshot that will not
        # render -- is named out loud before the exit code says 1.
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from mcp_server.agent_mode import runAgentMode
        try:
            return runAgentMode(args)
        except Exception as e:
            print('REFUSAL — %s' % e, file=sys.stderr)
            return 1

    if args.offscreen:
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

    app, window = buildApplication(args)
    uv = serveTools(window, args.host, args.port)
    print('IMASViz is serving its tools on http://%s:%s/mcp'
          % (args.host, args.port))

    def _shutdown(*_args):
        """Ctrl+C takes the service down first, then the session."""
        uv.should_exit = True
        window.close()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
