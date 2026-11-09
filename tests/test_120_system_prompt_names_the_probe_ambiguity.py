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
"""The system prompt keeps an occurrence apart from an element of an array
of structures, and the probe ambiguity stays named instead of guessed.

What this file answers: the in-app agent was asked what the magnetics IDS
of WEST 54924 holds and answered ``bpol_probe (5 occurrences : 0 à 4)`` --
five, where the case holds **130** `bpol_probe` **elements** (T38), and it
later drew that many. The number did not come from a tool: it came from the
system instructions themselves, which carried ``five bpol_probe
occurrences ([0] to [4])``, and it called the members of an AOS
*occurrences*, which is not what an occurrence is in this application: an
**occurrence** is a version of an IDS the case holds
(``list_idss`` / ``load_ids(occurrence=…)``), while a member of an array
of structures (``magnetics.bpol_probe[3]``) is an **element** -- one probe,
and the count of them is what ``search_nodes`` and ``list_quantities``
answer of the case, never a number the prompt recalls.

The instruction the in-app agent reads therefore says, in words:

* the two words, kept apart: an occurrence is a version of one IDS the
  case holds; an element is one member of an array of structures, and it
  is not an occurrence -- the magnetics bpol-probes stay the standing
  example, spelled as a member index;
* a count the agent gives back is a count a tool answered in this
  conversation, not one the prompt carries -- and no number may sit
  before ``bpol_probe`` in the prompt (the shape that came in as ``five
  bpol_probe``);
* a loose ordinal over one array of structures is an ambiguity, not a
  fact: name the options found and ask which one means, instead of
  choosing one by feel -- a probe picked at random is a wrong curve
  presented as the right one.

Pinning the prompt text is the shape the surface contracts use elsewhere
(``test_116`` pins the tool names, this one pins these words), because
there is no behaviour to drive without the local model that is being asked
to change.
"""

import re

import pytest

from imasviz.VizAgent.tools import SYSTEM_INSTRUCTIONS


def _text():
    """The instruction, lowercased with its line breaks and runs of spaces
    collapsed: the prompt is wrapped for readability, and a phrase guard must
    not fail because a line break split the words it pins."""
    return ' '.join(SYSTEM_INSTRUCTIONS.split()).lower()


def test_the_prompt_keeps_occurrence_apart_from_element():
    """The two words the model mixes are defined, in the direction of the
    application: an occurrence is the IDS version the case holds; a member
    of an array of structures is an element, and an element is not an
    occurrence."""
    text = _text()
    assert 'an occurrence is a version of one ids the case holds' in text
    assert ('an element is one member of an array of structures, '
            'and it is not an occurrence' in text)


def test_the_prompt_keeps_the_standing_example_without_a_count():
    """The bpol probes of magnetics stay the standing example of the
    ambiguity -- so a reader meets it in concrete terms -- but the prompt
    spells one of them as an element index and carries **no** number of
    them: a count before the name is the shape of the wrong ``five
    bpol_probe`` that came back as ``5 occurrences`` on screen."""
    text = _text()
    assert 'bpol_probe' in text
    assert 'magnetics' in text
    assert 'magnetics.bpol_probe[3]' in text
    # No numeral -- digit or small word -- sitting before the name.
    assert not re.search(r'\b\d+\s+bpol_probe\b', text)
    assert not re.search(
        r'\b(?:two|three|four|five|six|seven|eight|nine|ten)\s+bpol_probe\b',
        text)


def test_the_prompt_anchors_counts_to_tools():
    """The counts an answer carries come from the tools of the
    conversation -- search_nodes names the leaves, list_quantities says how
    many elements of their array the case holds -- and the prompt says it
    does not carry a count itself."""
    text = _text()
    assert 'search_nodes' in text
    assert 'list_quantities' in text
    assert 'how many elements of their array the case holds' in text
    assert 'not one this prompt carries' in text


def test_the_prompt_keeps_the_ordinal_guardrail():
    """The ambiguity stays a question to the user, not a pick: a loose
    ordinal over one array of structures is named as an ambiguity, and the
    rule ends asking which one means instead of choosing one by feel."""
    text = _text()
    assert 'an ambiguity, not a fact' in text
    assert 'name the options found and ask which one means' in text
    assert 'instead of choosing one by feel' in text
    assert ('a probe picked at random is a wrong curve '
            'presented as the right one' in text)
