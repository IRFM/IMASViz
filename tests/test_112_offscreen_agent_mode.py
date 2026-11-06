# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The one-shot agent mode: prompt, local model, the images behind.

What it pins, in the order the mode must answer them:

* a scripted LLM (no network, the stand-in of `test_110`) whose tool call
  goes through the **real** `GuiDispatcher` and the **real** event pump:
  exit 0, the app and the session's windows on disk as PNGs, the
  transcript beside them;
* a refused loop (truncation, `max_turns`) is **still** saved -- the
  images and the transcript come to disk either way -- and the exit
  code says 1 with the refusal named;
* the model rule, asked of the `LLMClient` built for the run: an
  endpoint named without a model resolves from `/v1/models`, a named
  model is kept, and without an endpoint the preferences stand;
* an empty prompt is refused by name before any window is built.
"""

import base64
import os

from imasviz.VizAgent.llm_client import LLMResponse, _messagesForRequest

from mcp_server.agent_mode import buildLLM, runAgentMode
from mcp_server.run import parseArguments

# A 1x1 transparent PNG: the file tests check the magic, not the pixels.
PNG_1x1 = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
    'AAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')

CASE_URI = ('imas:hdf5?path='
            '/afs/eufus.eu/g2itmdev/user/g2lfleur/public/imasdb/west/3/54924/0')


class FakeLLMClient:
    """The scripted LLM of `test_110`, kept: one response per turn."""
    def __init__(self, responses):
        self.responses = list(responses)

    def chat(self, messages, tools=None, **kwargs):
        if not self.responses:
            raise AssertionError('FakeLLMClient: no more scripted responses')
        return self.responses.pop(0)


class FakeCore:
    """A core that answers PNGs: the app, one case view (no figure key,
    as `QVizWindowRecord` answers for it), and one figure window."""
    def list_windows(self):
        return [
            {'kind': 'case view', 'label': '54924 / 0', 'key': None,
             'visible': True, 'cases': [CASE_URI]},
            {'kind': 'SlicesPlot', 'label': 'SlicesPlot 1',
             'key': 'SlicesPlot1', 'visible': True, 'cases': []}]

    def screenshot(self, window):
        if window not in ('app', 'SlicesPlot1', CASE_URI):
            raise ValueError('no such window: %r' % window)
        return PNG_1x1

    def list_cases(self):
        return []


def AWindow():
    """What runAgentMode asks of the window: nothing but the session's api."""
    class AWindow(object):
        def sessionApi(self):
            return None
    return AWindow()


def buildArgs(tmp_path, extra=None):
    """The command line of one run, its output under a directory of the
    test -- the real parser, not a stand-in namespace."""
    argv = ['--agent', 'do it', '--shots', str(tmp_path / 'shots')]
    if extra:
        argv += extra
    return parseArguments(argv)


def test_happy_path_saves_images_and_transcript(qapp, tmp_path):
    """An answered loop: exit 0, the app and the figure on disk as PNGs,
    the transcript beside them. The tool call ran through the real
    dispatcher and the real event pump."""
    args = buildArgs(tmp_path)
    llm = FakeLLMClient([
        LLMResponse(content='', tool_calls=[{'name': 'list_cases', 'args': {}}],
                    finish_reason='tool_calls'),
        LLMResponse(content='The case is open and the figure is drawn.',
                    finish_reason='stop'),
    ])
    code = runAgentMode(args, app=qapp, window=AWindow(),
                        core=FakeCore(), llm=llm)
    assert code == 0
    shots = tmp_path / 'shots'
    for name in ('00_app.png', 'SlicesPlot1.png'):
        with open(shots / name, 'rb') as f:
            assert f.read() == PNG_1x1
    # The case view answers no figure key: its file is named from the
    # tail of the case it serves, and it is there too.
    case_files = [p.name for p in shots.iterdir()
                  if p.name.startswith('case_') and p.name.endswith('.png')]
    assert case_files == ['case_afs_eufus.eu_g2itmdev_user_g2lfleur_public_'
                          'imasdb_west_3_54924_0.png']
    with open(shots / case_files[0], 'rb') as f:
        assert f.read() == PNG_1x1
    transcript = (shots / 'transcript.txt').read_text()
    assert 'The case is open and the figure is drawn.' in transcript
    assert 'list_cases' in transcript


def test_refused_loop_still_saves_and_says_one(qapp, tmp_path):
    """A refusal (the truncation, here) is not a silence: the images and
    the transcript come to disk for what was drawn, the exit code says 1,
    and the transcript names it."""
    args = buildArgs(tmp_path)
    llm = FakeLLMClient([
        LLMResponse(content='partial answer...', finish_reason='length'),
    ])
    code = runAgentMode(args, app=qapp, window=AWindow(),
                        core=FakeCore(), llm=llm)
    assert code == 1
    shots = tmp_path / 'shots'
    assert (shots / '00_app.png').is_file()
    assert (shots / 'SlicesPlot1.png').is_file()
    transcript = (shots / 'transcript.txt').read_text()
    assert 'REFUSAL' in transcript
    assert 'truncated' in transcript


def test_max_turns_is_the_limit_and_names_it(qapp, tmp_path):
    """The loop stops at the turn limit, the exit code says 1, and the
    refusal names the limit -- not the number of responses the stand-in
    held (here 3 more than the limit)."""
    from imasviz.VizAgent.llm_client import LLMResponse as Resp
    args = buildArgs(tmp_path, extra=['--max-turns', '2'])
    llm = FakeLLMClient([
        Resp(content='', tool_calls=[{'name': 'list_cases', 'args': {}}],
             finish_reason='tool_calls')
        for _ in range(6)
    ])
    code = runAgentMode(args, app=qapp, window=AWindow(),
                        core=FakeCore(), llm=llm)
    assert code == 1
    assert len(llm.responses) == 6 - 2
    transcript = (tmp_path / 'shots' / 'transcript.txt').read_text()
    assert 'max_turns' in transcript


def test_endpoint_without_model_resolves_from_models(monkeypatch, tmp_path):
    """An endpoint named without a model: the model is left to be read
    from the endpoint's first /v1/models entry (a llama-server is where
    this lands). No network here: the rule is asked of the built
    client, and the default name of the preferences is not used."""
    monkeypatch.setenv('HOME', str(tmp_path))
    args = parseArguments(['--agent', 'x',
                           '--llm-url', 'http://10.0.0.1:8080/v1'])
    client = buildLLM(args)
    assert client.endpoint == 'http://10.0.0.1:8080/v1'
    assert client.model is None


def test_named_model_is_kept(monkeypatch, tmp_path):
    """A named model -- with or without an endpoint -- is the one
    sent: the preferences and the model list do not override it."""
    monkeypatch.setenv('HOME', str(tmp_path))
    client = buildLLM(parseArguments(
        ['--agent', 'x', '--llm-url', 'http://10.0.0.1:8080/v1',
         '--llm-model', 'my-model']))
    assert client.model == 'my-model'
    assert client.endpoint == 'http://10.0.0.1:8080/v1'


def test_no_endpoint_keeps_the_preferences(monkeypatch, tmp_path):
    """Without an endpoint, the preferences stand -- as in the in-app
    agent -- and the configured values are the ones that would be sent.
    The preferences are pinned to their configured defaults, because a
    build() on another test's files may have moved them."""
    from imasviz.VizUtils import QVizPreferences
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr(QVizPreferences, 'AgentLLMEndpoint',
                        'http://127.0.0.1:11434/v1')
    monkeypatch.setattr(QVizPreferences, 'AgentLLMModel', 'qwen3.8:27b')
    client = buildLLM(parseArguments(['--agent', 'x']))
    assert client.model == 'qwen3.8:27b'
    assert client.endpoint == 'http://127.0.0.1:11434/v1'


def test_a_request_ending_on_a_tool_result_is_nudged_with_a_user_line():
    """The loop always ends a request on the last tool result. An
    endpoint that requires the last message to be a user one (Ollama:
    ``HTTP 500: no user query found in messages``) gets one short line
    appended -- and a request that already ends on a user message is
    sent untouched, for the other endpoints."""
    tool_tail = [
        {'role': 'system', 'content': 'instruct'},
        {'role': 'user', 'content': 'do it'},
        {'role': 'assistant', 'content': None, 'tool_calls': [{}]},
        {'role': 'tool', 'name': 'list_cases',
         'content': '{"result": []}'},
    ]
    sent = _messagesForRequest(tool_tail)
    assert sent is not tool_tail
    assert sent[:-1] == tool_tail
    assert sent[-1] == {'role': 'user', 'content': 'Continue.'}

    user_tail = [
        {'role': 'user', 'content': 'do it'},
        {'role': 'assistant', 'content': 'done'},
    ]
    assert _messagesForRequest(user_tail) is user_tail
    assert _messagesForRequest([]) == []


def test_empty_prompt_is_refused_before_anything(qapp, tmp_path):
    """A `--agent` with nothing after it is refused by name -- the
    panel says 'no prompt entered' -- and nothing is built for it."""
    args = parseArguments(['--agent', '', '--shots', str(tmp_path / 'shots')])
    try:
        runAgentMode(args, app=qapp, window=AWindow(),
                     core=FakeCore(), llm=FakeLLMClient([]))
    except ValueError as e:
        assert 'no prompt' in str(e)
    else:
        raise AssertionError('an empty prompt must be refused by name')
