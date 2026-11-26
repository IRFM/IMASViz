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

The 2026-11-24 rewrite dropped the shared sentence for sentence and
spelled the rule in the in-app copy's own words -- NO HALLUCINATION
(only the facts a tool returned in this session), NO FAKE ACTIONS
(no plotted curve, written report or saved note unless the tool
returned ``error: null`` in this turn) and the refusal reported with
its exact reason -- so this file pins each copy in the words IT
carries: the in-app rule in its strict-form words, the MCP rule in the
shared sentences it still carries. What must never leave either copy
is the direction: a claim of work stands only on the call that made
it, a refusal is reported with its reason, and nothing is invented.

The prose budget of T7 makes the two copies the place where the shared
vocabulary is said: a tool description is now measured in words, so
what every tool would otherwise repeat -- what ``uri``, ``path``,
``indices``, ``along``, ``time``, ``figure_key`` mean, that a group's
discriminant is never guessed, that a refusal is an answer -- is said
once, in a block both copies carry. That trade only pays while the
block stands on both faces, which the last test of this file is.
"""

from imasviz.VizAgent.tools import SYSTEM_INSTRUCTIONS
from mcp_server.tools import INSTRUCTIONS


def _text(instructions):
    """Lowercased with line breaks and space runs collapsed: the copies are
    wrapped for readability, and a phrase guard must not fail because a
    line break split the words it pins."""
    return ' '.join(instructions.split()).lower()


def test_the_in_app_copy_carries_the_grounding_rule():
    """The in-app copy, in its own strict words: nothing invented, only the
    facts a tool returned in this session; no action said done unless the
    tool returned without an error; a refusal reported with its exact
    reason."""
    text = _text(SYSTEM_INSTRUCTIONS)
    assert 'never invent ids names, paths, numbers, ' \
           'figure keys, or file paths' in text, \
        'the in-app copy lost the no-invention rule'
    assert 'only state facts returned by a tool in this session' in text, \
        'the in-app copy lost the grounding of every fact on a tool call'
    assert 'never say you plotted a curve, wrote a report, or saved a note' \
        in text, \
        'the in-app copy lost the no-fake-actions rule'
    assert ('unless the corresponding tool returned `error: null` '
            'in this turn' in text), \
        'the in-app copy lost the one legitimation of a claim: ' \
        'the call that returned without an error'
    assert 'report the exact refusal reason' in text, \
        'the in-app copy lost the refusal-with-reason rule'


def test_the_mcp_copy_carries_the_grounding_rule():
    """The MCP copy, in the shared sentences it still carries: the state of
    a figure is what the calls made and the reads answered -- not what
    was said of it; a refused call changed nothing, and the answer is
    the refusal with its reason; a call that had not returned is not
    a success."""
    text = _text(INSTRUCTIONS)
    assert 'a curve you say was added, a transform you say was applied, ' \
           'an axis you say moved' in text, \
        'the mcp copy lost the work-claim rule'
    assert 'stands only if the call that did it succeeded naming that figure' \
        in text, \
        'the mcp copy lost the grounding of a claim on the call'
    assert 'a refused call changed nothing' in text, \
        'the mcp copy lost the refused-call rule'
    assert 'the answer is the refusal it named, with the reason it gave' \
        in text, \
        'the mcp copy lost the refusal-with-reason rule'
    assert ('a call that did not run, or that had not returned '
            'when you answered, is not a success' in text), \
        'the mcp copy lost the not-returned-is-not-a-success rule'


def test_the_refusal_is_an_answer_in_both_copies():
    """The one rule both copies must keep in whatever words they carry:
    a refusal is not a failure, it is an answer with the reason the
    application names -- the in-app copy says "report the exact refusal
    reason", the MCP copy says the refusal IS an answer with the
    reason."""
    in_app = _text(SYSTEM_INSTRUCTIONS)
    mcp = _text(INSTRUCTIONS)
    assert 'report the exact refusal reason' in in_app
    assert 'it is an answer, with the reason' in mcp


# The words every call is answered with. They are defined ONCE, in the
# block both copies carry, so that a tool's own sentence no longer has to
# re-say them: measured before this block, the parameter notes alone cost
# 10 712 characters, and `uri` by itself was spelled seven different ways
# across fourteen tools.
_ADDRESSING_WORDS = ('uri', 'ids_name', 'occurrence', 'path', 'indices',
                     'along', 'time', 'figure_key', 'window')

# The two directions of that block, in words both copies carry identically.
_ADDRESSING_RULES = (
    'a call that leaves it out is refused, never run on a guess',
    'a refusal is an answer: report its reason, then answer again in the '
    'spelling that refusal names',
)


def _plain(instructions):
    """Collapsed like `_text`, with the in-app copy's backticks off: the
    two copies mark a parameter name differently -- `uri` there, uri on
    the MCP page -- and the shape this asks is the definition, not the
    markup."""
    return ' '.join(instructions.replace('`', '').split()).lower()


def test_both_copies_define_the_words_a_call_is_answered_with():
    """Each word of the shared vocabulary is defined, in both copies. This
    is what lets a tool description be short: the tool no longer carries
    the definition, so a copy that loses the block loses the meaning of
    every parameter that word names, on every face at once."""
    for label, copy in (('in-app', SYSTEM_INSTRUCTIONS),
                        ('mcp', INSTRUCTIONS)):
        plain = _plain(copy)
        missing = [word for word in _ADDRESSING_WORDS
                   if ('%s:' % word) not in plain]
        assert not missing, \
            'the %s copy no longer defines %s' % (label, ', '.join(missing))
        for rule in _ADDRESSING_RULES:
            assert rule in _text(copy), \
                'the %s copy lost the addressing rule: %s' % (label, rule)
