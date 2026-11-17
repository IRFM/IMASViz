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
"""The two instruction copies both forbid claiming work that did not run.

The in-app agent (``imasviz.VizAgent.tools``'s ``SYSTEM_INSTRUCTIONS``,
read by the panel, viz_web and viz_cli) and the external MCP clients
(``mcp_server.tools``'s ``INSTRUCTIONS``, read by whatever model the
``python -m mcp_server`` session serves) are two hand-kept copies of the
working method: the in-app agent is policed by the loop's guards as well,
but the external one is policed by the prompt alone -- a copy that loses
the rule is a surface that claims without being checked.

The rule the field failure needed, spelled so both copies can share it:

* the state of a figure is what the calls of the exchange made, and a
  read it answered -- not what was said of it; a curve said added, a
  transform said applied, an axis said moved stands only if the call
  that did it succeeded naming that figure, or a read of the figure
  (``curve_stats``, ``export_curve``) answered that state;
* a refused call changed nothing: the answer is the refusal it named,
  with the reason it gave -- not the state it would have left;
* a call that did not run, or had not returned when the answer was
  given, is not a success: read the figure with ``curve_stats`` before
  saying what it holds, or say it stands as you found it.

The test pins the shared sentences in both copies: edit one and forget
the other, and this file is the one that says so -- the same shape
``test_120`` gives the words it pins.
"""

from imasviz.VizAgent.tools import SYSTEM_INSTRUCTIONS
from mcp_server.tools import INSTRUCTIONS


def _text(instructions):
    """Lowercased with line breaks and space runs collapsed: the copies are
    wrapped for readability, and a phrase guard must not fail because a
    line break split the words it pins."""
    return ' '.join(instructions.split()).lower()


# The sentences both copies must carry, byte for byte: this is what makes
# one an edit of the other.
SHARED_RULE = (
    'a curve you say was added, a transform you say was applied, '
    'an axis you say moved',
    'stands only if the call that did it succeeded naming that figure',
    'or a read of the figure (curve_stats, export_curve) '
    'answered that state',
    'a refused call changed nothing',
    'the answer is the refusal it named, with the reason it gave',
    'not the state it would have left',
    'a call that did not run, or that had not returned '
    'when you answered, is not a success',
    'read the figure with curve_stats before saying what it holds',
    'or say it stands as you found it',
)


def test_both_copies_carry_the_grounding_rule():
    """Every shared sentence of the rule stands in both copies: an in-app
    agent that reads the rule and an MCP client that does not (or the
    reverse) is the drift the field failure is made of."""
    texts = [_text(SYSTEM_INSTRUCTIONS), _text(INSTRUCTIONS)]
    for text in texts:
        for phrase in SHARED_RULE:
            assert phrase in text, \
                'missing from one copy: %r' % phrase


def test_the_in_app_rule_speaks_of_the_exchange():
    """The in-app copy says *this exchange* -- one ask, one re-anchor
    budget -- where the MCP copy says *this session*, because the one it
    polices owns the history across the calls of a conversation. The two
    words apart is the point, and it is the one thing the shared sentences
    above cannot carry."""
    assert 'the calls of this exchange made' in _text(SYSTEM_INSTRUCTIONS)
    assert 'the calls of this session made' in _text(INSTRUCTIONS)
