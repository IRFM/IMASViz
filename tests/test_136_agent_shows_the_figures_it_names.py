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
"""Showing a figure is the user's command, not the model's standing duty.

The first cut of this direction was what this file used to pin the
other way around: the model focused a figure whenever it drew one or
named one, on the standing rule that a figure named that the user
cannot see is a figure not shown (``focus it, do not only describe it``,
``whenever you draw a figure or name one``, ``a figure you moved is a
figure that stands``). The user's call on it: a show is an explicit
command ("montre-moi Plot1"), and a draw or a mention in the answer is
not one -- the figure is in the *Windows* menu, and the raise and the
size are the user's own gestures there.

So the guard stands as it is now: the instruction the model reads
(``SYSTEM_INSTRUCTIONS``, rewritten on 2026-11-24 with the WINDOWS &
FOCUS rule in its own words) and the tool description it calls on the
strength of the instruction (``focus_window``) both say the show is
the user's command, and refuse the standing-show vocabulary -- and this
file keeps a revert honest the way the other surface contracts do
(``test_120`` pins the occurrence/index/path words, ``test_125`` the
unified schema). There is no behaviour to drive without the local
model that is being asked to change, and the guard is what keeps the
direction.
"""

from imasviz.VizAgent.tools import SYSTEM_INSTRUCTIONS, TOOLS


def _text():
    """The instruction lowercased with line breaks and runs of spaces
    collapsed: a phrase guard must not fail because a wrap split the words
    it pins (the same idiom `test_120` uses)."""
    return ' '.join(SYSTEM_INSTRUCTIONS.split()).lower()


def _focus_description():
    """The `focus_window` tool description, collapsed as `_text` does."""
    description = next((t.get('function', {}).get('description', '')
                        for t in TOOLS
                        if t.get('function', {}).get('name') == 'focus_window'),
                       '')
    return ' '.join(description.split()).lower()


def test_showing_is_the_users_command_in_the_instruction():
    """The direction the user calls: a show is the user's own command
    ("ramène Plot1 devant"), and a draw or a mention in the answer is not
    a reason to raise or size a window -- the instruction says neither
    focus_window nor show_window is called automatically after a plot, and
    only when the user explicitly asks to bring a window to the front."""
    text = _text()
    assert 'do not call `focus_window` or `show_window` ' \
           'automatically after plotting' in text, \
        'the instruction no longer refuses the automatic show after a ' \
        'plot: a draw is the show again'
    assert 'only call them if the user explicitly asks ' \
           'to bring a window to the front' in text, \
        'the instruction lost the one legitimation: the explicit ask of ' \
        'the user'


def test_the_standing_show_vocabulary_is_gone():
    """Every phrase of the previous direction -- the standing duty to
    focus on a draw or a mention, and the "moved figure stands" rule of
    item 9 -- must not be in the instruction the model reads."""
    text = _text()
    assert 'a figure you named that the user does not see ' \
           'is a figure not shown' not in text, \
        'the standing rule is back: a figure the model named must be ' \
        'focused so the user sees it'
    assert 'focus it, do not only describe it' not in text, \
        'the standing remedy is back: the model must focus the figure ' \
        'it named'
    assert 'whenever you draw a figure or name one' not in text, \
        'the standing trigger is back: a draw or a mention is a show'
    assert 'a figure you moved is a figure that stands' not in text, \
        'the item-9 rule is back: a figure the gesture moved must be ' \
        'focused again'
    assert 'it is not an ask to show anything' not in text, \
        'the item-9 refusal is back in the instruction'


def test_focus_window_reads_itself_as_the_users_command():
    """The tool the model calls on the strength of the prompt reads itself
    the same way: the user's "show me this" command, bringing the window
    to the front -- shown when off screen, raised when not -- keeping
    the size it holds unless pixels are named, and refusing the draw and
    the mention as reasons to call it. Without the system prompt and the
    tool description agreeing, one of them would keep the standing-show
    posture and the model would have two of the opposite mind about the
    same call."""
    text = _focus_description()
    assert 'the user\'s "show me this" command' in text, \
        'the focus_window description is not the user\'s command: the ' \
        'standing-show reading is back'
    assert 'keeps the size it holds' in text, \
        'the focus_window description lost the size keep: a call with ' \
        'no pixels resizes the window again'
    assert 'a side left out keeps the size the window holds on that side' \
        in text, \
        'the focus_window description lost the half keep: one named side ' \
        'and one kept side must stand'
    assert 'a draw is not an ask to show it' in text, \
        'the focus_window description lets the model focus on a draw: ' \
        'the standing show is back in the tool it would call'
    assert 'whenever you draw a figure or name one' not in text, \
        'the standing trigger is back in the focus_window description'


def test_focus_window_keeps_its_size_in_its_properties():
    """The `width` and `height` properties say the keep out loud: a side
    left out keeps the size the window holds, not a default of 1280."""
    tool = next((t for t in TOOLS
                 if t.get('function', {}).get('name') == 'focus_window'),
                None)
    assert tool is not None, 'the focus_window tool is gone'
    properties = tool['function']['parameters']['properties']
    for side in ('width', 'height'):
        description = ' '.join(properties[side].get('description', '')
                               .split()).lower()
        assert 'left out, the size the window holds' in description, \
            'the %s property no longer says the keep: a call without it ' \
            'resizes the window on that side again' % side
        assert 'default: 1280' not in description, \
            'the %s property is back to the 1280 default: the no-pixels ' \
            'show resizes the window again' % side
