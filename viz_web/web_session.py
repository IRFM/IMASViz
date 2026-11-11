# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""One web session: the stack it drives, and one prompt's turn.

The stack is the one the REPL and the *Agent* entry of the *File* menu build:
`McpGuiCore` on the session's api, one `GuiDispatcher`, one `AgentLoop`.
What this module adds over `viz_cli.session.CliSession` is the shape an HTTP
endpoint needs: the turn's transcript is handed out **as it is written**
(`onLine`, called from a worker thread into a `queue.Queue` the page drains),
the gesture of the core is asked the way the loop itself asks it
(`callGesture` runs the same `AgentLoop._dispatch`, so the refusal a tool
earns is named the same way on this path and the one the agent takes), and a
turn at a time is enforced by a lock -- two prompts or a prompt and a gesture
run at once would interleave gestures on the one shared tree.

`runTurn` and `callGesture` are asked from a thread that is **not** the one
the `GuiDispatcher` was built on: the loop and the gestures are queued onto
that thread through the dispatcher, and whatever thread the caller is, it
waits. The caller never pumps: the one that owns the widgets owns the loop
(`app.exec_()` in the run, a `processEvents()` cycle in the test), and a
thread that does not own a widget may not touch one -- the rule the
dispatcher exists for.
"""

import base64
import json
import os
import re
import threading
import time

from PySide6.QtCore import Qt

from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.dispatcher import GuiDispatcher


class WebSession:
    """What the server holds open: its stack, its parameters, its turns.

    `app` is the `QApplication` of the run -- the one that owns the event
    loop every gesture is queued onto -- `window` the `QVizMainWindow` the
    core serves, `core` the `McpGuiCore` of this same session (the
    gestures), `client` the `Client` (the LLM and its running parameters,
    the one the REPL reads), `shots_dir` the directory every turn leaves
    its images and its transcript in, and `max_turns` the loop's turn limit.

    The `GuiDispatcher` is built here and only here, because its
    thread affinity is whichever thread builds it: the caller of
    `runTurn` and `callGesture` must be a different thread than that one,
    which a worker of the loop or the page is.
    """

    # The subset of a turn's record that reaches the disk: the fields
    # the page renders and the routes serve. Never the base64 the live
    # stream hands over (big) and never the transcript twice
    # (`transcript.txt` already holds it) -- and the one a turn that
    # comes back on a restart reads is the same subset, so the page
    # sees its captures and addresses the way it did on the run that
    # drew them.
    PERSISTED_KEYS = ('n', 'prompt', 'error', 'refusals',
                      'image_files', 'image_windows', 'reports', 'dir')

    @staticmethod
    def recordsFromDisk(shots_dir):
        """The records the captures directory holds, oldest first.

        A directory that holds no `turn.json` is one the run that wrote
        it predates the record (or one a test made by hand): its `n`
        comes from the number the directory name leads with, and its
        pictures the PNGs it holds -- an address the shot route can
        serve and the gallery re-builds from. The name of the picture
        carries the window it shows, because that is how a PNG without
        a record can still be acted on (`Plot1.png` -> `Plot1`).
        """
        records = []
        if not os.path.isdir(shots_dir):
            return records
        for entry in sorted(os.listdir(shots_dir)):
            match = re.match(r'^(\d+)_', entry)
            if not match:
                continue
            directory = os.path.join(shots_dir, entry)
            if not os.path.isdir(directory):
                continue
            number = int(match.group(1))
            record = None
            path = os.path.join(directory, 'turn.json')
            if os.path.isfile(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        record = json.load(f)
                except (OSError, ValueError):
                    record = None
            if record is None:
                images = sorted(name for name in os.listdir(directory)
                                if name.endswith('.png'))
                record = {'n': number, 'prompt': '', 'error': None,
                          'refusals': [], 'image_files': images,
                          'image_windows': [{'name': name,
                                             'window': name[:-4]}
                                            for name in images],
                          'reports': [], 'dir': directory}
            record['dir'] = os.path.abspath(directory)
            records.append(record)
        records.sort(key=lambda record: record['n'])
        return records

    def __init__(self, app, window, core, client, shots_dir, max_turns=12):
        from mcp_server.agent_mode import _apiOf

        self.app = app
        self.window = window
        self.core = core
        self.client = client
        self.llm = client  # the field the REPL's /llm asks of, shared
        self.max_turns = max_turns
        self.shots_dir = os.path.abspath(os.path.expanduser(shots_dir))
        self.dispatcher = GuiDispatcher()
        self.agent = AgentLoop(core, client, self.dispatcher,
                               main_window=window, api=_apiOf(window))
        self.prompts = []
        # The turns the captured directory holds, oldest first: a
        # restart of the process keeps the captures and the list that
        # names them. The one this process draws continues the numbering
        # where the ones on disk stop.
        self.turns = self.recordsFromDisk(self.shots_dir)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ turns

    @staticmethod
    def reportsFolder():
        """The reports folder, resolved the way the core's own
        `_namedReport` resolves it: under $HOME -- one answer for the
        two callers (the turn record and the service route), so a test
        that points HOME at its own tree points both there."""
        return os.path.realpath(os.path.expanduser(
            os.path.join('~', '.imasviz', 'reports')))

    @classmethod
    def reportsOnDisk(cls):
        """The names the reports folder holds -- the empty set while it
        does not exist yet, the state before the core's first write."""
        folder = cls.reportsFolder()
        try:
            return set(os.listdir(folder))
        except OSError:
            return set()

    def runTurn(self, prompt, onLine=None):
        """One prompt, and its whole turn.

        `onLine`, when named, is called with every line the loop writes, in
        the order it does, on the thread the loop runs -- the page feeds a
        queue from it and drains that queue as the turn goes. Left out, no
        one but the record listens, and the turn is simply a call and its
        answer.

        Returns the turn's record: the prompt, its lines, its captures as
        PNGs -- the figures the turn drew or asked to be captured, with
        the base64 the page needs to draw them and the window each one
        shows (a figure an earlier turn drew is not among them: it is
        captured in that turn's files) -- the reports its gestures wrote
        (the names the reports folder did not hold before the turn and
        holds after it), the refusal named, and the directory the images
        and the transcript are left in. An empty prompt is a named
        refusal, as the REPL refuses it.
        """
        with self._lock:
            prompt = (prompt or '').strip()
            if not prompt:
                raise ValueError(
                    'no prompt: name what to ask, or a gesture on the '
                    'tools panel.')
            self.prompts.append(prompt)

            lines = []
            requested_windows = []
            done = threading.Event()
            outcome = [None]
            # What the reports folder holds before the loop runs: the
            # turn's own reports are the names it holds after that are
            # not here now (the gestures write them through the core).
            before_reports = self.reportsOnDisk()
            # What the session already holds as figures before this turn
            # draws: the turn's own figures are the ones it adds to that,
            # and the ones an earlier turn drew stay in the files that
            # turn left, not repeated into this one. Asked the same way
            # the end of the turn asks the core -- on the GUI thread.
            figure_keys_before = self.dispatcher.call(
                lambda: {record['key']
                         for record in self.core.list_windows()
                         if record['key'] is not None})

            def onLineSlot(line):
                lines.append(line)
                if onLine is not None:
                    onLine(line)

            def onGestureSlot(name, args):
                # A capture is an ask. `get_screenshot` is the one the
                # loop saves a PNG for. `focus_window` is the "show me
                # this" in the desktop app: it brings the window forward
                # so the user sees it. In the web there is **no screen** --
                # the only way a figure reaches the user is the PNG this
                # turn saves -- so a focus of a figure or of `app` is a
                # capture ask too, not a by-product: the same window is
                # asked for twice (focus, then the screenshot) but keeps
                # to one file, the way the two `get_screenshot` asks of it
                # deduplicate in `_finishTurn`. A focus is thus how the
                # web answers "show me figure N" when the agent, on the
                # strength of the gesture it named, did not also ask for
                # the picture: the figure is still one the turn asked for,
                # and it is kept.
                # The same rule stands for `plot_one` with `into_figure_key`
                # set: the agent drew onto a figure it already held, so the
                # delta `figure_keys_now - figure_keys_before` is empty
                # (the key was in both), and without this the page would
                # render nothing for a turn the loop says drew -- the "je
                # ne vois plus les autres figures" case. The redraw names
                # its target, and it is the capture ask.
                if name in ('get_screenshot', 'focus_window'):
                    requested_windows.append(
                        (args or {}).get('window', 'app'))
                elif name == 'plot_one':
                    key = (args or {}).get('into_figure_key')
                    if key and key not in requested_windows:
                        requested_windows.append(key)

            def onDone(error):
                outcome[0] = error
                done.set()

            # `Qt.DirectConnection`, deliberately. These two callbacks touch no
            # widget -- they append to a local list and set a `threading.Event`
            # -- so they need no event loop to be delivered. A default (auto)
            # connection is queued, and a queued emission is delivered on the
            # thread the connection was *made* on: here `runTurn` runs on a
            # caller that is never the one pumping (the page's worker in the
            # run, the test thread in the suite), so the `done` handoff is
            # posted to a loop nothing ever runs and the turn hangs with the
            # loop already finished. Direct is the synchronous handoff these
            # two primitives want; the widget work below already crosses to
            # the GUI thread through the `GuiDispatcher`.
            self.agent.transcriptLine.connect(onLineSlot, Qt.DirectConnection)
            self.agent.askFinished.connect(onDone, Qt.DirectConnection)
            self.agent.gestureIssued.connect(onGestureSlot,
                                             Qt.DirectConnection)
            try:
                thread = threading.Thread(target=self.agent.ask,
                                          args=(prompt, self.max_turns),
                                          daemon=True)
                thread.start()
                while not done.wait(0.1):
                    pass
                thread.join()
            finally:
                for signal, slot in ((self.agent.transcriptLine, onLineSlot),
                                     (self.agent.askFinished, onDone),
                                     (self.agent.gestureIssued,
                                      onGestureSlot)):
                    try:
                        signal.disconnect(slot)
                    except (TypeError, RuntimeError):
                        pass

            # The figures the turn owns are the ones it adds to the
            # session's own, asked before the loop drew (`figure_keys
            # _before`) and now: the end of the turn names the
            # difference, and a figure an earlier turn drew stays in the
            # files that turn left, not repeated into this one.
            turn_dir, saved, refused, images, windows = self.dispatcher.call(
                lambda: self._finishTurn(lines, requested_windows,
                                         figure_keys_before))

            record = {'n': len(self.turns) + 1,
                      'prompt': prompt,
                      'lines': lines,
                      'refusals': list(refused),
                      'error': outcome[0],
                      'images': images,
                      'image_files': [name for name in
                                      (entry['name'] for entry in windows)],
                      # The address of every picture: what the page's
                      # Focus and Screenshot buttons send to focus_window
                      # and get_screenshot.
                      'image_windows': windows,
                      'reports': sorted(self.reportsOnDisk() - before_reports),
                      'dir': turn_dir}
            self.turns.append(record)
            # The record stays on disk beside its PNGs, the subset
            # `recordsFromDisk` reads back: a server that restarts between
            # turns answers its earlier turns from the folder instead of
            # an empty list while its captures sit there.
            with open(os.path.join(record['dir'], 'turn.json'), 'w',
                      encoding='utf-8') as f:
                json.dump({k: record.get(k) for k in self.PERSISTED_KEYS}, f)
            return record

    def _finishTurn(self, lines, requested_windows=(),
                    figure_keys_before=None):
        """The part of a turn that runs on the GUI thread: the window off
        the screen, the images and the transcript on disk, the PNGs
        read back.

        The turn's own figures are the ones it drew -- what it holds now
        and did not hold before the loop ran (`figure_keys_before`) --
        besides the windows the turn asked to be captured
        (`requested_windows`, the `get_screenshot` of the loop, the user's
        asks), which are its own even when the figure is an old one: a
        capture is what a turn draws or asks for, and a figure an earlier
        turn drew stays in the files that turn left. `requestedCaptures`
        splits the asks for `saveShots`, which is where the interface
        stands (`app` and the case URIs are its `extras`), and refuses a
        figure key the session does not hold by naming it.

        Asked through the `GuiDispatcher`, because it asks the core to
        render (`screenshot` -> `QWidget.grab()`), and a thread that does
        not own a widget must not ask one to draw. Returns the directory,
        the list of the PNGs written (window and path), the ones the core
        refused, every PNG as `{'name', 'window', 'b64'}` for the page,
        and the `({'name', 'window'})` pairs the record keeps for the
        page's buttons.
        """
        from mcp_server.agent_mode import (requestedCaptures, saveShots)

        number = len(self.turns) + 1
        turn_dir = os.path.join(
            self.shots_dir,
            '%02d_%s' % (number, time.strftime('%Y%m%d-%H%M%S')))
        if self.app is not None:
            # Settle the event queue, without hiding the application.
            # This session stays open for the next turn, and its
            # `show_window` / `focus_window` have to be able to bring a
            # figure back forward: a sub-window whose top-level was
            # hidden is not a sub-window that can be shown again -- it
            # answers `visible: false` to every `show()` (measured:
            # after one turn every figure of the session answered
            # `visible: false`, and `show_window` / `focus_window`
            # repeated the same answer to every retry). The hide at
            # the end is the one for a process that is leaving -- the
            # one-shot agent mode and the exit paths of the server and
            # the REPL (`_settleWindow`) -- not the one a turn of a
            # session that stays open earns.
            drain = getattr(self.app, 'processEvents', None)
            if callable(drain):
                drain()
        extras, askedFigures = requestedCaptures(requested_windows)
        figureKeysNow = {record['key']
                         for record in self.core.list_windows()
                         if record['key'] is not None}
        figures = (figureKeysNow - (figure_keys_before or set())) \
            | set(askedFigures)
        saved, refused = saveShots(
            self.core, turn_dir, extras=extras, figures=figures)
        with open(os.path.join(turn_dir, 'transcript.txt'), 'w') as f:
            f.write('\n'.join(lines) + '\n')
        # `saveShots` answers the (window, path) pairs it wrote: the name
        # the page shows is the file's own, and `window` is the address
        # the same page acts on it with -- focus_window and get_screenshot
        # take that name back.
        images = []
        windows = []
        for window, path in saved:
            with open(path, 'rb') as f:
                images.append({'name': os.path.basename(path),
                               'window': window,
                               'b64': base64.b64encode(f.read()).decode('ascii')})
            windows.append({'name': os.path.basename(path),
                            'window': window})
        return turn_dir, saved, list(refused), images, windows

    def stop(self):
        """Ask the loop to stop at the next turn boundary.

        The gesture that was started still finishes, and its images still
        come to disk -- the same rule the REPL applies to `Ctrl+C`.
        """
        self.agent.stop()

    # --------------------------------------------------------------- gestures

    def callGesture(self, name, args):
        """One gesture of the core, by its tool name, and value or refusal.

        The same `AgentLoop._dispatch` the loop uses: a name the core does
        not answer, and an argument the tool does not take, are both named
        where the page reads them, as they are named in the agent's
        transcript. A refusal is not an exception that dies here, it is a
        value the page prints -- which is what `test_116`/`test_117` pin
        on the loop, and what this path inherits because it runs the same
        method.
        """
        with self._lock:
            try:
                return {'error': None,
                        'result': self.dispatcher.call(
                            lambda: self.agent._dispatch(name, args or {}))}
            except Exception as e:
                return {'error': str(e), 'result': None}

    def llmFields(self):
        """What /llm reports, as the one command answers it: the endpoint,
        the model, whether the key is set, and the three running
        parameters the loop sends."""
        from imasviz.VizAgent.llm_client import LLMClient
        return {
            'endpoint': self.client.endpoint,
            'model': self.client.model
            or 'the endpoint\'s first /v1/models entry, read on first use',
            'key': bool(self.client.key),
            'max_turns': self.max_turns,
            'temperature': self.client.temperature,
            'max_tokens': self.client.max_tokens,
        }
