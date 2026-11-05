# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The tools end to end: a real MCP client over a real transport.

`test_100` drives `McpGuiCore` in process. This file closes the loop the
agent actually travels: the `FastMCP` instance of `buildServer` served by
uvicorn on a local socket, and the `streamablehttp_client` of the
official SDK answering the calls -- with the session of
`McpGuiCore` sitting on the reference case, so a refusal the agent reads
through the wire is the refusal the application would have named on its
own.

The threading is the whole shape of the design and is pinned here: the
SDK answers tool calls on the transport thread, and that thread blocks in
`GuiDispatcher.call` until the GUI thread runs the gesture. The GUI
thread is the test thread itself, so it pumps `app.processEvents()`
while the client thread waits -- the same hand-off the production
`python -m mcp_server` gets from `app.exec_()`.
"""

import asyncio
import socket
import threading
import time

import pytest

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)

IDS_NAME = 'equilibrium'
EQUILIBRIUM_OCCURRENCES = [0, 1, 2, 3]

EXPECTED_TOOLS = {
    'open_case', 'list_cases', 'close_case',
    'list_idss', 'load_ids', 'search_nodes', 'select_signals',
    'unselect_all',
    'plot_one', 'plot_selection', 'plot_table', 'plot_stacked',
    'get_signal',
    'list_windows', 'show_window', 'hide_window', 'close_window',
    'list_plugins', 'run_plugin',
    'save_session', 'restore_session',
    'export_to_ids',
    'get_screenshot', 'get_logs',
}

CALL_TIMEOUT = 90.0


def _freePort():
    """A port nobody else holds right now."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


@pytest.fixture(scope='module')
def mcpSession(qapp, tmp_path_factory):
    """The whole stack running: case, core, dispatcher, server, transport.

    The suite does not isolate ``$HOME``, so the configuration the
    session writes lands in the real ``~/.imasviz`` when ``HOME`` is left
    alone -- the same reason and the same guard as ``test_100``.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)

    from PySide6.QtWidgets import QApplication
    from mcp_server.core import McpGuiCore
    from mcp_server.dispatcher import GuiDispatcher
    from mcp_server.tools import buildServer
    import uvicorn

    app = QApplication.instance()
    home = tmp_path_factory.mktemp('mcpHttpHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))

    core = McpGuiCore()
    dispatcher = GuiDispatcher()
    server = buildServer(core, dispatcher, name='imasviz')
    port = _freePort()
    config = uvicorn.Config(server.streamable_http_app(),
                            host='127.0.0.1', port=port,
                            log_level='error')
    uv = uvicorn.Server(config)
    uv.install_signal_handlers = lambda: None

    def _serve():
        try:
            asyncio.run(uv.serve())
        except Exception:  # torn down at the end of the module
            pass

    thread = threading.Thread(target=_serve, name='mcp-test-transport',
                              daemon=True)
    thread.start()
    ready = time.time() + 8
    while not uv.started and time.time() < ready:
        time.sleep(0.05)
        app.processEvents()
    if not uv.started:
        raise RuntimeError('the test transport did not start on port %s'
                           % port)

    url = 'http://127.0.0.1:%d/mcp' % port

    def invoke(callables):
        """Run the client flow on its own loop, pumping the GUI thread at
        once.

        `callables` is a list of (name of the client step, coroutine
        function); each runs in order inside one client session, and the
        main thread drains the queue the dispatcher posts into, gesture
        after gesture.
        """
        box = {}

        def run():
            async def go():
                results = []
                from mcp import ClientSession
                from mcp.client.streamable_http import streamable_http_client
                async with streamable_http_client(url) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        init = await session.initialize()
                        results.append(init)
                        for step in callables:
                            results.append(await step(session))
                return results

            try:
                box['value'] = asyncio.run(go())
            except BaseException as exc:  # surface it at the caller
                box['error'] = exc

        worker = threading.Thread(target=run, name='mcp-test-client',
                                  daemon=True)
        worker.start()
        deadline = time.time() + CALL_TIMEOUT
        while worker.is_alive() and time.time() < deadline:
            app.processEvents()
            time.sleep(0.02)
        worker.join(10.0)
        if worker.is_alive():
            raise RuntimeError('the tool call outlived %ss -- the gesture '
                               'on the GUI thread never answered'
                               % int(CALL_TIMEOUT))
        if 'error' in box:
            raise box['error']
        return box['value']

    yield {'url': url, 'core': core, 'invoke': invoke,
           'home': str(home)}

    uv.should_exit = True
    thread.join(timeout=4.0)
    app.processEvents()
    patch.undo()


# ---------------------------------------------------------------- helpers

def _text(result):
    """The words the tool answered, in its first content block."""
    return result.content[0].text if result.content else ''


def _payload(result):
    """The data the tool answered, read off its JSON."""
    import json
    return json.loads(_text(result))


def _openCase(session):
    return session.call_tool('open_case', {
        'uri': CASE_URI, 'dd_version': CASE_DATA_DICTIONARY_VERSION})


def _listIdss(session, uri):
    return session.call_tool('list_idss', {'uri': uri})


def _listCases(session):
    return session.call_tool('list_cases', {})


def _getLogs(session):
    return session.call_tool('get_logs', {'uri': None, 'tail': 200})


def _screenshotApp(session):
    return session.call_tool('get_screenshot', {'window': 'app'})


# -------------------------------------------------------------------- run

def test_the_transport_lists_every_tool_and_says_the_method(mcpSession):
    """Every one of the 24 tools is there, and the instructions read back.

    `results[0]` is the `InitializeResult` of the session: the server's
    name and its instructions -- the working method the agent is handed
    before its first call.
    """
    init, listed = mcpSession['invoke']([
        lambda s: s.list_tools(),
    ])[:2]
    names = {tool.name for tool in listed.tools}
    assert EXPECTED_TOOLS <= names, names
    assert 'imasviz' in (init.serverInfo.name or '').lower(), init.serverInfo
    assert 'open_case' in (init.instructions or ''), (init.instructions or '')[:80]


def test_open_case_comes_back_over_the_wire(mcpSession):
    result = mcpSession['invoke']([_openCase])[1]
    data = _payload(result)
    assert data['already_open'] is False, data
    assert 'equilibrium' in data['ids'], 'the ids the case holds are not in the answer'


def test_list_idss_answers_the_case_itself(mcpSession):
    result = mcpSession['invoke']([lambda s: _listIdss(s, CASE_URI)])[1]
    data = _payload(result)
    entry = next(item for item in data['idss'] if item['name'] == IDS_NAME)
    assert entry['occurrences'] == EQUILIBRIUM_OCCURRENCES, entry


def test_get_logs_reads_the_panel(mcpSession):
    # The panel holds what the gestures of this module wrote -- the content
    # after a gesture is the domain of `test_100`, in process. Here the tool
    # is asked for the panel and answers its shape, with the case named.
    result = mcpSession['invoke']([_getLogs])[1]
    data = _payload(result)
    assert data['uri'] == CASE_URI, data
    assert isinstance(data['lines'], list), data


def test_a_refusal_is_named_over_the_wire(mcpSession):
    result = mcpSession['invoke']([
        lambda s: _listIdss(s, 'imas:hdf5?path=/no/such/case')])[1]
    assert result.isError is True, 'a refused case is an error the tool says so'
    assert 'is not open in this session' in _text(result), _text(result)


def test_the_screenshot_refusal_comes_back_an_error(mcpSession):
    result = mcpSession['invoke']([_screenshotApp])[1]
    assert result.isError is True, 'no window here: this is a named refusal'
    assert 'No application window' in _text(result), _text(result)
