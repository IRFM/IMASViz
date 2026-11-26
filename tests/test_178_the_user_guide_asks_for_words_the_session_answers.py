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
"""The user guide asks the reader for words the session actually answers.

``AGENT_HELP.md`` is not a manual page: it is the sheet a user reads to know
**what to type** to the agent, and it answers with the call that words reach.
So its vocabulary is load-bearing in a way a prose page is not -- a reader who
types what the sheet shows gets a refusal, and the refusal is not the sheet's
fault, which is why nothing tells them the sheet is a year old.

The manual's table is already asked against ``tools.FAMILIES`` (``test_174``).
What nothing asked was the sheet, and it drifted to the vocabulary that
preceded the merges: **22** calls spelled with a name the model is no longer
offered -- ``plot_one`` ten times, ``plot_slice`` five, ``load_ids`` three,
and ``open_case``, ``list_idss``, ``search_nodes``, ``focus_window`` once
each. Each of those names is still a **gesture** of the core and still a
legal ``action``/``mode``/``operation`` value; what is gone is the name as
something one **calls**. So the rule the guard asks is narrow and cannot be
met by deleting words: a name that left the wire may be named in prose, but
may not be spelled as a call -- never followed by an argument list.

Two more things the sheet does that rot on their own, both asked here because
both are how a reader checks a claim: a pointer at a test that no longer
exists sends them to nothing, and the pair the drawing takes has to be spelled
as the tool spells it, not only as the gesture behind it does.
"""

import os
import re

from imasviz.VizAgent.tools import FAMILIES, TOOLS

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDE = os.path.join(REPO_ROOT, 'AGENT_HELP.md')
MANUAL = os.path.join(REPO_ROOT, 'doc', 'source', 'manual', 'agentics.rst')
TESTS = os.path.join(REPO_ROOT, 'tests')

# A call, as a reader would type it: a lower-case name and its arguments.
CALL = re.compile(r'\b([a-z][a-z_0-9]{2,})\s*\(')
TEST_POINTER = re.compile(r'\btest_(\d{3})\b')


def _text(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


def _offTheWire():
    """The gestures a group merged under another name.

    Still methods of the core, still legal values of a discriminant -- no
    longer a name on the wire, so no longer a name to CALL."""
    offered = {tool['function']['name'] for tool in TOOLS}
    members = set(name for _label, group, _offers in FAMILIES
                  for name in group)
    return members - offered


def test_the_guide_never_asks_the_reader_to_call_a_name_off_the_wire():
    """A name that left the wire may be named, never called.

    This is the guard that was missing when the merges went in: every one of
    them renamed a CALL, and the sheet kept calling the old name for the
    reader to copy."""
    dead = _offTheWire()
    for path in (GUIDE, MANUAL):
        called = sorted(set(name for name in CALL.findall(_text(path))
                            if name in dead))
        assert not called, \
            ('%s asks the reader to call %d name(s) the faces no longer '
             'offer: %s' % (os.path.relpath(path, REPO_ROOT), len(called),
                            ', '.join(called)))


def test_every_test_the_guide_points_at_is_a_file():
    """The sheet proves its measured claims by naming the test that pins
    them (``test_132``, ``test_134``...). A pointer at a test that was
    renamed or taken away is a claim the reader cannot check, which is
    worse than no claim: it reads as verified."""
    names = os.listdir(TESTS)
    for number in sorted(set(TEST_POINTER.findall(_text(GUIDE)))):
        prefix = 'test_%s_' % number
        assert any(name.startswith(prefix) for name in names), \
            ('the guide points at test_%s, which holds no file' % number)


def test_the_sheet_spells_the_pair_as_the_tool_spells_it():
    """``along`` and ``indices`` are the pair the sheet exists to teach, and
    the drawing answers them under one name with a discriminant. A sheet
    that teaches the pair but never spells the call the reader is offered
    leaves them to guess how the two get there."""
    text = _text(GUIDE)
    for word in ('along', 'indices'):
        assert re.search(r'\b%s\b' % word, text), \
            'the sheet no longer names %s' % word
    drawing = next(offers for label, _members, offers in FAMILIES
                   if label == 'the drawing')
    name, discriminant = drawing[0][0], drawing[0][1]
    assert re.search(r'%s\(\s*%s\s*=' % (name, discriminant), text), \
        ('the sheet never spells the drawing as it is offered: %s(%s=...)'
         % (name, discriminant))
