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
    return parser.parse_args(argv)


def buildApplication(args):
    """The GUI, in the order of `QtVIZ_GUI.main()`.

    The preferences are read before the window (a theme is one of them,
    and a window built under the desktop's own palette paints its first
    frame in colours the user did not ask for); the window is shown so
    the service drives one the user can watch.
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
    """The entry point: the session and its service, together, until the
    window closes."""
    args = parseArguments(argv)
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
