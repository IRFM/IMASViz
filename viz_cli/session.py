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
"""

import os
import threading
import time

from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.dispatcher import GuiDispatcher


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
    def __init__(self, app, window, core, llm, shots_dir, max_turns=8):
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

        lines = []
        done = threading.Event()
        outcome = [None]

        def onLine(line):
            print(line, flush=True)
            lines.append(line)

        def onDone(error):
            outcome[0] = error
            done.set()

        self.agent.transcriptLine.connect(onLine)
        self.agent.askFinished.connect(onDone)
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
            for signal, slot in ((self.agent.transcriptLine, onLine),
                                 (self.agent.askFinished, onDone)):
                try:
                    signal.disconnect(slot)
                except (TypeError, RuntimeError):
                    pass
        thread.join()

        self.turns.append(time.strftime('%H%M%S'))
        number = len(self.turns)
        sub = '%02d_%s' % (number, time.strftime('%Y%m%d-%H%M%S'))
        directory = os.path.join(self.shots_dir, sub)

        from mcp_server.agent_mode import saveShots
        saved, refused = saveShots(self.core, directory)
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
