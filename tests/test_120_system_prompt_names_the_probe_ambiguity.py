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
"""The system prompt keeps an occurrence, an index and a path apart, and
the probe ambiguity stays a question to the user, not a pick.

The 2026-11-24 rewrite of the instruction keeps the field rules in their
own words:

* the three words, kept apart: an ``occurrence`` is a version of an IDS
  (passed to ``load_ids``); ``indices`` is the 0-based index of a tensor
  dimension or nested array; a ``path`` is a specific member of a
  structure array;
* a family member is picked by its OWN path, never by ``indices`` -- the
  prompt says "never put ``flux_loop`` in ``indices``", the same
  direction the old prompt spelled with ``magnetics.bpol_probe[3]``;
* the answer stands on the tools: "only state facts returned by a tool
  in this session" -- a count or a name the prompt itself carries is the
  shape the field failure came in as (``five bpol_probe occurrences
  ([0] to [4])`` in the old prompt, ``bpol_probe (5 occurrences : 0 à 4)``
  on screen where the case holds 130 elements);
* a loose ordinal over one array of structures is an ambiguity, not a
  fact: "sonde 2" names the options ``inspect_tree(action="search")``
  found and asks the user to choose, instead of picking one by feel.

Pinning the prompt text is the shape the surface contracts use elsewhere
(``test_116`` pins the tool names, this one pins these words), because
there is no behaviour to drive without the local model that is being
asked to change.
"""

import re

from imasviz.VizAgent.tools import SYSTEM_INSTRUCTIONS


def _text():
    """The instruction, lowercased with its line breaks and runs of spaces
    collapsed: the prompt is wrapped for readability, and a phrase guard must
    not fail because a line break split the words it pins."""
    return ' '.join(SYSTEM_INSTRUCTIONS.split()).lower()


def test_the_prompt_keeps_the_three_words_apart():
    """The three words the model mixes are each defined, in the direction
    of the application: an occurrence is a version of an IDS passed to
    load_ids; indices is the 0-based index of a tensor dimension or nested
    array; a path is a specific member of a structure array."""
    text = _text()
    assert '`occurrence`: version of an ids (passed to `load_ids`)' in text
    assert '0-based index of a tensor dimension or nested array' in text
    assert 'specific member of a structure array' in text


def test_a_family_member_is_its_own_path_not_an_index():
    """The standing direction of the old ``bpol_probe[3]`` example, now
    spelled on the flux loops: the second member is the other call's PATH
    (``into_figure_key``), and the family name never sits in
    ``indices``."""
    text = _text()
    assert 'magnetics.flux_loop[2].flux.data' in text
    assert 'call `plot(mode="single")` twice using `into_figure_key`' in text
    assert 'never put `flux_loop` in `indices`' in text
    # No number of a family member as a count: an index in brackets is an
    # index, a word or digit before the name is the count the old prompt
    # carried ("five bpol_probe"), and that shape is what came back as
    # "5 occurrences" on screen.
    assert not re.search(r'\b\d+\s+(bpol_probe|flux_loop)\b', text)
    assert not re.search(
        r'\b(?:two|three|four|five|six|seven|eight|nine|ten)\s+'
        r'(bpol_probe|flux_loop)\b', text)


def test_the_prompt_anchors_every_fact_to_the_tools():
    """A name, a count or a value an answer carries stands only on a tool
    call of the session -- the one sentence the rewritten rule keeps of the
    old count-to-tool anchoring."""
    text = _text()
    assert 'only state facts returned by a tool in this session' in text
    assert 'never invent ids names, paths, numbers, figure keys, or file paths' \
        in text


def test_the_prompt_keeps_the_probe_ambiguity_a_question():
    """The ambiguity stays a question to the user, not a pick: "sonde 2"
    with several probes standing is named as an ambiguity, and the rule
    ends asking the user to choose among the exact paths
    ``inspect_tree(action="search")`` found."""
    text = _text()
    assert '"sonde 2" when multiple probes exist' in text
    assert ('list the exact paths found by '
            '`inspect_tree(action="search")`') in text
    assert 'ask the user to choose' in text
