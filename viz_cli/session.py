# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""One viz_cli session: the stack it drives, and one prompt's turn.

The stack is the one the *Agent* entry of the *File* menu builds
(`QVizFileMenu.openAgent`): `McpGuiCore` on the session's api, one
`GuiDispatcher`, one `AgentLoop`. What this module adds is the REPL
discipline around it: one turn is one worker thread and the event pump
(the `mcp_server.agent_mode` pattern, which a thread that does not own
a widget may not touch one without), the turns keep the loop's history
(a prompt answers the one before it), and each turn leaves its images
and its transcript on disk under a numbered directory -- the `saveShots`
of the one-shot, asked after every prompt instead of once at the end.

`Ctrl+C` during a turn asks the loop to stop at the turn boundary
(`AgentLoop.stop`), and the turn that was started still leaves its
images and its transcript on disk.

And the same capture rule the page applies: a turn's captures are the
figures it drew, the figures its gestures moved (scale, shift,
normalize, reset, remove, the axes -- they ask for their `figure_key`
the way the redraw asks for its `into_figure_key`, so a turn that
multiplied a curve an earlier prompt drew keeps that figure for the
user), and the windows it asked to be captured -- a figure an earlier
prompt drew is captured in that prompt's directory, not repeated into
every prompt after it, and an ask for it (the loop's `get_screenshot`,
the way a prompt says "give me a capture of that figure") is the one
that recaptures it into the prompt that asked. A figure the ACCEPTED
final answer names by its key is an ask of the same kind: the promise
the agent makes -- show the figures it traces OR NAMES -- holds
mechanical this way, and not on the model's deciding to call
focus_window after it drew, moved or named one.
"""

import os
import threading
import time

from PySide6.QtCore import Qt

from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.dispatcher import GuiDispatcher
from imasviz.VizAgent.QVizPromptHistory import QVizPromptHistory


class Client:
    """One LLM endpoint and its running parameters, over the `LLMClient`.

    `AgentLoop` asks one chat method of it; `endpoint`, `model` and
    `key` are read off its `LLMClient`, and `temperature` and
    `max_tokens` are what every call is sent with. `apply()` rebuilds
    the `LLMClient` from the preferences after a `/llm` change, and the
    loop's own reference keeps standing.
    """
    def __init__(self, inner, temperature=0.2, max_tokens=2048):
        self.inner = inner
        self.temperature = temperature
        self.max_tokens = max_tokens

    @property
    def endpoint(self):
        return self.inner.endpoint

    @property
    def model(self):
        return self.inner.model

    @property
    def key(self):
        return self.inner.api_key

    def apply(self):
        """Re-read the endpoint, model and key from the preferences."""
        from imasviz.VizAgent.llm_client import LLMClient
        self.inner = LLMClient()

    def chat(self, messages, tools=None):
        return self.inner.chat(messages, tools=tools,
                               max_tokens=self.max_tokens,
                               temperature=self.temperature)


class CliSession:
    """What the REPL holds open: its stack, its parameters, its turns.

    `app` is the `QApplication` of the run -- the one that pumps events
    while a turn runs -- `window` the `QVizMainWindow` it serves, `core`
    the `McpGuiCore` of this same session, `llm` the `Client`,
    `shots_dir` the directory under which every turn leaves its images
    and its transcript.
    """
    def __init__(self, app, window, core, llm, shots_dir, max_turns=12):
        from mcp_server.agent_mode import _apiOf
        self.app = app
        self.window = window
        self.core = core
        self.llm = llm
        self.max_turns = max_turns
        self.shots_dir = os.path.abspath(os.path.expanduser(shots_dir))
        self.dispatcher = GuiDispatcher()
        self.agent = AgentLoop(core, self.llm, self.dispatcher,
                               main_window=window, api=_apiOf(window))
        # No mode is pinned here: `ask` reads the preference each turn (the
        # live view, `hide` by default), and the on-disk transcript is fed by
        # the `fullLine` -- the full render, which carries the tool traffic
        # whatever the live view hides. So the live view follows `hide`, and
        # the audited file still gets the calls it ran: the two were the same
        # shape before (forced `verbose`), and now the file stops being tied
        # to the view's quietness. `/tools` pins and persists the mode.
        self.prompts = []
        self.turns = []

    def runPrompt(self, text):
        """One turn: the loop, the transcript on the console, the images
        and the transcript on disk. Returns the turn's outcome, and
        raises a named `ValueError` on an empty prompt."""
        prompt = (text or '').strip()
        if not prompt:
            raise ValueError(
                'no prompt: name what to ask, or /help for the commands.')
        self.prompts.append(prompt)
        # The one list the whole application shares: a prompt this turn asks
        # is where the panel, the web, and the arrows of the next run recall
        # it, and `new session` cannot reach it.
        QVizPromptHistory.append(prompt)

        # The live view (the console) and the artifact (`transcript.txt`)
        # are two different shapes of the same turn: the console wears the
        # mode (`transcriptLine` -- quiet under `hide`), the file is the full
        # render the `fullLine` carries whatever the mode hides. Splitting
        # them is the whole point of `fullLine`: the reader who audits the
        # turn needs the `get_screenshot(…)` / `← focus_window: …` the mode
        # cut from the view, and the mode is not what decides what lands on
        # disk.
        lines = []
        requested_windows = []
        # The accepted final answer(s) of this turn: the one the loop
        # emits on the path that accepts them (`finalAnswer`), not on a
        # refusal or the max-turns stop. A figure it names by a key the
        # session holds is an ask the turn owes its capture -- the
        # "ou nomme" half of the promise, held mechanical here instead
        # of on the model's calling focus_window. Appending to a local
        # list touches no widget, so the direct hand-off is the one the
        # web keeps for the same reason: no loop to pump this onto.
        final_texts = []
        done = threading.Event()
        outcome = [None]

        def onLive(line):
            print(line, flush=True)

        def onFull(line):
            lines.append(line)

        def onGesture(name, args):
            # A capture is an ask. `get_screenshot` is the one the loop
            # saves a PNG for. `focus_window` is the "show me this" in
            # the desktop app: it brings the window forward so the user
            # sees it. In the REPL there is **no screen** to bring
            # forward -- the only way a figure reaches the user is the
            # PNG this prompt saves -- so a focus of a figure or of `app`
            # is a capture ask too, keeping to one file the way a focus
            # and the screenshot of the same window deduplicate below.
            # The same rule stands for `plot_one` with `into_figure_key`
            # set: the agent drew onto a figure it already held, so the
            # delta `figure_keys_now - figure_keys_before` is empty (the
            # key was in both), and without this the transcript would
            # "en parler" while the PNG never lands -- the same "je ne
            # vois plus les autres figures" case. The redraw names its
            # target, and it is the capture ask.
            # And the gestures that move a figure's content (scale,
            # shift, normalize, reset, remove, the axes) ask for the
            # figure they work on: the turn moved a figure an earlier one
            # drew, and the delta is empty the way the redraw's is --
            # "multiplie la courbe par 3" left a transcript and no
            # picture until this read the `figure_key` as the ask.
            # `captureAsk` holds the whole rule, one place, and the web
            # asks the one it shares.
            from mcp_server.agent_mode import captureAsk
            window = captureAsk(name, args)
            if window and window not in requested_windows:
                requested_windows.append(window)

        def onDone(error):
            outcome[0] = error
            done.set()

        def onFinal(text):
            final_texts.append(text)

        # What the session already holds as figures before this prompt
        # draws: the prompt's own figures are the ones it adds to that,
        # and the ones an earlier prompt drew stay in the directories
        # those prompts left, not repeated into this one.
        figure_keys_before = {record['key']
                              for record in self.core.list_windows()
                              if record['key'] is not None}
        self.agent.transcriptLine.connect(onLive)
        self.agent.fullLine.connect(onFull)
        self.agent.askFinished.connect(onDone)
        self.agent.gestureIssued.connect(onGesture)
        self.agent.finalAnswer.connect(onFinal, Qt.DirectConnection)
        thread = threading.Thread(target=self.agent.ask,
                                  args=(prompt, self.max_turns),
                                  daemon=True)
        interrupted = False
        try:
            thread.start()
            while not done.wait(0.1):
                self.app.processEvents()
        except KeyboardInterrupt:
            # The loop stops at the next turn boundary; what was drawn
            # before it is the turn, and it is saved below either way.
            interrupted = True
            self.agent.stop()
            deadline = time.time() + 5
            while not done.wait(0.1) and time.time() < deadline:
                self.app.processEvents()
        finally:
            for signal, slot in ((self.agent.transcriptLine, onLive),
                                 (self.agent.fullLine, onFull),
                                 (self.agent.askFinished, onDone),
                                 (self.agent.gestureIssued, onGesture),
                                 (self.agent.finalAnswer, onFinal)):
                try:
                    signal.disconnect(slot)
                except (TypeError, RuntimeError):
                    pass
        thread.join()

        self.turns.append(time.strftime('%H%M%S'))
        number = len(self.turns)
        sub = '%02d_%s' % (number, time.strftime('%Y%m%d-%H%M%S'))
        directory = os.path.join(self.shots_dir, sub)

        from mcp_server.agent_mode import requestedCaptures, saveShots
        from imasviz.VizAgent.agent import figuresNamedIn

        # The captures of this prompt only: the figures it drew (what it
        # holds now and did not hold before the loop ran), the figures
        # its gestures moved (`captureAsk` reads their `figure_key` as
        # the ask), and the windows it asked to be captured -- old or
        # new. A figure an earlier prompt drew is not among them, and
        # the one this prompt asked is, `saveShots` naming it by
        # refusal when the session no longer holds it.
        # The figures the ACCEPTED final answer names stand beside those
        # three: the promise the agent made ("show the figures it
        # traces or NAMES") is what the scan holds mechanical, and it
        # walks only the keys the session holds NOW -- a figure the turn
        # closed, or one the answer invented, is not named, because a
        # capture of it would be the refusal the core earns, and the
        # promise is about the figures the session shows, not the words
        # it does not hold. A refused turn has no final answer (the loop
        # emits it only where it accepts one), and so names nothing.
        extras, askedFigures = requestedCaptures(requested_windows)
        figure_keys_now = {record['key']
                           for record in self.core.list_windows()
                           if record['key'] is not None}
        namedFigures = figuresNamedIn('\n'.join(final_texts),
                                      sorted(figure_keys_now))
        figures = ((figure_keys_now - figure_keys_before)
                   | set(askedFigures)
                   | set(namedFigures))
        saved, refused = saveShots(
            self.core, directory, extras=extras, figures=figures)
        transcript = os.path.join(directory, 'transcript.txt')
        with open(transcript, 'w') as f:
            f.write('\n'.join(lines) + '\n')

        if interrupted:
            print('Interrupted: the turn was stopped at your request; '
                  'what it drew is saved below.', flush=True)
        for reason in refused:
            print('REFUSAL — screenshot: %s' % reason, flush=True)
        if outcome[0] is not None:
            print('REFUSAL — %s' % outcome[0], flush=True)
        print('Turn %d: %s' % (number, directory), flush=True)

        return {'refusal': outcome[0], 'saved': saved,
                'refused': refused, 'dir': directory}
