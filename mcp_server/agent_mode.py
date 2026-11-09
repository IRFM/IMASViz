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
run's figures are saved as PNGs under a directory the caller names --
that is how the images the agent drew reach the user: one
``<figure key>.png`` per figure the run left open (a key's ``:``
spelled ``_``), and ``transcript.txt`` for the transcript the user reads
on screen in the panel. The run is one turn on a fresh app: every figure
it holds, it drew. A session that keeps more turns (a page, a REPL)
passes each turn's own figures to `saveShots`, because a figure an
earlier turn drew is captured in that turn's files, not repeated into
the one after. A capture of the interface is an ask anywhere -- the
application shell (``00_app.png``) and the data-tree panel of a case
(``case_…``) are the `EXTRA_SHOTS` a caller names -- with
`--extra-shots` here, or the turn's own ask there -- and neither is
saved by default.

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


def _settleWindow(window, app):
    """Take the run's window off the screen and settle the event queue.

    A figure left *shown* as the process leaves is the one a queued paint
    event can strike while the interpreter tears the widget down -- the
    documented `Fatal … Segmentation fault inside pyqtgraph's
    GraphicsView.paintEvent`, and a picture window in particular is retained
    to the end of a run, so it is the one still on the paint queue at exit.
    `hide()` is immediate and reaches the children, and it does not raise the
    `QVizGlobalOperations.YesNo` confirmation the main window's `closeEvent`
    would pop in offscreen mode; draining the queue after it means there is no
    paint event left to land on a widget as the process dies.
    """
    hide = getattr(window, 'hide', None)
    if callable(hide):
        hide()
    process = getattr(app, 'processEvents', None)
    if callable(process):
        process()


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


#: The two captures that show the interface, not a figure of their own,
#: named so that a page, a command line and a test can ask for one by
#: name. A capture of a turn is the figures it drew or asked to be
#: captured, and these are the two that show the application instead:
#: the whole application, or the data-tree panel of a case. Neither is
#: saved by default: a capture of the interface is an ask, not a
#: by-product of the turn.
EXTRA_SHOTS = ('app', 'case-views')


def requestedCaptures(requested_windows):
    """The windows a turn asked to be captured, split for `saveShots`:
    the ones that name the interface are its `extras`, the ones that
    name a figure are its `figures`.

    `app` is the application extra; a case URI (`imas:…`, the name the
    core takes for a shot view) is the `case-views` extra; the rest are
    figure keys -- the figure the turn asked to be captured, whether it
    drew it this turn or drew it in one before. A named ask for a figure
    is the one that recaptures it, because a capture is only what a turn
    asks for, and it cannot know the window is closed unless it names
    it: `saveShots` refuses such a key by name, so the ask is not
    answered with a silence.
    """
    extras, figures = [], []
    for window in requested_windows or ():
        if window == 'app':
            if 'app' not in extras:
                extras.append('app')
        elif isinstance(window, str) and window.startswith('imas:'):
            if 'case-views' not in extras:
                extras.append('case-views')
        elif window not in figures:
            figures.append(window)
    return extras, figures


def saveShots(core, shots_dir, extras=(), figures=None):
    """The session's figure windows, and the extras that were asked for.

    The figures a caller names are the ones saved, when it names them:
    a web or a REPL passes the figures of the one turn it is ending
    (the ones it drew, the ones it asked to be captured), and a figure
    an earlier turn drew stays in the files that turn left instead of
    being repeated into every turn after it. A one-shot does not name
    them: its app is fresh, so the figures it left open are the ones it
    drew, and `figures=None` saves every window the session still holds
    a key for.

    The interface is an ask either way: the application shell (saved as
    `00_app.png`) and the data-tree panel of a case are the `extras`,
    drawn from `EXTRA_SHOTS`, and a name it does not hold is refused by
    naming the ones it does, because a caller that spells one wrongly
    meant to have saved it. The same refusal stands for a figure key a
    caller named that the session no longer holds a window for: the
    capture was asked, it is not made, and the caller reads why.

    Returns the list of files written, each as a `(window, path)` pair:
    the window is the name the core was asked with ("app", the figure
    key, the case URI) -- what `focus_window` and `get_screenshot` take
    back -- so a page that draws the picture can act on the window it
    shows. A window that refuses to render is named in the list that
    follows, and the other windows still come to disk.
    """
    extras = tuple(extras)
    unknown = [one for one in extras if one not in EXTRA_SHOTS]
    if unknown:
        raise ValueError(
            '%s is not a capture this run saves: the ones it holds '
            'beyond the figures are %s.'
            % (unknown, ', '.join(EXTRA_SHOTS)))
    if figures is not None:
        figures = set(figures)
    os.makedirs(shots_dir, exist_ok=True)
    saved = []
    refused = []
    targets = []
    if 'app' in extras:
        targets.append(('app', '00_app'))
    heldFigureKeys = set()
    for record in core.list_windows():
        if record['key'] is not None:
            heldFigureKeys.add(record['key'])
            if figures is None or record['key'] in figures:
                targets.append((record['key'],
                                record['key'].replace(':', '_')
                                .replace('/', '_')))
    if figures is not None:
        for key in sorted(figures - heldFigureKeys):
            refused.append(
                '%s: the session holds no figure window by that key: it '
                'is not captured' % key)
    if 'case-views' in extras:
        for record in core.list_windows():
            if record['key'] is not None:
                continue
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
    for window, name in targets:
        try:
            png = core.screenshot(window)
        except Exception as e:
            refused.append('%s: %s' % (window, e))
            continue
        path = os.path.join(shots_dir, name + '.png')
        with open(path, 'wb') as f:
            f.write(png)
        saved.append((window, path))
    return saved, refused


def extrasFromFlag(value):
    """The value of `--extra-shots` as the list `saveShots` takes.

    Names are comma-separated, kept in the order the caller spelled
    them, and a name `EXTRA_SHOTS` does not hold is refused by naming
    the ones it does -- the same words a misspelling gets from
    `saveShots` itself, one place early: a flag that dies at parse time
    is the one the user reads before any window is built.
    """
    extras = tuple(one.strip() for one in (value or '').split(',')
                   if one.strip())
    unknown = [one for one in extras if one not in EXTRA_SHOTS]
    if unknown:
        raise ValueError(
            '%s is not a capture this run saves: the ones it holds '
            'beyond the figures are %s.'
            % (unknown, ', '.join(EXTRA_SHOTS)))
    return extras


def runAgentMode(args, app=None, window=None, core=None, llm=None):
    """Run the agent once with the prompt after `--agent`, and save what it
    drew. Returns the exit code of the run."""
    prompt = (args.agent or '').strip()
    if not prompt:
        raise ValueError(
            'no prompt after --agent: %r. Name it, or drop the flag and '
            'serve the MCP service the usual way.' % args.agent)
    # Asked before any window is built: a name the run does not save dies
    # here, in the words `saveShots` would otherwise answer only at the
    # very end of the run.
    extras = extrasFromFlag(getattr(args, 'extra_shots', ''))
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

    saved, refused = saveShots(core, args.shots, extras=extras)
    transcript = os.path.join(args.shots, 'transcript.txt')
    with open(transcript, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('Saved images:',
          ', '.join(os.path.basename(path) for _, path in saved) or 'none',
          flush=True)
    for reason in refused:
        print('REFUSAL — screenshot: %s' % reason, flush=True)

    if outcome[0] is not None:
        print('Agent refusal: %s' % outcome[0], flush=True)
    if not saved:
        # Not a refusal: the loop answered, and it drew no figure -- the
        # capture of a run is its plots, and a run that worked on words
        # has none at its end. The interface captures are the ones a
        # caller names with --extra-shots, and a caller who meant to have
        # them is the one who was refused, by name, in the line above.
        print('No figure was open at the end of the run: nothing besides '
              'the transcript was saved.', flush=True)

    # The saved or the refused are the run's pictures, not its verdict:
    # the verdict is whether the loop answered, and a refusal with no
    # figure beside it is still the refusal the user reads.
    code = 0 if outcome[0] is None else 1
    _settleWindow(window, app)
    return code
