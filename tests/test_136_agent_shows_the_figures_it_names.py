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
"""The agent shows the figures it names, not the ones it only describes.

The field report, word for word: "une certaine paresse à me montrer des
plots pourtant existants; si je lui dis 'je ne vois pas cette figure',
l'agent fait un effort et finit par faire une capture qui fonctionne."

The machinery is not the cause. A web turn captures exactly the figures
it drew plus the windows it focused
(`viz_web/web_session.py::_finishTurn`, `saveShots`), and `focus_window`
IS a capture ask there -- a focus of a figure "is a capture ask too, not
a by-product" (`web_session.py:216`), pinned by `test_127`/`test_128`.
So the figure reaches the screen the moment the model calls
`focus_window` on it. What was missing was the model never calling it
unless the phrasing sounded like an ask: the system prompt carried
"it is yours to call **only when the user asks** for a capture ... this
turn reaches it again **only when the ask names it**"
(`imasviz/VizAgent/tools.py`, item 5) -- a standing instruction to stay
quiet about a figure until the user chases it. "je ne vois pas" read as
a chase; a bare question about state read as silence.

The fix is in the prompt the model reads, and this file pins it the way
the other surface contracts do (`test_120` pins the probe-ambiguity
words, `test_125` the unified schema): the lazy "only when the user
asks" trigger is gone, and the standing rule is now that a figure the
model named but the user cannot see is a figure not shown -- so it is
focused, not merely described. There is no behaviour to drive without
the local model that is being asked to change, and the guard is what
keeps a revert honest.
"""

import pytest

from imasviz.VizAgent.tools import SYSTEM_INSTRUCTIONS, TOOLS


def _text():
    """The instruction lowercased with line breaks and runs of spaces
    collapsed: a phrase guard must not fail because a wrap split the words
    it pins (the same idiom `test_120` uses)."""
    return ' '.join(SYSTEM_INSTRUCTIONS.split()).lower()


def test_the_lazy_only_when_asked_trigger_is_gone():
    """The clause that made the model stay quiet about figures until the
    user chased it -- "only when the user asks for a capture" and the
    twin "reaches it again only when the ask names it" -- must not be in
    the instruction the model reads."""
    text = _text()
    assert 'only when the user asks for a capture' not in text, \
        'the lazy "only when the user asks" trigger is back: the model ' \
        'stays quiet about a figure until the user chases it'
    assert 'reaches it again only when the ask names it' not in text, \
        'the "only when the ask names it" trigger is back: a figure an ' \
        'earlier turn drew is never shown again until the user chases it'


def test_the_prompt_makes_showing_a_standing_rule():
    """The rule is now the direction it was missing: whenever the model
    draws a figure or names one the session holds, it focuses it so the
    user sees it -- a figure named that the user does not see is a figure
    not shown."""
    text = _text()
    assert 'focus_window' in text, \
        'the instruction no longer names focus_window: the show gesture ' \
        'is unreachable'
    assert 'a figure you named that the user does not see ' \
           'is a figure not shown' in text, \
        'the standing rule is missing: a figure the model named but the ' \
        'user cannot see must be a figure not shown, to be focused'
    assert 'focus it, do not only describe it' in text, \
        'the remedy is missing: the model must focus the figure, not ' \
        'only describe it'


def test_focus_window_reads_itself_as_the_show_gesture():
    """The tool the model calls on the strength of the prompt reads itself
    proactively: it is the "show it" gesture, called whenever a figure is
    drawn or named -- not only the preparation of an explicit screenshot.
    Without the system prompt and the tool description agreeing, one of
    them would keep the old "only before a screenshot" posture and the
    model would have two of the opposite mind about the same call."""
    description = next((t.get('function', {}).get('description', '')
                        for t in TOOLS
                        if t.get('function', {}).get('name') == 'focus_window'),
                       '')
    text = ' '.join(description.split()).lower()
    assert 'so the user sees it' in text, \
        'the focus_window description is not the show gesture: it does ' \
        'not say it exists so the user sees the figure'
    assert 'whenever you draw a figure or name one' in text, \
        'the focus_window description does not name the standing trigger: ' \
        'call it whenever a figure is drawn or named'
