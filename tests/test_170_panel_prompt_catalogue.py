# Copyright holders : Commissariat à l'Energie Atomique et aux Energies
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

"""The prompt catalogue in the agent's panel: the box, the window, the run.

The panel is the surface a user chooses from, so this file pins the two
things a catalogue on a shelf does not have to: that **choosing is not
running** -- picking a line fills the prompt box, and *Tourner* stays the
ask -- and that **a value the user did not type is a value they are
told about**, in the transcript for the combo and in the line under the
field for the window.

Both halves reach the same six gestures of the core (``test_167``), so the
panel grows no catalogue of its own: the box is filled from
``list_prompts``, a choice goes through ``fill_prompt``, the *Prompts…*
window writes with ``save_prompt`` / ``edit_prompt`` / ``delete_prompt``,
and the panel's box is refilled from the same read. A change made in the
window is therefore a change the page and the client see too.

Three refusals are pinned here because they are the ones a hand meets: a
hole nothing answers (the combo refuses in the transcript rather than
filling a box with ``{rho}`` in it), an ask made with no prompt chosen,
and a shared catalogue the node cannot answer -- said in the status line,
not swallowed.

Qt notes: the manager is a non-modal ``QDialog`` held on the panel
(``promptManager``) because a window no Python reference holds dies with
the wrapper that made it, and it is never ``exec()``'d -- a nested event
loop on the GUI thread would stop the transcript behind it. The panel
itself is not shown: only the manager is, and it is taken down at the end
of each test.
"""

import os

import pytest

from PySide6.QtWidgets import QLabel

from imasviz.VizAgent import prompts as promptStore
from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.core import McpGuiCore
from imasviz.VizAgent.llm_client import LLMResponse
from imasviz.VizAgent.QVizPromptCatalog import (
    NO_PROMPT,
    QVizPromptManager,
)

from imasviz.Viz_API import Viz_API

pytestmark = pytest.mark.ui

CASE_URI = ('imas:hdf5?path='
            '/afs/eufus.eu/g2itmdev/user/g2lfleur/public/imasdb/west/3/54924/0')


class _Source:
    def __init__(self, uri):
        self.uri = uri


class _View:
    def __init__(self, uri):
        self.dataSource = _Source(uri)


class _Api:
    def __init__(self, uris):
        self.DTVlist = [_View(uri) for uri in uris]


class FakeLLM:
    """Never asked: no test here runs a turn. An empty queue that is asked
    is a failure of the test, which is how "choosing is not running" is
    checked."""

    def chat(self, messages, tools=None, **kwargs):
        raise AssertionError('the catalogue started a turn on its own')


class FakeDispatcher:
    def call(self, function, timeout=300.0):
        return function()


def _core(uris=(CASE_URI,)):
    made = McpGuiCore.__new__(McpGuiCore)
    made.api = _Api(list(uris))
    made.list_windows = lambda: []
    return made


class FakeWindow:
    def sessionApi(self):
        return None

    def hide(self):
        pass


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setattr('imasviz.VizUtils.QVizPreferences.SharedPromptsDir',
                        '', raising=False)
    return home


@pytest.fixture
def panel(qapp):
    """The panel of a session whose one open case is spelled by a URI, on
    a core that answers the catalogue gestures. Registered in the api's
    ``figureframes`` as every window is, and taken back with it."""
    from imasviz.VizAgent.panel import QVizAgentPanel
    api = Viz_API(None)
    agent = AgentLoop(core=_core(), llm=FakeLLM(),
                      dispatcher=FakeDispatcher(), main_window=FakeWindow(),
                      api=api)
    made = QVizAgentPanel(main_window=None, api=api, agent=agent)
    try:
        yield made
    finally:
        manager = getattr(made, 'promptManager', None)
        if manager is not None:
            manager.hide()
        key = getattr(made, 'figureKey', None)
        if key in api.figureframes:
            del api.figureframes[key]


def filePrompt(core, name, text, **fields):
    return core.save_prompt(text=text, name=name, **fields)


# ---------------------------------------------------------------- the combo

def test_the_box_holds_the_catalogue_grouped_and_addressable(panel):
    core = panel.agent.core
    filePrompt(core, 'Profils 1D', 'trace {ids} de {shot}',
               category='profils', description='une ligne')
    filePrompt(core, 'Bilan', 'le bilan energetique')
    panel._loadCatalogue()

    box = panel.promptCatalogueBox
    assert box.itemText(0) == NO_PROMPT
    labels = [box.itemText(i) for i in range(1, box.count())]
    assert 'profils — Profils 1D  ·  une ligne' in labels
    assert '(sans catégorie) — Bilan' in labels
    # The line is addressable: what the gesture takes is the catalogue and
    # the id, not the label the user reads.
    where = [box.itemData(i) for i in range(box.count()) if box.itemData(i)]
    assert ('personal', 'profils-1d') in where
    assert ('personal', 'bilan') in where
    # Category first, and a separator between two categories.
    assert labels.index('profils — Profils 1D  ·  une ligne') \
        < labels.index('(sans catégorie) — Bilan')


def test_a_choice_fills_the_box_and_names_what_answered(panel):
    """The shot of the open case goes in without a word typed, and the
    transcript says where it came from -- and nothing turns."""
    core = panel.agent.core
    filePrompt(core, 'Spectro', 'le spectrogramme du {shot}',
               variables='shot=')
    panel._loadCatalogue()
    index = _indexOf(panel, 'spectro')
    panel._onCatalogueSelected(index)

    assert panel.promptEdit.toPlainText() == 'le spectrogramme du 54924'
    line = panel.transcript.toPlainText()
    assert 'Catalogue — Spectro' in line
    assert '{shot} (this session)' in line


def test_a_hole_nothing_answers_refuses_rather_than_filling_the_box(panel):
    core = panel.agent.core
    filePrompt(core, 'Rho', 'trace a {rho}')
    panel._loadCatalogue()
    panel.promptEdit.setPlainText('ce qui etait ecrit')
    index = _indexOf(panel, 'rho')
    panel._onCatalogueSelected(index)

    assert panel.promptEdit.toPlainText() == 'ce qui etait ecrit'
    line = panel.transcript.toPlainText()
    assert 'REFUSAL — catalogue:' in line and '{rho}' in line


def test_a_choice_is_not_a_turn(panel):
    """Choosing from a menu is not an ask to start a turn: the model is
    never reached, and the *Tourner* button stays the ask."""
    core = panel.agent.core
    filePrompt(core, 'Spectro', 'le spectrogramme du {shot}')
    panel._loadCatalogue()
    panel._onCatalogueSelected(_indexOf(panel, 'spectro'))
    assert panel.runButton.isEnabled() and not panel.stopButton.isEnabled()


def _indexOf(panel, needle):
    for i in range(panel.promptCatalogueBox.count()):
        data = panel.promptCatalogueBox.itemData(i)
        if data and needle in data[1]:
            return i
    raise AssertionError('the catalogue box holds no %r: %r'
                         % (needle, [panel.promptCatalogueBox.itemText(i)
                                     for i in range(
                                         panel.promptCatalogueBox.count())]))


# ------------------------------------------------------------- the Prompts… window

def test_the_button_opens_one_window_and_raises_it_rather_than_doubling_it(
        panel):
    panel.promptsButton.click()
    first = panel.promptManager
    assert isinstance(first, QVizPromptManager)
    assert first.isVisible(), 'the catalogue window is not on screen'
    assert first.parent() is panel, 'held on the panel, as the history is'

    panel.promptsButton.click()
    assert panel.promptManager is first


def test_the_window_lists_the_catalogue_and_says_the_half_it_cannot_read(panel):
    core = panel.agent.core
    filePrompt(core, 'Profils 1D', 'trace {ids}', category='profils')
    panel.promptsButton.click()
    window = panel.promptManager
    assert window.listBox.count() == 1
    assert 'profils — Profils 1D' in window.listBox.item(0).text()
    # The shared half is said, not hidden: a shorter list with no reason
    # reads as an empty shelf.
    assert 'shared' in window.status.text()
    assert 'SharedPromptsDir' in window.status.text()


def test_the_window_shows_each_hole_and_where_its_value_would_come_from(panel):
    core = panel.agent.core
    filePrompt(core, 'Trois trous', 'trace {ids} de {shot} a {rho}',
               variables='ids=core_profiles; shot=')
    panel.promptsButton.click()
    window = panel.promptManager
    window.listBox.setCurrentRow(0)

    assert window.bodyView.toPlainText() == 'trace {ids} de {shot} a {rho}'
    assert sorted(window._valueEdits) == ['ids', 'rho', 'shot']
    assert window._valueEdits['ids'].text() == 'core_profiles'
    assert window._valueEdits['shot'].text() == '54924'
    assert window._valueEdits['rho'].text() == ''
    said = []
    for i in range(window.valuesLayout.count()):
        item = window.valuesLayout.itemAt(i).widget()
        if isinstance(item, QLabel):
            said.append(item.text())
    assert any("the prompt's own default" in one for one in said)
    assert any('this session' in one for one in said)
    assert any('rien ne répond' in one for one in said), \
        'a hole nothing answers says so where the value would be typed'


def test_putting_in_the_box_does_not_run_and_launching_runs_once(panel):
    core = panel.agent.core
    filePrompt(core, 'Spectro', 'le spectrogramme du {shot}')
    panel.promptsButton.click()
    window = panel.promptManager
    window.listBox.setCurrentRow(0)

    ran = []
    panel._onRun = lambda: ran.append(panel.promptEdit.toPlainText())

    window.putButton.click()
    assert panel.promptEdit.toPlainText() == 'le spectrogramme du 54924'
    assert ran == [], 'Mettre dans la boîte ne lance pas le tour'
    assert 'Spectro' in window.status.text()
    assert '{shot} (this session)' in window.status.text()

    window.runButton.click()
    assert ran == ['le spectrogramme du 54924']


def test_a_hole_typed_in_the_window_answers_the_fill_and_is_remembered(panel):
    core = panel.agent.core
    filePrompt(core, 'Rho', 'trace a {rho}')
    panel.promptsButton.click()
    window = panel.promptManager
    window.listBox.setCurrentRow(0)

    window.putButton.click()
    assert 'REFUSAL —' in window.status.text() and '{rho}' \
        in window.status.text()
    assert panel.promptEdit.toPlainText() == ''

    window._valueEdits['rho'].setText('0.85')
    window.putButton.click()
    assert panel.promptEdit.toPlainText() == 'trace a 0.85'
    assert promptStore.lastValues() == {'personal/rho': {'rho': '0.85'}}

    # The next time the same prompt is opened, the hole arrives filled
    # with what was typed last time -- and the line says so.
    window.refresh()
    window.listBox.setCurrentRow(0)
    assert window._valueEdits['rho'].text() == '0.85'


def test_the_asks_of_no_chosen_prompt_are_refused_rather_than_empty(panel):
    panel.promptsButton.click()
    window = panel.promptManager
    for button in (window.putButton, window.runButton, window.deleteButton,
                   window.editButton):
        button.click()
        assert 'REFUSAL —' in window.status.text(), \
            '%s went through with nothing chosen' % button.text()


def test_writing_a_prompt_in_the_window_files_it_and_refills_the_panel_box(
        panel):
    panel.promptsButton.click()
    window = panel.promptManager
    window._newPrompt()
    assert window.nameEdit.isVisible()
    window.nameEdit.setText('Relance')
    window.categoryEdit.setText('bilan')
    window.descriptionEdit.setText('une relance')
    window.bodyEdit.setPlainText('relance du {shot}')
    window.variablesEdit.setText('shot=54924')
    window._saveForm()

    entry = promptStore.PromptStore.read_prompt('personal', 'relance')
    assert entry.body == 'relance du {shot}'
    assert entry.variables == {'shot': '54924'}
    assert 'bilan — Relance  ·  une relance' in [
        panel.promptCatalogueBox.itemText(i)
        for i in range(panel.promptCatalogueBox.count())]
    assert 'save_prompt : relance' in window.status.text()


def test_an_edit_keeps_the_id_a_delete_forgets_the_values_it_remembered(panel):
    core = panel.agent.core
    filePrompt(core, 'Rho', 'trace a {rho}')
    panel.promptsButton.click()
    window = panel.promptManager
    window.listBox.setCurrentRow(0)
    window._valueEdits['rho'].setText('0.4')
    window.putButton.click()
    assert promptStore.lastValues() == {'personal/rho': {'rho': '0.4'}}

    window.listBox.setCurrentRow(0)
    window._openEdit()
    assert not window.nameEdit.isEnabled(), \
        'an edit does not move the id its values are remembered under'
    assert window._editing['id'] == 'rho'
    window.bodyEdit.setPlainText('trace a {rho} avec {shot}')
    window._saveForm()
    entry = promptStore.PromptStore.read_prompt('personal', 'rho')
    assert entry.body == 'trace a {rho} avec {shot}'

    window.listBox.setCurrentRow(0)
    window.deleteButton.click()
    assert not os.path.exists(entry.path)
    assert promptStore.lastValues() == {}, \
        'a deleted prompt keeps no value on the disk'
    assert panel.promptCatalogueBox.count() == 1
    assert 'supprimé : rho' in window.status.text()


def test_the_window_writes_personally_and_the_core_refuses_an_unnamed_shared(
        panel):
    """The window offers no catalogue chooser: what it files is the user's
    own, and the shared half is the core's refusal, named -- never a prompt
    silently filed personally because the shared folder was unreachable."""
    panel.promptsButton.click()
    window = panel.promptManager
    window._newPrompt()
    window.nameEdit.setText('Equipe')
    window.bodyEdit.setPlainText('un prompt de l equipe')
    window._saveForm()
    assert 'save_prompt : equipe' in window.status.text()
    assert promptStore.PromptStore.read_prompt('personal', 'equipe')

    with pytest.raises(ValueError) as exc:
        panel.agent.core.save_prompt(name='Equipe2', text='shared',
                                     scope='shared')
    assert 'SharedPromptsDir' in str(exc.value)
    assert promptStore.PromptStore.list_prompts(scope='shared') == []


def test_the_form_of_a_prompt_can_be_closed_again(panel):
    """The window opens at all only if every button finds its method: a
    connect to a name the class does not carry dies inside the panel's
    click, Qt swallows it, and the catalogue never appears."""
    panel.promptsButton.click()
    window = panel.promptManager
    window._newPrompt()
    assert window.bodyEdit.isVisible()
    window.cancelButton.click()
    assert not window.bodyEdit.isVisible()
    assert not window.saveButton.isVisible()
    assert window._editing is None
    assert window.listBox.isEnabled()


def test_the_window_refuses_an_empty_body_rather_than_filing_a_blank(panel):
    panel.promptsButton.click()
    window = panel.promptManager
    window._newPrompt()
    window.nameEdit.setText('Vide')
    window._saveForm()
    assert 'REFUSAL —' in window.status.text()
    assert window.nameEdit.text() == 'Vide', \
        'the words typed stay in the form: a refusal does not throw them away'
    assert promptStore.PromptStore.list_prompts(scope='personal') == []
