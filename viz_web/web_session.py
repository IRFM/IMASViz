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
import os
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
        self.turns = []
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

        Returns the turn's record: the prompt, its lines, its images as
        PNGs (with the base64 the page needs to draw them), the reports
        its gestures wrote (the names the reports folder did not hold
        before the turn and holds after it), the refusal named, and the
        directory the images and the transcript are left in. An empty
        prompt is a named refusal, as the REPL refuses it.
        """
        with self._lock:
            prompt = (prompt or '').strip()
            if not prompt:
                raise ValueError(
                    'no prompt: name what to ask, or a gesture on the '
                    'tools panel.')
            self.prompts.append(prompt)

            lines = []
            done = threading.Event()
            outcome = [None]
            # What the reports folder holds before the loop runs: the
            # turn's own reports are the names it holds after that are
            # not here now (the gestures write them through the core).
            before_reports = self.reportsOnDisk()

            def onLineSlot(line):
                lines.append(line)
                if onLine is not None:
                    onLine(line)

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
                                     (self.agent.askFinished, onDone)):
                    try:
                        signal.disconnect(slot)
                    except (TypeError, RuntimeError):
                        pass

            turn_dir, saved, refused, images = \
                self.dispatcher.call(lambda: self._finishTurn(lines))

            record = {'n': len(self.turns) + 1,
                      'prompt': prompt,
                      'lines': lines,
                      'refusals': list(refused),
                      'error': outcome[0],
                      'images': images,
                      'image_files': [os.path.basename(path) for path in saved],
                      'reports': sorted(self.reportsOnDisk() - before_reports),
                      'dir': turn_dir}
            self.turns.append(record)
            return record

    def _finishTurn(self, lines):
        """The part of a turn that runs on the GUI thread: the window off
        the screen, the images and the transcript on disk, the PNGs
        read back.

        Asked through the `GuiDispatcher`, because it asks the core to
        render (`screenshot` -> `QWidget.grab()`), and a thread that does
        not own a widget must not ask one to draw. Returns the directory,
        the list of the PNGs written (name and path), the ones the core
        refused, and every PNG as `{'name', 'b64'}` for the page.
        """
        from mcp_server.agent_mode import _settleWindow, saveShots

        number = len(self.turns) + 1
        turn_dir = os.path.join(
            self.shots_dir,
            '%02d_%s' % (number, time.strftime('%Y%m%d-%H%M%S')))
        if self.app is not None and self.window is not None:
            _settleWindow(self.window, self.app)
        saved, refused = saveShots(self.core, turn_dir)
        with open(os.path.join(turn_dir, 'transcript.txt'), 'w') as f:
            f.write('\n'.join(lines) + '\n')
        # `saveShots` answers the paths it wrote, not (name, path) pairs:
        # the name the page shows is the file's own.
        images = []
        for path in saved:
            with open(path, 'rb') as f:
                images.append({'name': os.path.basename(path),
                               'b64': base64.b64encode(f.read()).decode('ascii')})
        return turn_dir, saved, list(refused), images

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
