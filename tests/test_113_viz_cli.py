# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The viz_cli REPL: the command answers, and the turn that keeps its context.

What it pins, in the order the client must answer them:

* `/llm` prints what is in force, and `endpoint`, `model` and `key` are
  set **and persisted** in the one preferences file the GUI reads (HOME
  pointed at a test directory, the `test_39` pattern), so the two
  interfaces stay on the same endpoint; an unknown field and a non-http
  endpoint are refused by name;
* `/mcp` answers the endpoint, names the models when they answer -- the
  named refusal when they do not -- and lists every tool of the agent,
  one by one on `/mcp <name>`, refusing a name it does not hold;
* a prompt runs the loop through the **real** dispatcher and event pump
  of `test_112`, and the turn that answers (or refuses) still leaves its
  images and its transcript on disk;
* the **context survives between two prompts** of one session -- the
  second call to the model carries the first exchange;
* `/history`, `/shots`, `/session` and the unknown-command refusal
  answer the way the client's own commands do;
* `main()` with a prompt delegates to the one-shot `runAgentMode`, and
  an empty prompt is refused before anything is built.

Nothing here touches the network: the LLM is scripted (`test_112`'s
stand-in, recording what it is asked), and the endpoint it reports
points at a port nothing listens on.
"""

import base64

from imasviz.VizAgent.llm_client import LLMClient, LLMResponse

from viz_cli.commands import execute, help_text, parse
from viz_cli.session import CliSession, Client

# A 1x1 transparent PNG: the file tests check the magic, not the pixels.
PNG_1x1 = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
    'AAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')

CASE_URI = ('imas:hdf5?path='
            '/afs/eufus.eu/g2itmdev/user/g2lfleur/public/imasdb/west/3/54924/0')

# A port nothing on this node listens on: the `/mcp` models probe reads
# its refusal by that name, and no round-trip costs the run.
DEAD_ENDPOINT = 'http://127.0.0.1:65531/v1'


class FakeLLMClient:
    """The scripted LLM of `test_112`, kept, recording what it is asked."""
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, messages, tools=None, **kwargs):
        self.calls.append(list(messages))
        if not self.responses:
            raise AssertionError('FakeLLMClient: no more scripted responses')
        return self.responses.pop(0)


class FakeCore:
    """A core that answers PNGs and records the session gestures."""
    def __init__(self):
        self.saved = []
        self.restored = []

    def list_windows(self):
        return [{'kind': 'SlicesPlot', 'label': 'SlicesPlot 1',
                 'key': 'SlicesPlot1', 'visible': True, 'cases': []}]

    def screenshot(self, window):
        if window not in ('app', 'SlicesPlot1'):
            raise ValueError('no such window: %r' % window)
        return PNG_1x1

    def list_cases(self):
        return [{'uri': CASE_URI, 'dd_version': '3.35.0',
                 'loaded': {'equilibrium': [0]}, 'signals': 33}]

    def list_case_idss(self, uri):
        assert uri == CASE_URI, uri
        return [{'name': 'equilibrium', 'occurrences': [0, 1, 2, 3]},
                {'name': 'magnetics', 'occurrences': [0]}]

    def save_session(self, name=None, path=None):
        self.saved.append(name)
        return {'saved_to': '/preferences/%s.vsess' % name}

    def restore_session(self, name=None, path=None):
        self.restored.append(name)
        return {'cases': [{'uri': CASE_URI, 'opened': True}],
                'windows': []}


class FakeWindow:
    """What the session asks of the window: the api, and a hide at exit."""
    def sessionApi(self):
        return None

    def hide(self):
        pass


def buildSession(qapp, tmp_path, llm=None, shots=None, max_turns=8):
    """One session on stand-ins: the real loop, dispatcher and pump, a
    scripted model, a core that answers PNGs, the images under a test
    directory."""
    llm = llm or Client(LLMClient(endpoint=DEAD_ENDPOINT, model='stub',
                                  timeout=2.0))
    core = FakeCore()
    session = CliSession(app=qapp, window=FakeWindow(), core=core, llm=llm,
                         shots_dir=str(shots or (tmp_path / 'shots' / 'default')),
                         max_turns=max_turns)
    return session, core


def toolCall():
    return LLMResponse(content='',
                       tool_calls=[{'name': 'list_cases', 'args': {}}],
                       finish_reason='tool_calls')


def test_llm_prints_what_is_in_force(qapp, tmp_path, capsys):
    session, _ = buildSession(qapp, tmp_path)
    assert execute(parse('/llm'), session)
    out = capsys.readouterr().out
    assert DEAD_ENDPOINT in out
    for word in ('endpoint', 'model', 'key', 'max_turns', 'temperature',
                 'max_tokens'):
        assert word in out


def test_llm_endpoint_is_set_persisted_and_in_force(
        qapp, tmp_path, monkeypatch, capsys):
    """`/llm endpoint` is the one change the client persists: the line
    lands in the preferences file the GUI reads, the in-memory value
    moves with it, and the client in force answers the new endpoint."""
    monkeypatch.setenv('HOME', str(tmp_path))
    session, _ = buildSession(qapp, tmp_path)
    new = 'http://10.0.0.7:8080/v1'
    execute(parse('/llm endpoint %s' % new), session)
    prefs = tmp_path / '.imasviz' / 'preferences'
    assert prefs.is_file()
    assert ('AgentLLMEndpoint=%s' % new) in prefs.read_text()
    assert session.llm.endpoint == new
    capsys.readouterr()


def test_llm_refuses_an_unknown_field_by_name(qapp, tmp_path):
    session, _ = buildSession(qapp, tmp_path)
    try:
        execute(parse('/llm banana 1'), session)
    except ValueError as e:
        text = str(e).lower()
        assert 'banana' in text
        for field in ('endpoint', 'model', 'key'):
            assert field in text
    else:
        raise AssertionError('an unknown /llm field must be refused by name')


def test_llm_endpoint_must_be_an_http_url(qapp, tmp_path):
    session, _ = buildSession(qapp, tmp_path)
    try:
        execute(parse('/llm endpoint notanurl'), session)
    except ValueError as e:
        assert 'http' in str(e)
    else:
        raise AssertionError('a non-http endpoint must be refused by name')


def test_llm_max_turns_and_sampling_are_session_only(qapp, tmp_path):
    """The loop parameters steer this client run: set, read back, and
    refused by name when they are not the number they claim to be."""
    session, _ = buildSession(qapp, tmp_path)
    execute(parse('/llm max_turns 4'), session)
    assert session.max_turns == 4
    execute(parse('/llm temperature 0.7'), session)
    assert session.llm.temperature == 0.7
    execute(parse('/llm max_tokens 321'), session)
    assert session.llm.max_tokens == 321
    for line in ('/llm max_turns zero', '/llm temperature -1',
                 '/llm max_tokens -8'):
        try:
            execute(parse(line), session)
        except ValueError:
            pass
        else:
            raise AssertionError('%s must be refused by name' % line)
    assert session.max_turns == 4


def test_mcp_answers_endpoint_models_and_every_tool(qapp, tmp_path, capsys):
    """`/mcp` is the answer to 'what can this session give today': the
    endpoint, the models when they answer -- the named refusal when they
    do not -- and every tool of the agent, by its schema's name."""
    from imasviz.VizAgent.tools import TOOLS
    session, _ = buildSession(qapp, tmp_path)
    execute(parse('/mcp'), session)
    out = capsys.readouterr().out
    assert DEAD_ENDPOINT in out
    assert 'unanswered' in out          # the models probe, named
    for tool in TOOLS:
        assert tool['function']['name'] in out
    assert '(run it with /mcp <name>)' in out


def test_mcp_one_gesture_and_the_refusal_of_another(qapp, tmp_path):
    session, _ = buildSession(qapp, tmp_path)
    execute(parse('/mcp open_case'), session)
    try:
        execute(parse('/mcp banana'), session)
    except ValueError as e:
        assert 'banana' in str(e)
        assert 'open_case' in str(e)     # the answer names what it does hold
    else:
        raise AssertionError('an unknown gesture must be refused by name')


def test_a_prompt_is_answered_and_its_turn_is_left_on_disk(qapp, tmp_path):
    llm = FakeLLMClient([toolCall(),
                         LLMResponse(content='Le cas est ouvert.',
                                     finish_reason='stop')])
    session, _ = buildSession(qapp, tmp_path, llm=llm)
    out = session.runPrompt('liste les cas ouverts')
    assert out['refusal'] is None
    turn = out['dir']
    with open(turn + '/SlicesPlot1.png', 'rb') as f:
        assert f.read() == PNG_1x1
    with open(turn + '/00_app.png', 'rb') as f:
        assert f.read() == PNG_1x1
    with open(turn + '/transcript.txt') as f:
        transcript = f.read()
    assert 'Le cas est ouvert.' in transcript
    assert 'list_cases' in transcript


def test_a_refused_turn_is_named_and_still_saved(qapp, tmp_path):
    """The refusal (the truncation, here) is not a silence: it is named
    in the outcome and the transcript, and the turn still leaves its
    images on disk -- the rule `test_112` pins for the one-shot."""
    llm = FakeLLMClient([LLMResponse(content='partial...',
                                     finish_reason='length')])
    session, _ = buildSession(qapp, tmp_path, llm=llm)
    out = session.runPrompt('une requete trop longue')
    assert out['refusal'] is not None
    with open(out['dir'] + '/transcript.txt') as f:
        transcript = f.read()
    assert 'REFUSAL' in transcript
    import os
    assert os.path.isfile(out['dir'] + '/00_app.png')


def test_the_context_survives_between_two_prompts(qapp, tmp_path):
    """What `test_110` could not see from one side: the second prompt is
    asked **with** the first exchange -- its user line and its answer --
    so 'et maintenant le suivant' can point, without naming the case
    again. A fresh loop per prompt would send a history holding only
    the new line."""
    llm = FakeLLMClient([
        toolCall(),
        LLMResponse(content='Premier : le cas est ouvert.',
                    finish_reason='stop'),
        toolCall(),
        LLMResponse(content='Deuxieme : toujours le meme cas ouvert.',
                    finish_reason='stop'),
    ])
    session, _ = buildSession(qapp, tmp_path, llm=llm)
    assert session.runPrompt('ouvre le cas de reference')['refusal'] is None
    out = session.runPrompt('et maintenant le suivant')
    assert out['refusal'] is None
    # The turn of the second prompt starts at the third chat: the first
    # asked the model, then the tool's answer was asked again before the
    # first turn stopped. The context is asked of this third one.
    second = llm.calls[2]
    contents = [m.get('content') or '' for m in second]
    # The first exchange in full: its user line, its answer -- and then
    # the new line, the second prompt itself. 'meme cas' is the answer
    # of this very turn, and cannot be in what it is asked with.
    assert any('et maintenant le suivant' in c for c in contents)
    assert any('Premier : le cas est ouvert.' in c for c in contents)
    assert any('ouvre le cas de reference' in c for c in contents)


def test_history_lists_the_prompts_in_order(qapp, tmp_path, capsys):
    llm = FakeLLMClient([LLMResponse(content='un.', finish_reason='stop')
                         for _ in range(3)])
    session, _ = buildSession(qapp, tmp_path, llm=llm)
    session.runPrompt('le premier prompt')
    session.runPrompt('le deuxieme prompt')
    assert execute(parse('/history'), session)
    out = capsys.readouterr().out
    assert 'le premier prompt' in out
    assert 'le deuxieme prompt' in out
    assert out.index('le premier prompt') < out.index('le deuxieme prompt')


def test_shots_moves_the_turn_directory(qapp, tmp_path):
    llm = FakeLLMClient([LLMResponse(content='ok.', finish_reason='stop')])
    session, _ = buildSession(qapp, tmp_path, llm=llm)
    new = str(tmp_path / 'alt' / 'shots')
    execute(parse('/shots %s' % new), session)
    out = session.runPrompt('une image')
    assert out['dir'].startswith(new)


def test_ids_prints_the_held_idss_without_the_llm(qapp, tmp_path, capsys):
    """`/ids` reads `list_case_idss` off the core and prints it raw -- no
    LLM, no round-trip: the names and their occurrence counts come to the
    terminal straight from the case."""
    session, core = buildSession(qapp, tmp_path)
    core.list_case_idss  # exercised below, present on the core
    assert execute(parse('/ids'), session)
    out = capsys.readouterr().out
    assert 'equilibrium' in out and '0, 1, 2, 3' in out
    assert 'magnetics' in out and '0' in out
    # The command names the case and the count, the way the /session lines do.
    assert 'IDS 2 held by %s' % CASE_URI in out


def test_ids_with_a_uri_passes_it_to_the_core(qapp, tmp_path, capsys):
    """With a URI, `/ids` reads that case, not the single open one."""
    session, core = buildSession(qapp, tmp_path)
    assert execute(parse('/ids %s' % CASE_URI), session)
    out = capsys.readouterr().out
    assert 'equilibrium' in out
    assert CASE_URI in out


class _CoreWithTwoCases:
    """A core that holds two cases at once: `/ids` with no URI must refuse."""
    def list_cases(self):
        return [{'uri': CASE_URI}, {'uri': CASE_URI + '/sibling'}]


def test_ids_with_no_case_and_no_uri_is_refused_named(qapp, tmp_path):
    """No case open and no URI: the refusal names the need for a case."""
    session = CliSession(
        app=None, window=None, core=type('C', (), {
            'list_cases': lambda self: []})(),
        llm=None, shots_dir=str(tmp_path))
    try:
        execute(parse('/ids'), session)
    except ValueError as e:
        assert 'uri' in str(e).lower() or 'case' in str(e).lower()
    else:
        raise AssertionError('/ids with no case and no URI must be refused')


def test_ids_with_two_cases_and_no_uri_is_refused_named(qapp, tmp_path):
    """More than one case open and no URI: name which one, not guess."""
    session = CliSession(
        app=None, window=None, core=_CoreWithTwoCases(),
        llm=None, shots_dir=str(tmp_path))
    try:
        execute(parse('/ids'), session)
    except ValueError as e:
        assert '2' in str(e)
    else:
        raise AssertionError('/ids is ambiguous when more than one case is open')


def test_session_save_and_restore_go_through_the_core(qapp, tmp_path):
    llm = FakeLLMClient([])
    session, core = buildSession(qapp, tmp_path, llm=llm)
    execute(parse('/session save myname'), session)
    execute(parse('/session restore myname'), session)
    assert core.saved == ['myname']
    assert core.restored == ['myname']
    try:
        execute(parse('/session save'), session)
    except ValueError as e:
        assert 'name' in str(e).lower()
    else:
        raise AssertionError('/session save without a name must be refused')


def test_unknown_command_is_refused_named(qapp, tmp_path):
    session, _ = buildSession(qapp, tmp_path)
    try:
        execute(parse('/banana'), session)
    except ValueError as e:
        text = str(e)
        assert 'banana' in text
        for command in ('/llm', '/mcp', '/history', '/help', '/quit'):
            assert command in text
    else:
        raise AssertionError('an unknown command must be refused by name')


def test_help_names_the_commands():
    for command in ('/llm', '/mcp', '/shots', '/session', '/history',
                    '/help', '/quit'):
        assert command in help_text()


def test_main_oneshot_delegates_to_run_agent_mode(monkeypatch):
    """The one-shot path is the one `test_112` already pins: `main` maps
    its prompt onto the argument the one-shot reads, and carries back
    its exit code."""
    calls = {}

    def fakeRunAgentMode(args):
        calls['args'] = args
        return 0

    monkeypatch.setattr('mcp_server.agent_mode.runAgentMode',
                        fakeRunAgentMode)
    from viz_cli import run
    code = run.main(['le prompt de la journee',
                     '--llm-url', 'http://10.0.0.1:8080/v1'])
    assert code == 0
    assert calls['args'].agent == 'le prompt de la journee'
    assert calls['args'].llm_url == 'http://10.0.0.1:8080/v1'


def test_main_oneshot_refuses_an_empty_prompt(capsys):
    """Nothing after the prompt is the refusal of the one-shot, named
    before anything is built for it -- and `test_112` pins the same
    rule on the flag it reads."""
    from viz_cli import run
    code = run.main([''])
    assert code == 1
    assert 'REFUSAL' in capsys.readouterr().err


def test_history_lands_in_the_file_and_comes_back(tmp_path):
    """The file is plain text under $HOME/.imasviz, as the preferences:
    a line added is in it, and the client that reopens it holds the
    lines it holds already. Two consecutive additions of the same line
    cost one entry, the rule the shells apply."""
    from viz_cli.history import History
    path = str(tmp_path / '.imasviz' / 'cli_history')
    history = History(path)
    line = "trace le champ de l'iteration 0"
    history.add(line)
    history.add(line)
    with open(path) as f:
        held = f.read()
    assert held.count(line) == 1
    again = History(path)
    assert again.entries == [line]


def test_the_arrows_walk_the_history_and_the_typed_line_comes_back(
        tmp_path):
    """The up and down walk, as a shell walks its own: up from the current
    line gives the newest, again the one before, and down from the
    oldest gives the line the walk left back. Driven through a real
    pty, because the editor is `termios` and `select` and a pipe would
    not reach it."""
    import io
    import os
    import pty
    import sys

    from viz_cli.history import History
    from viz_cli import tui

    history = History(str(tmp_path / 'cli_history'))
    history.add('premier prompt')
    history.add('deuxieme prompt')

    master, slave = pty.openpty()
    keep_in = os.dup(0)
    keep_out = sys.stdout
    os.dup2(slave, 0)
    sys.stdout = io.StringIO()
    try:
        # Up, then Return: the newest walked line is the one read out.
        os.write(master, b'\x1b[A\r')
        newest = tui.readLine('> ', history=history)
        os.write(master, b'\x1b[A\r')
        before = tui.readLine('> ', history=history)
        os.write(master, b'\x1b[B\r')
        back = tui.readLine('> ', history=history)
    finally:
        sys.stdout = keep_out
        os.dup2(keep_in, 0)
        os.close(master)
        os.close(slave)

    assert newest == 'deuxieme prompt'
    assert before == 'premier prompt'
    # Down from the oldest line: the walk ends, and the line it left --
    # here the empty one -- is what comes back.
    assert back == ''
