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
written on the parameter that carries it: the pair is asked of the whole
entry -- its description and the descriptions of its parameters -- not of
the top sentence alone, which cannot carry five modes' prose.

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


def _proseOf(name):
    """Everything the model reads about one tool: its sentence plus the
    sentence of each of its parameters."""
    for tool in TOOLS:
        function = tool.get('function', {})
        if function.get('name') == name:
            parts = [function.get('description', '')]
            parts += [one.get('description', '')
                      for one in function.get('parameters', {})
                      .get('properties', {}).values()]
            return '\n'.join(parts)
    raise AssertionError('no tool named %r in TOOLS' % name)


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


def test_the_tools_refuse_time_and_the_unified_schema_together():
    """`time` pins one slice; `along` / `indices` run along an axis. The
    schema is the refusal the tool answers. The 2026-11-24 rewrite of the
    in-app prompt names the half the user actually reaches for
    (`indices={"psi": 50}`), and the tool entry of `plot` and of
    `get_signal` name both halves for the model -- `along` and `indices`
    alike -- so the loop the user saw does not close on a second ask.
    """
    system = SYSTEM_INSTRUCTIONS
    assert 'indices' in system, 'the system prompt does not name `indices`'
    # The unified schema is named for `plot` and for `get_signal`
    # alike, in the prose the model reads at the call.
    for toolName in ('plot', 'get_signal'):
        prose = _proseOf(toolName)
        assert 'along' in prose and 'indices' in prose, \
            (toolName, prose)
