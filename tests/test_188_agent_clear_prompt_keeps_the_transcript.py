# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The agent's clear-the-box button: a discreet × beside the prompt,
that takes the box alone.

The *Clear* button clears the transcript and the box -- the user asked for
a way to empty the field without taking the conversation with it. This pins
the panel's discreet button (the small × beside the box) and its web twin:

* the panel -- the button exists beside the box, is small and disabled
  while the box is empty, and a click empties the box, leaves the
  transcript and the history exactly as they are;
* the page -- the button exists in the markup, disabled at birth, in the
  box's own row (not in the Run/Stop/Clear row), and the handler clears
  the box only -- the transcript, the gallery, the turns and the reports
  are untouched, and the *Clear* button stays wired to the full clear.

``HOME`` is pointed at a test folder for the panel tests (the ``test_39*``
pattern) so the history file never carries the user's real prompts.
"""

import os
import re

import pytest

from imasviz.VizAgent.QVizPromptHistory import QVizPromptHistory


@pytest.fixture(autouse=True)
def _agent_home(tmp_path, monkeypatch):
    """The history file lives under ``$HOME/.imasviz``; a test here must not
    read or write the user's own file."""
    monkeypatch.setenv('HOME', str(tmp_path))


def _build(agent=None):
    from imasviz.VizAgent.panel import QVizAgentPanel
    return QVizAgentPanel(main_window=None, api=None, agent=agent)


# ---------------------------------------------------------------- the panel

def test_the_button_is_discreet_and_beside_the_box(qapp):
    panel = _build()
    button = panel.clearPromptButton
    assert button.text() == '×'
    assert button.maximumWidth() <= 32, 'a discreet button, not a full-size one'
    assert button.maximumHeight() <= 32
    assert button.toolTip(), 'a discreet button carries its own word'
    # the button does not live in the Run/Stop/Clear row: it is beside the
    # box, with the box itself, not inside the buttons.
    row_widgets = [panel.buttonRow.itemAt(i).widget()
                   for i in range(panel.buttonRow.count())]
    assert button not in row_widgets


def test_the_button_is_disabled_while_the_box_is_empty(qapp):
    panel = _build()
    assert panel.clearPromptButton.isEnabled() is False

    panel.setPrompt('trace the flux')
    assert panel.clearPromptButton.isEnabled() is True

    panel.setPrompt('   ')
    assert panel.clearPromptButton.isEnabled() is False

    panel.setPrompt('')
    assert panel.clearPromptButton.isEnabled() is False


def test_a_click_clears_the_box_and_keeps_the_transcript(qapp):
    panel = _build()
    panel.setPrompt('trace the flux')
    panel._appendTranscript('a line of the transcript')
    panel.clearPromptButton.click()
    assert panel.promptEdit.toPlainText() == ''
    assert 'a line of the transcript' in panel.transcript.toPlainText()


def test_a_click_keeps_the_history(qapp):
    QVizPromptHistory.append('an older prompt')
    panel = _build()
    panel.setPrompt('typed now')
    panel.clearPromptButton.click()
    assert panel.promptEdit.toPlainText() == ''
    # the history file and the box are untouched
    assert QVizPromptHistory.load() == ['an older prompt']
    assert panel.promptHistoryBox.count() == 1


def test_the_clear_button_still_clears_the_transcript_and_the_box(qapp):
    """The discreet button does not replace the full clear: *Clear* keeps
    its own promise -- transcript and box, history kept."""
    panel = _build()
    panel.setPrompt('typed')
    panel._appendTranscript('a line of the transcript')
    panel._onClear()
    assert panel.promptEdit.toPlainText() == ''
    assert panel.transcript.toPlainText() == ''


# ------------------------------------------------------------------ the page

def _page():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        '..', 'viz_web', 'static', 'index.html')
    with open(path, encoding='utf-8') as f:
        return f.read()


def test_the_page_offers_a_discreet_button_beside_the_box():
    page = _page()
    assert 'id="clearPromptBtn"' in page, 'the page has no clear-the-box button'
    assert 'id="prompt"' in page
    # the button lives in the box's own row, next to the textarea, not in
    # the Run/Stop/Clear row
    m = re.search(r'<div class="promptRow">(.*?)</div>', page, re.S)
    assert m, 'the box is not in its own row'
    row = m.group(1)
    assert 'id="prompt"' in row, 'the textarea is not in the box row'
    assert 'id="clearPromptBtn"' in row, 'the button is not in the box row'
    # discreet: a small button in its own row, disabled at birth
    assert re.search(r'<button id="clearPromptBtn"[^>]*disabled', row), \
        'the button must start disabled, when the box is empty'
    assert re.search(r'>×</button>', row), \
        'the button carries the discreet glyph'
    # the run/stop/clear row is untouched by this change
    assert '<button id="clearBtn" type="button">Clear</button>' in page
    assert 'clearPromptBtn' not in re.search(
        r'<div class="row">.*?</div>', page, re.S).group(0)


def test_the_page_button_clears_the_box_alone():
    page = _page()
    head = page.index("byId('clearPromptBtn').addEventListener")
    handler = page[head:page.index('});', head)]
    # the handler clears the box, in place, and refocuses it
    assert "'prompt').value = ''" in handler, \
        'the handler must empty the box'
    assert 'focus' in handler, 'the handler must put the focus back on the box'
    # and it must not touch the conversation: no transcript, no gallery,
    # no turns, no reports -- the element the full clear takes
    for gone in ('transcript', 'images', 'turns', 'clearAll'):
        assert gone not in handler, \
            'the handler must clear the box only, not the %s' % gone


def test_the_page_button_is_wired_to_the_box_and_the_input():
    page = _page()
    assert re.search(r"'prompt'\)\.addEventListener\('input', syncClearPromptButton\)",
                     page), 'the button is not kept in sync with the box'
    # the two direct assignments to the box also sync the button, since a
    # plain .value assignment fires no 'input'
    sync_calls = len(re.findall(r'\bsyncClearPromptButton\(\)', page))
    assert sync_calls >= 4, 'every writer of the box must sync the button'
    # and it stays a distinct button from the full clear
    assert "'clearBtn').addEventListener('click', clearAll)" in page
