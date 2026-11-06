# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Run the in-app agent once, offscreen, and leave its images behind.

The application is built (offscreen: a node without a display is what this
is for), the agent asked its one prompt, and when the loop stops the
session's windows are saved as PNGs under a directory the caller names --
that is how the images the agent drew reach the user: ``00_app.png`` for
the application, one ``<figure key>.png`` per window the session still
holds (a key's ``:`` spelled ``_``), and ``transcript.txt`` for the
transcript the user reads on screen in the panel.

The stack the loop runs on is the one the *Agent* entry of the *File* menu
builds (`QVizFileMenu.openAgent`): `McpGuiCore` on the session's api, one
`GuiDispatcher` built on this thread, one `AgentLoop`. `LLMClient` takes
the endpoint, the model and the key from the command line when they are
named there, and from `QVizPreferences` otherwise; when an endpoint is
named without a model the first entry of its ``/v1/models`` is the model
(the read `LLMClient` already answers, for a llama-server that is where
its one model lives).

One run, one exit code: 0 when the loop answered, 1 when it refused
(named, out loud, in the transcript and on the line that follows),
whether the refusal is of the LLM, of a gesture, or of a snapshot.
"""

import os
import re
import threading

from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.core import McpGuiCore
from imasviz.VizAgent.dispatcher import GuiDispatcher
from imasviz.VizAgent.llm_client import LLMClient


def _apiOf(window):
    """The session's api, asked the way `QVizFileMenu.openAgent` asks it."""
    apiOf = getattr(window, 'sessionApi', None)
    return apiOf() if callable(apiOf) else None


def buildLLM(args):
    """The `LLMClient` of this run, from the command line.

    An explicit `--llm-model` is the model that is sent. When no model is
    named -- or an empty one is -- and an endpoint is named, the first
    entry of the endpoint's ``/v1/models`` is taken instead, because a name
    sent that the server does not hold is a connection cost and a refusal.
    Without an endpoint, the preferences stand, as in the in-app agent.
    """
    client = LLMClient(
        endpoint=args.llm_url or None,
        model=args.llm_model or None,
        api_key=args.llm_key or None,
    )
    if args.llm_model == '' or (args.llm_model is None and args.llm_url):
        # An explicit empty model, or an endpoint named without a model,
        # is "the server's first entry" -- a name the server does not hold
        # is a refusal that costs a round-trip to find out.
        client.model = None
    return client


def buildAgentStack(window, llm, core=None):
    """`McpGuiCore`, `GuiDispatcher`, `AgentLoop` -- the three of the panel.

    Built on the thread that owns the widgets of this run: the dispatcher's
    signal hand-off only means something where the events that drain it are
    pumped, and the worker that runs the loop is not that one.
    """
    api = _apiOf(window)
    if core is None:
        core = McpGuiCore(main_window=window, api=api)
    dispatcher = GuiDispatcher()
    agent = AgentLoop(core, llm, dispatcher,
                      main_window=window, api=api)
    return core, agent


def saveShots(core, shots_dir):
    """The app, and every window the session still holds, as PNGs on disk.

    Returns the list of files written. A window that refuses to render is
    named in the line that follows -- the style of the repository -- and
    the other windows still come to disk.
    """
    os.makedirs(shots_dir, exist_ok=True)
    saved = []
    refused = []
    targets = [('app', '00_app')]
    for record in core.list_windows():
        key = record['key']
        if key is None:
            # A case view answers no figure key (see `QVizWindowRecord`):
            # the case URI is the name its shot view is asked with, and
            # `McpGuiCore.screenshot` takes it. The file name keeps the
            # tail of the path it names.
            cases = [c for c in record.get('cases') or [] if c]
            if not cases:
                refused.append('%s: no key and no case to name it'
                               % (record.get('kind') or record.get('label')
                                  or 'a window'))
                continue
            uri = cases[0]
            tail = uri.rsplit('path=', 1)[-1]
            tail = re.sub(r'[^A-Za-z0-9._-]', '_', tail).strip('_')
            targets.append((uri, 'case_%s' % (tail or str(len(targets)))))
        else:
            targets.append((key, key.replace(':', '_').replace('/', '_')))
    for window, name in targets:
        try:
            png = core.screenshot(window)
        except Exception as e:
            refused.append('%s: %s' % (window, e))
            continue
        path = os.path.join(shots_dir, name + '.png')
        with open(path, 'wb') as f:
            f.write(png)
        saved.append(path)
    return saved, refused


def runAgentMode(args, app=None, window=None, core=None, llm=None):
    """Run the agent once with the prompt after `--agent`, and save what it
    drew. Returns the exit code of the run."""
    prompt = (args.agent or '').strip()
    if not prompt:
        raise ValueError(
            'no prompt after --agent: %r. Name it, or drop the flag and '
            'serve the MCP service the usual way.' % args.agent)
    if app is None:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
    if window is None:
        from mcp_server.run import buildApplication
        app, window = buildApplication(
            args,
            banner='Welcome to Viz! The agent runs offscreen: its prompt '
                   'is "%s" and its images will be saved under %s.'
                   % (prompt, args.shots))
    if llm is None:
        llm = buildLLM(args)
    core, agent = buildAgentStack(window, llm, core=core)

    lines = []
    done = threading.Event()
    outcome = [None]

    def onLine(line):
        print(line, flush=True)
        lines.append(line)

    def onFinished(error):
        outcome[0] = error
        done.set()

    agent.transcriptLine.connect(onLine)
    agent.askFinished.connect(onFinished)

    print('Agent: prompt "%s" against %s (model %s)'
          % (prompt,
             getattr(llm, 'endpoint', 'the endpoint of this run'),
             getattr(llm, 'model', None) or 'the endpoint\'s first entry'),
          flush=True)

    thread = threading.Thread(
        target=agent.ask, args=(prompt, args.max_turns), daemon=True)
    thread.start()
    while not done.wait(0.1):
        app.processEvents()
    thread.join()

    saved, refused = saveShots(core, args.shots)
    transcript = os.path.join(args.shots, 'transcript.txt')
    with open(transcript, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('Saved images:', ', '.join(saved) or 'none', flush=True)
    for reason in refused:
        print('REFUSAL — screenshot: %s' % reason, flush=True)

    if outcome[0] is not None:
        print('Agent refusal: %s' % outcome[0], flush=True)
        return 1
    if not saved:
        print('REFUSAL — no image could be saved: %s'
              % ('; '.join(refused) or 'no window to ask'), flush=True)
        return 1
    return 0
