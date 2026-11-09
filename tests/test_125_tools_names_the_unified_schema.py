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

"""The tool schemas of `plot_one` and `get_signal` both name the unified
schema: `along` (the axis a quantity runs along) and `indices` (the index
each other axis is pinned at, one entry per nested array of structures).

Pinned against the `TOOLS` the LLM is handed, because a param the schema
does not name is a param the model cannot reach even when the code has no
opinion about where its name sits: the `along`/`indices` pair is the user-
facing half of the shared resolver, and if a tool the user asks for cannot
take it (or one of `plot_one` / `get_signal` can but the other does not),
the two halves stop naming the same element and the bug the resolver
exists for moves.

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


@pytest.mark.parametrize('toolName', ['plot_one', 'get_signal'])
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


def test_the_tools_refuse_time_and_the_unified_schema_together():
    """`time` pins one slice; `along` / `indices` run along an axis. The
    schema is the refusal the tool answers, and the system prompt names it
    for the model, so the loop the user saw does not close on a second ask.
    """
    system = SYSTEM_INSTRUCTIONS
    assert 'along' in system, 'the system prompt does not name `along`'
    assert 'indices' in system, 'the system prompt does not name `indices`'
    # The refusal is named for `plot_one` and for `get_signal` alike, in the
    # prompt and in the tool description.
    for toolName in ('plot_one', 'get_signal'):
        description = next((t.get('function', {}).get('description', '')
                            for t in TOOLS
                            if t.get('function', {}).get('name') == toolName),
                           '')
        assert 'along' in description or 'indices' in description, \
            (toolName, description)
