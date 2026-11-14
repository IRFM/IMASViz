# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The agent's prompt history: a file a new session cannot reach, and the box
that recalls it.

What it pins, scripted, off the reference case:

* the file store -- an appended prompt is read back; a prompt already held
  is recalled, not repeated; a list past the cap keeps the newest prompts;
  an empty prompt and a file that is not a list of prompts are refused by
  name; ``HOME`` unset is a refusal too (the folder it would write to is
  not).
* the panel -- the box lists the file's prompts newest first; selecting a
  line puts that prompt back in the input box; a run records its prompt
  into the file and the box; and ``Effacer`` clears the input box and the
  transcript but does not touch the history.

``HOME`` is pointed at a test folder for the whole file (the ``test_39*``
pattern) so neither the store nor the panel reads the user's own
``~/.imasviz/agent_prompts``.
"""

import os

import pytest

from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.llm_client import LLMResponse
from imasviz.VizAgent.QVizPromptHistory import QVizPromptHistory


@pytest.fixture(autouse=True)
def _agent_home(tmp_path, monkeypatch):
    """The store and the panel both live under ``$HOME/.imasviz``; a test
    here must not read or write the user's real prompt history, so the
    home it works in is its own, and pytest puts it back."""
    monkeypatch.setenv('HOME', str(tmp_path))


class _LLM:
    """A scripted LLM that answers in one turn (a final answer, no tool)."""
    def chat(self, messages, tools=None, **kwargs):
        return LLMResponse(content='done.', tool_calls=None,
                           finish_reason='stop')


class _Core:
    """A stand-in gesture surface; the scripted turn never reaches it."""


class _Dispatcher:
    def call(self, function, timeout=300.0):
        return function()


# ---------------------------------------------------------------- the file

def test_append_then_load_roundtrip():
    QVizPromptHistory.append('open the case')
    QVizPromptHistory.append('trace the flux')
    assert QVizPromptHistory.load() == ['open the case', 'trace the flux']


def test_most_recent_first():
    for one in ('one', 'two', 'three'):
        QVizPromptHistory.append(one)
    assert QVizPromptHistory.mostRecentFirst() == ['three', 'two', 'one']


def test_most_recent_first_limit():
    for one in ('one', 'two', 'three', 'four'):
        QVizPromptHistory.append(one)
    assert QVizPromptHistory.mostRecentFirst(limit=2) == ['four', 'three']


def test_recalled_prompt_is_recalled_not_repeated():
    QVizPromptHistory.append('a')
    QVizPromptHistory.append('b')
    QVizPromptHistory.append('a')  # already held -> recalled to the newest
    assert QVizPromptHistory.load() == ['b', 'a']


def test_cap_keeps_the_newest():
    from imasviz.VizAgent.QVizPromptHistory import MAX_HISTORY
    for i in range(MAX_HISTORY + 5):
        QVizPromptHistory.append('p%d' % i)
    entries = QVizPromptHistory.load()
    assert len(entries) == MAX_HISTORY
    assert entries[0] == 'p5'          # p0..p4 dropped at the cap
    assert entries[-1] == 'p%d' % (MAX_HISTORY + 4)


def test_empty_prompt_is_refused():
    with pytest.raises(ValueError):
        QVizPromptHistory.append('   ')


def test_home_unset_is_refused(monkeypatch):
    monkeypatch.delenv('HOME')
    with pytest.raises(ValueError):
        QVizPromptHistory.directory()


def test_file_that_is_not_a_list_is_refused(tmp_path):
    folder = os.path.join(str(tmp_path), '.imasviz')
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, 'agent_prompts'), 'w') as f:
        f.write('{"not": "a list of prompts"}')
    with pytest.raises(ValueError):
        QVizPromptHistory.load()


# ----------------------------------------------------------------- the panel

def _build(agent):
    from imasviz.VizAgent.panel import QVizAgentPanel
    return QVizAgentPanel(main_window=None, api=None, agent=agent)


def test_box_lists_the_file_newest_first(qapp):
    QVizPromptHistory.append('open the case')
    QVizPromptHistory.append('trace the flux')
    panel = _build(agent=None)
    assert panel.promptHistoryBox.count() == 2
    assert panel.promptHistoryBox.itemText(0) == 'trace the flux'
    assert panel.promptHistoryBox.itemText(1) == 'open the case'


def test_selecting_a_line_fills_the_input_box(qapp):
    QVizPromptHistory.append('open the case')
    QVizPromptHistory.append('trace the flux')
    panel = _build(agent=None)
    panel.promptHistoryBox.setCurrentIndex(0)
    panel._onHistorySelected(0)
    assert panel.promptEdit.toPlainText() == 'trace the flux'


def test_a_run_records_its_prompt(qapp):
    agent = AgentLoop(core=_Core(), llm=_LLM(), dispatcher=_Dispatcher())
    panel = _build(agent=agent)
    panel.setPrompt('do something new')
    panel.runAgent()  # records the prompt, then drives the scripted turn
    assert 'do something new' in QVizPromptHistory.load()
    # and the box refreshed to hold it newest first, pointing at it
    assert panel.promptHistoryBox.count() == 1
    assert panel.promptHistoryBox.itemText(0) == 'do something new'
    assert panel.promptHistoryBox.currentIndex() == 0


def test_effacer_clears_the_box_not_the_history(qapp):
    QVizPromptHistory.append('an older prompt')
    panel = _build(agent=None)
    panel.setPrompt('typed now')
    panel.transcript.appendPlainText('a line of the transcript')
    panel._recordPrompt('typed now')  # what a run does before driving
    panel._onClear()
    # the input box and the transcript are cleared ...
    assert panel.promptEdit.toPlainText() == ''
    assert panel.transcript.toPlainText() == ''
    # ... and the history keeps both prompts, and the box still lists them.
    assert sorted(QVizPromptHistory.load()) == ['an older prompt', 'typed now']
    assert panel.promptHistoryBox.count() == 2
