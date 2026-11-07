# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""One REPL for the in-app agent, without the window — or one prompt and its images.

    python3 -m viz_cli                          # the REPL, offscreen
    python3 -m viz_cli "trace le champ"         # one-shot: exit 0 if it
                                                # answered, 1 if it refused

The REPL holds one session open for its whole life -- the offscreen
application, its core, its one `AgentLoop` -- so a prompt can point at
what the one before it named. The stack it stands on is the one the GUI's
*Agent* entry and the one-shot build: `McpGuiCore` on the session's api,
one `GuiDispatcher`, one `AgentLoop`, the parameters -- `max_turns`,
`temperature`, `max_tokens` -- steered on the `Client` of `session`
with `/llm`.

The arrows, the completion and the history are the client's own
(`viz_cli.tui` and `viz_cli.history`): this node's Python does not have
the C module behind the standard library's `readline` (measured: the
module is there, `_rl` is not, and with it the arrows, the history file
and the completion), so what the client asks of the keyboard is a small
line editor over `termios` and `select`, and the history is the one
file `$HOME/.imasviz/cli_history` it keeps in, between runs, as the
preferences are kept.

The one-shot path is the one `mcp_server --agent` already owns: `main`
maps its prompt onto the argument that entry reads and delegates, and
its exit code and its images stay exactly where `test_112` pins them.
"""

import argparse
import os
import sys


def parseArguments(argv=None):
    """The command line of one client run."""
    parser = argparse.ArgumentParser(
        prog='viz_cli',
        description='IMASViz without the window: the in-app agent on '
                    'your prompts, its images and its transcript on disk.')
    parser.add_argument('prompt', nargs='*', default=None,
                        help='one-shot: the prompt to run, then exit — '
                             '0 if it answered, 1 if it was refused '
                             '(the same one-shot as `mcp_server --agent`)')
    parser.add_argument('--llm-url', dest='llm_url', default=None,
                        help='base URL of the local model, ending in /v1 '
                             '(default: the preferences\' '
                             'AgentLLMEndpoint, http://127.0.0.1:11434/v1)')
    parser.add_argument('--llm-model', dest='llm_model', default=None,
                        help='model name to send (default: the '
                             'preferences\' AgentLLMModel when no '
                             '--llm-url is named, the endpoint\'s first '
                             '/v1/models entry when one is)')
    parser.add_argument('--llm-key', dest='llm_key', default=None,
                        help='API key for the endpoint (sent only when '
                             'non-empty)')
    parser.add_argument('--max-turns', dest='max_turns', type=int,
                        default=12,
                        help='the agent loop\'s turn limit (default: 12)')
    parser.add_argument('--shots', default=None,
                        help='directory the turns\' images and transcripts '
                             'are saved in (default: '
                             '~/.imasviz/cli/shots)')
    parser.add_argument('--history', default=None,
                        help='readline history file (default: '
                             '~/.imasviz/cli_history)')
    parser.add_argument('--display', action='store_true',
                        help='keep the display when you have one (default: '
                             'offscreen — the point of the client)')
    return parser.parse_args(argv)


def _candidates():
    """Tab completion: the commands, the fields they steer, the gestures.

    One list, sorted, with a space after the word, so a completed tab
    leaves a word the line can still take an argument on."""
    from viz_cli.commands import COMMANDS, LLM_FIELDS
    candidates = ['/' + c + ' ' for c in COMMANDS]
    candidates += ['/llm ' + f + ' ' for f in LLM_FIELDS]
    candidates += ['/session save ', '/session restore ']
    try:
        from imasviz.VizAgent.tools import TOOLS
        candidates += ['/mcp ' + t['function']['name'] + ' ' for t in TOOLS]
    except Exception:
        pass
    return sorted(set(candidates))


def banner(llm, max_turns, shots_dir):
    """The line the REPL says when it opens, and the one /help expands."""
    return ('IMASViz client — the agent, %s. Endpoint %s, model %s, '
            '%d turns. A line runs it: its images and its transcript are '
            'saved under %s. Commands: /help.'
            % ('on the display' if os.environ.get('DISPLAY') else 'offscreen',
               llm.endpoint,
               llm.model or 'the endpoint\'s first /v1/models entry on '
                            'first use',
               max_turns, shots_dir))


def _realSession(args):
    """The session a real run holds: built in the order of
    `QtVIZ_GUI.main()`, offscreen unless the run was asked for its
    display, and refused by name when the environment refuses it."""
    from PySide6.QtWidgets import QApplication

    if not args.display:
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    app = QApplication.instance() or QApplication(['viz_cli'])

    from imasviz.VizAgent.core import McpGuiCore
    from imasviz.VizAgent.llm_client import LLMClient
    from imasviz.VizUtils import QVizGlobalOperations, QVizPreferences

    try:
        QVizGlobalOperations.checkEnvSettings()
    except SystemExit:
        raise ValueError(
            'the environment refused the session before any window: the '
            'line above names the variable it lacks. On this node the '
            'profile exports AL_VERSION, not IMAS_VERSION, and the '
            'application runs from the modules: `module load '
            'IMAS-Python/2.3.0-…` before `python3 -m viz_cli`, or start '
            'without VIZ_PRODUCTION=1.')
    QVizPreferences().build()
    from imasviz.VizGUI.VizGuiCustomization import QVizStyle
    QVizStyle.applyToApplication(app)
    from imasviz.VizGUI.QtVIZ_GUI import QVizMainWindow
    window = QVizMainWindow()
    window.show()

    client = LLMClient(
        endpoint=args.llm_url or None,
        model=args.llm_model or None,
        api_key=args.llm_key or None,
    )
    if args.llm_url and args.llm_model in (None, ''):
        # An endpoint named without a model: the first entry of that
        # endpoint's /v1/models is the one sent, the rule agent_mode holds.
        client.model = None
    from viz_cli.session import Client, CliSession
    wrapped = Client(client, max_tokens=2048)
    core = McpGuiCore(main_window=window,
                      api=_sessionApiOf(window))
    session = CliSession(app=app, window=window, core=core, llm=wrapped,
                         shots_dir=args.shots
                         or os.path.expanduser('~/.imasviz/cli/shots'),
                         max_turns=args.max_turns)
    return app, window, session


def _sessionApiOf(window):
    from mcp_server.agent_mode import _apiOf
    return _apiOf(window)


def interactive(args, session=None, inputs=None, settle=True):
    """The REPL loop. `session` is injected by the tests (a stand-in core
    and a scripted model); left out it is built for this run. `inputs`
    scripts the lines, one by one; left out the arrows own the keyboard.
    Returns 0 on a clean leave."""
    from viz_cli.commands import execute, parse
    from viz_cli.history import History
    from viz_cli import tui

    if session is None:
        app, window, session = _realSession(args)
        built = True
    else:
        app = session.app
        window = session.window
        built = False

    history = History(args.history
                      or os.path.expanduser('~/.imasviz/cli_history'))
    candidates = _candidates()
    print(banner(session.llm, session.max_turns, session.shots_dir))
    print('')

    lines = iter(inputs) if inputs is not None else None

    def readLine():
        if lines is not None:
            try:
                return next(lines)
            except StopIteration:
                return None
        return tui.readLine('IMASViz> ', history=history,
                            candidates=candidates)

    while True:
        try:
            line = readLine()
        except KeyboardInterrupt:
            print('')
            continue
        if line is None:
            print("Leaving: the arrows keep this run's prompts in %s"
                  % history.path)
            break
        line = (line or '').strip()
        if not line:
            continue
        try:
            if line.startswith('/'):
                if not execute(parse(line), session):
                    print('Leaving.')
                    break
            else:
                session.runPrompt(line)
        except Exception as e:
            # A refused command, a refused turn, any refusal the stack
            # gives: named out loud, and the REPL is still standing.
            print('REFUSAL — %s' % e, file=sys.stderr)

    if built and settle:
        from mcp_server.agent_mode import _settleWindow
        _settleWindow(window, app)
    return 0


def main(argv=None):
    """The entry: one prompt and its images, or the REPl until it is left."""
    args = parseArguments(argv)
    if args.prompt:
        prompt = ' '.join(args.prompt).strip()
        if not prompt:
            print('REFUSAL — no prompt after the flag: name it, or drop '
                  'the flag and the REPL is what answers.', file=sys.stderr)
            return 1
        args.agent = prompt
        if args.shots is None:
            args.shots = os.path.expanduser('~/.imasviz/cli/shots')
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from mcp_server.agent_mode import runAgentMode
        try:
            return runAgentMode(args)
        except ValueError as e:
            print('REFUSAL — %s' % e, file=sys.stderr)
            return 1
    return interactive(args)
