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
"""The system prompt names the probe-occurrence ambiguity instead of guessing.

On WEST 54924 the ``magnetics`` IDS holds five ``bpol_probe`` occurrences
(``[0]`` to ``[4]``); asked for "sonde 2", the agent picked occurrence
``[2]`` by feel -- defensible, but not forced, and the follow-up showed it
would rather lose the work than admit it had chosen. The instruction the
in-app agent and the MCP surface share must say, in words, that a loose
ordinal over an array-of-structures is an ambiguity to name and ask
about, not a fact to resolve by picking. This file pins that sentence:

* several occurrences of one array-of-structures (the bpol probes of
  magnetics are the standing example);
* that a loose ordinal is an ambiguity, not a fact -- occurrence 2 and the
  first probe are different leaves;
* that the answer names the options found and asks which occurrence means,
  instead of choosing one by feel.

Pinning the prompt text is the shape the surface contracts use elsewhere
(``test_116`` pins the tool names, this one pins the guardrail words),
because there is no behaviour to drive without the local model that is
being asked to change.
"""

import pytest

from imasviz.VizAgent.tools import SYSTEM_INSTRUCTIONS


def _text():
    """The instruction, lowercased with its line breaks and runs of spaces
    collapsed: the prompt is wrapped for readability, and a phrase guard must
    not fail because a line break split the words it pins."""
    return ' '.join(SYSTEM_INSTRUCTIONS.split()).lower()


def test_the_prompt_names_the_array_of_structures_ambiguity():
    """The instruction is present, and it is the one that says the ordinal
    over several occurrences is an ambiguity rather than a fact."""
    text = _text()
    assert 'several occurrences of one array-of-structures' in text
    assert 'ambiguity, not a fact' in text


def test_the_prompt_points_at_the_standing_example():
    """The magnetics bpol-probes are the standing example the rule leans on,
    so a reader meets the ambiguity in concrete terms, not in the abstract."""
    text = _text()
    assert 'bpol_probe' in text
    assert 'magnetics' in text


def test_the_prompt_says_ask_which_occurrence_rather_than_guess():
    """The rule ends in a question to the user, not a call one way or the
    other: name the options found, ask which occurrence means, and do not
    choose by feel -- a picked-at-random probe is a wrong curve presented
    as the right one."""
    text = _text()
    assert 'ask which occurrence' in text
    assert 'instead of choosing one by feel' in text


def test_the_prompt_names_the_tool_that_lists_the_options():
    """The options the agent is told to name come from a call, not from
    memory: search_nodes and list_idss are where the case tells its
    occurrences, and both are names the loop already knows."""
    text = _text()
    assert 'search_nodes' in text
    assert 'list_idss' in text
