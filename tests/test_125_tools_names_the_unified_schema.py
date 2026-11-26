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

"""The tool schemas of ``plot`` and ``get_signal`` both name the unified
schema: `along` (the axis a quantity runs along) and `indices` (the index
each other axis is pinned at, one entry per nested array of structures).

Pinned against the `TOOLS` the LLM is handed, because a param the schema
does not name is a param the model cannot reach even when the code has no
opinion about where its name sits: the `along`/`indices` pair is the user-
facing half of the shared resolver, and if a tool the user asks for cannot
take it (or one of `plot` / `get_signal` can but the other does not),
the two halves stop naming the same element and the bug the resolver
exists for moves.

The drawing answers one name and a `mode` now, so what is per mode is
written on the parameter that carries it. What the PAIR means is no
longer written where it is typed: T7 gave the tool descriptions a word
budget and lifted the definition into the shared ADDRESSING block of the
instruction (`test_147` keeps that block on both faces). What is pinned
here is the half only the schema can answer -- that a tool the user asks
for DECLARES `along` and `indices`, so the model may type them at all --
and that the definition it reads stands in the one block sent with every
turn rather than in N tool sentences that drift apart.

Both halves are also refused together with `time` (the value the user asked
at, not the value the case holds); the schema keeps that refusal the tool
can still answer.
"""

import pytest

from imasviz.VizAgent.tools import TOOLS, SYSTEM_INSTRUCTIONS


def _schemaOf(name):
    for tool in TOOLS:
        if tool.get('function', {}).get('name') == name:
            return tool.get('function', {}).get('parameters', {})
    raise AssertionError('no tool named %r in TOOLS' % name)


def _declares(toolName, word):
    """The tool's schema names the parameter, which is what says the model
    may type it at all."""
    return word in _schemaOf(toolName).get('properties', {})


@pytest.mark.parametrize('toolName', ['plot', 'get_signal'])
def test_the_tools_both_name_the_unified_schema(toolName):
    schema = _schemaOf(toolName)
    props = schema.get('properties', {})
    # The axis a quantity runs along, and the index each other axis is
    # pinned at, are the two names the user uses and the two the schema
    # has to offer.
    assert 'along' in props, (toolName, sorted(props))
    assert 'indices' in props, (toolName, sorted(props))

    # Both `indices` entries hold an index, spelled as an integer: the
    # values the user names are numbers, not words.
    assert 'integer' in props['indices'].get('additionalProperties', {}).get('type', [])


def test_the_definition_of_the_pair_is_said_once_for_every_tool():
    """`time` pins one slice; `along` / `indices` run along an axis. The
    schema is where a tool says it takes them; the shared block of the
    instruction is where what they MEAN is said -- once, for every tool
    that takes them, instead of once per tool sentence. The 2026-11-24
    rewrite put the half the user actually reaches for
    (`indices={"psi": 50}`) in a tool description; T7 lifted that sentence
    into the block, so this guard follows it to where it now stands. A
    definition asked of a description is a definition rewritten for every
    tool that takes the word: 10 712 characters of parameter notes, with
    `uri` alone spelled seven ways across fourteen tools, is what that
    measured before the block.
    """
    for word in ('along', 'indices', 'time'):
        assert '`%s`:' % word in SYSTEM_INSTRUCTIONS, \
            'the instruction no longer defines `%s`' % word
    assert 'indices={"psi": 50}' in SYSTEM_INSTRUCTIONS, \
        'the half the user reaches for is gone from the instruction'
    # What only the schema can answer stays asked of the schema, for the
    # two tools the field failure came in on.
    for toolName in ('plot', 'get_signal'):
        for word in ('along', 'indices'):
            assert _declares(toolName, word), \
                '%s cannot be typed at %s' % (word, toolName)
