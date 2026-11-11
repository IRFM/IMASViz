# Copyright holders: Commissariat à l'Energie Atomique et aux Energies
# Alternatives (CEA), France; and Laboratory for Engineering Design - LECAD,
# University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C
# open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted
# upon downloading the software and/or exercising any of the rights granted
# under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""A destructive gesture is asked, not taken.

`close_window`, `close_case` and `new_session` are the three
bookkeeping-erasing gestures of the session, and a figure they delete is
gone when it is gone: "un plot perd" in the field is one of them with no
close in the user's request. The loop is the one surface the model
decides them with, and it is also the one the page's buttons act through
(`callGesture` runs `AgentLoop._dispatch`), so the rule lives there and
the two callers are told apart by who asked:

* a gesture the MODEL takes is refused by name when the user's request
  does not ask for a closure -- no window, case or session to close, no
  reset -- and is run once the same request asks for it ("close Plot5",
  "ferme la figure", "nouvelle session");
* a gesture the USER takes through the `requested_by='user'` caller is
  the button's own: the user IS the ask, and no word is owed to it;
* the refusal never runs the gesture: the figure, the case and the
  session it named are still there after a refused turn, and the loop's
  memory goes with the new session that was allowed, not the one that
  was refused.

The one path this does not touch: the standalone MCP server
(`mcp_server/tools.py`) maps its tools onto the core directly -- its
caller is the user's own program, and the ask is that program's.
"""

import pytest

from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.llm_client import LLMResponse

from test_115_agent_no_confabulation import (
    FakeCore, FakeDispatcher, FakeLLMClient)


class ClosingCore(FakeCore):
    """The three destructive answers, recorded in the order they were
    asked for: a gesture the guard refused must stay an empty list, and a
    gesture it let through the one name it erased."""
    def __init__(self):
        self.closed = []

    def close_window(self, key):
        self.closed.append(('close_window', key))
        return {'closed': key}

    def close_case(self, uri):
        self.closed.append(('close_case', uri))
        return {'closed': uri}

    def new_session(self):
        self.closed.append(('new_session', None))
        return {'closed': 0, 'saved_to': None}


@pytest.fixture
def agent_kwargs(qapp):
    return {'main_window': None, 'api': None}


def _run(agent, prompt):
    lines, errors = [], []
    agent.transcriptLine.connect(lines.append)
    agent.askFinished.connect(errors.append)
    agent.ask(prompt)
    return ' '.join(lines), errors


def _oneTool(name, args, then):
    return [
        LLMResponse(content='', finish_reason='tool_calls',
                    tool_calls=[{'name': name, 'args': args}]),
        LLMResponse(content=then, tool_calls=None, finish_reason='stop'),
    ]


# ---------------------------------------------------------- the model path

def test_an_unasked_close_window_is_refused_and_the_figure_stands(agent_kwargs):
    """'trace la pression' names no closure. A model that calls
    `close_window` on that turn is refused by name, the gesture never
    runs, and the figure it named is still on the other side of the
    refusal -- the "Plot2/Plot3 créées puis disparues" of the field is
    this with no ask in between."""
    core = ClosingCore()
    llm = FakeLLMClient(_oneTool(
        'close_window', {'key': 'Plot2'},
        'Le tracage est ouvert (Plot1). Je n’ai pas fermé Plot2 : '
        'veux-tu que je le ferme ?'))
    agent = AgentLoop(core=core, llm=llm, dispatcher=FakeDispatcher(),
                      **agent_kwargs)
    joined, errors = _run(agent, 'trace la pression sur la pression du slice')
    assert core.closed == [], \
        'a destructive gesture must not run on a request that does not ' \
        'ask for it: %r' % core.closed
    assert errors == [None], \
        'the answer is what reaches the user, not a crash on the guard'
    assert 'REFUSAL' in joined, 'the refusal is named, not a silence'
    assert 'close_window' in joined, 'it names the gesture it refused'
    assert 'ask' in joined.lower(), \
        'the rule is stated: a closure is asked for, not taken'


def test_the_same_close_is_run_once_the_request_asks_for_it(agent_kwargs):
    """'ferme Plot2' IS the ask: the guard stands aside, the gesture runs,
    and the answer is let stand -- a refusal here would be the same
    failure in the other direction (a window the user asked to close,
    still open because the loop second-guessed)."""
    core = ClosingCore()
    llm = FakeLLMClient(_oneTool(
        'close_window', {'key': 'Plot2'},
        'Plot2 est fermée.'))
    agent = AgentLoop(core=core, llm=llm, dispatcher=FakeDispatcher(),
                      **agent_kwargs)
    _run(agent, 'ferme Plot2')
    assert core.closed == [('close_window', 'Plot2')], \
        'an asked closure is the gesture the loop must run: %r' \
        % core.closed


def test_an_unasked_new_session_is_refused_and_the_memory_stands(agent_kwargs):
    """A `new_session` with no reset in the request refuses the same way,
    and the loop's own memory -- the state `5dcd55a` cleared on an
    allowed one -- survives the refused one: a reset that never ran is not
    a slate cleared."""
    core = ClosingCore()
    loop = AgentLoop(core=core, llm=FakeLLMClient(_oneTool(
        'new_session', {},
        'Je n’ai rien refermé, la session tient : les figures sont '
        'encore là.')),
        dispatcher=FakeDispatcher())
    loop.history = [{'role': 'user', 'content': 'trace la pression'}]
    loop.transcriptLine.connect(lambda line: None)
    loop.askFinished.connect(lambda reason: None)
    loop.ask('montre-moi les figures ouvertes')
    assert core.closed == [], \
        'a new session the request does not name must not run: %r' \
        % core.closed
    assert loop.history, \
        'a refused new session is not a clean slate: the loop still held ' \
        'the turns it served'


def test_an_asked_new_session_runs_and_clears_the_memory(agent_kwargs):
    """'nouvelle session' is the ask: it runs, and -- the `5dcd55a` half --
    the loop's memory goes with it: the turns served before the reset are
    the clean slate, not the conversation about the reset itself (the
    loop keeps the turn it is in: the ask that ran the reset and the
    answer it owes to it)."""
    core = ClosingCore()
    loop = AgentLoop(core=core, llm=FakeLLMClient(_oneTool(
        'new_session', {}, 'La session est à neuf.')),
        dispatcher=FakeDispatcher())
    # Two turns served before the reset: a request of the case and the
    # figure it drew. That is the memory the next turn must not be able
    # to recite -- the "is a case open?" answered from the old session.
    loop.history = [
        {'role': 'user',
         'content': 'trace la pression du slice dans une figure'},
        {'role': 'assistant', 'content': 'Plot5 : la pression est tracée.'},
    ]
    loop.transcriptLine.connect(lambda line: None)
    loop.askFinished.connect(lambda reason: None)
    loop.ask('nouvelle session, pars de zéro')
    assert core.closed == [('new_session', None)], \
        'the asked new session is the gesture the loop must run: %r' \
        % core.closed
    remembered = [m.get('content') or '' for m in loop.history]
    joined = ' '.join(remembered)
    assert 'Plot5' not in joined and 'trace la pression' not in joined, \
        'the allowed new session is the clean slate: the turns served ' \
        'before it are the ones that go, not the conversation about ' \
        'the reset itself: %r' % remembered


def test_an_unasked_close_case_is_refused_and_the_case_stands(agent_kwargs):
    """The third of the three, the one that takes the whole case and its
    own figures: the same refusal, on the same request that does not
    name it."""
    core = ClosingCore()
    llm = FakeLLMClient(_oneTool(
        'close_case', {'uri': 'imas:hdf5?path=/fake'},
        'Le cas est encore ouvert, je ne l’ai pas refermé.'))
    agent = AgentLoop(core=core, llm=llm, dispatcher=FakeDispatcher(),
                      **agent_kwargs)
    joined, errors = _run(agent, 'liste les cas ouverts')
    assert core.closed == [], \
        'a close_case on a request that does not ask for it does not ' \
        'run: %r' % core.closed
    assert errors == [None]
    assert 'REFUSAL' in joined and 'close_case' in joined


# ------------------------------------------------------------ the button

def test_the_button_path_asks_no_question(agent_kwargs):
    """The page's New-session button and its per-figure close act
    `callGesture` -> `AgentLoop._dispatch(requested_by='user')`: the
    click IS the ask, and there is no user-prompt text to check. A guard
    that asks the button for a word it cannot give would be the refusal
    in the wrong direction, and a button that could not close a window is
    a window it cannot take away."""
    core = ClosingCore()
    agent = AgentLoop(core=core, llm=FakeLLMClient([]),
                      dispatcher=FakeDispatcher(), **agent_kwargs)
    out = agent._dispatch('close_window', {'key': 'Plot5'},
                          requested_by='user')
    assert out == {'closed': 'Plot5'}, out
    assert core.closed == [('close_window', 'Plot5')], core.closed
    out = agent._dispatch('new_session', {}, requested_by='user')
    assert core.closed[-1] == ('new_session', None), core.closed
