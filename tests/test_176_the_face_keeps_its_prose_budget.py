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
"""The tool face keeps its prose budget, and the shared block its rules.

The loop sends its whole ``TOOLS`` list on **every** turn of an ask, so a
description is paid once per turn, not once per session. Measured on this
tree with ``python3 scripts/tool_schema_size.py``: 23 tools, a 32 120
character payload, of which 8 571 are descriptions (1 457 words) and
17 748 parameter notes. The plumbing (149 characters per tool before a
word of its own) and the parameter blocks did not move during the merge;
the descriptions went from 12 259 to 8 571, and that is the half this
file keeps from coming back.

The budget is one line, and it is asked of the **table**, not of the
sentence: a name gets ``BASE_WORDS`` for the ask it answers and
``WORDS_PER_ACTION`` more for each action it answers, because a group of
asks has to say which ask is which -- that is the only prose a merge
genuinely adds. So ``get_logs``, which answers itself, has 40 words, and
``manage_session``, which answers eight, has 104.

    words <= BASE_WORDS + WORDS_PER_ACTION * len(actionsOf(name))

What does not fit goes in the comment above the entry, which is read by
the person changing the tool and costs the model nothing. That is the
trade the T7 pass made on ten tools, and the facts are still there: the
slice cost of ``manage_idss(action="load")``, the profile names
``equilibrium`` brings back, what a session file holds.

And the second half of the trade: three rules that used to be repeated
inside tool descriptions are said **once**, in the block both faces carry
(``SYSTEM_INSTRUCTIONS`` here, ``INSTRUCTIONS`` in ``mcp_server``). A
rule said by a tool is a rule the other twenty-two do not obey, and a
rule said by the block costs one copy instead of twenty-three. They are
pinned here as present in the block -- which is what test_147 does for
the addressing vocabulary -- and as absent from the descriptions, so a
rewrite cannot quietly move one back out. The destructive rule is asked
of the in-app copy only: the MCP endpoint's caller is the user's own
program, and the ask is that program's (test_135).
"""

from imasviz.VizAgent.tools import (
    SYSTEM_INSTRUCTIONS,
    TOOLS,
    actionsOf,
    discriminatorOf,
)
from mcp_server.tools import INSTRUCTIONS as MCP_INSTRUCTIONS

# The budget, as T7 settled it: one block for the ask, one sentence per
# action the name answers.
BASE_WORDS = 40
WORDS_PER_ACTION = 8

# The three rules that left the descriptions for the shared block. Said
# here in the words both copies carry, so a rewrite that rewords the block
# is named rather than read as a pass.
_ONE_WINDOW = 'ask one, not both'
_PICTURES = 'a screenshot is a picture you cannot read'
_NEVER_PNG = 'never from the png'


def _cap(name):
    """What ``name`` may say, counted off the actions the table spells for
    it. A tool that answers itself gets ``BASE_WORDS`` and nothing more.

    Asked of ``actionsOf`` and not of the schema's own enum on purpose: the
    table is what the loop resolves against and what the next merge will
    change, and the enum is a copy of it -- the copy is pinned in the next
    test, not trusted here."""
    return BASE_WORDS + WORDS_PER_ACTION * len(actionsOf(name))


def _plain(text):
    """Collapsed and with the backticks off: the copies are wrapped for
    reading and mark a parameter name differently (``uri`` in the in-app
    prompt, uri on the MCP page), and what is pinned is a sentence."""
    return ' '.join(text.replace('`', '').split()).lower()


def test_no_description_is_over_its_cap():
    """Twenty-three names, each measured against what its own group asks.
    A description over its cap is not a style complaint: it is the fixed
    cost of every turn of every ask, paid by the user's own inference
    budget, and it is the half of the payload that a merge leaves free to
    grow.

    When one goes over, the fix is the comment above the entry in
    ``imasviz/VizAgent/tools.py``: what the call answers field by field,
    the numbers a caller would want, the refusals it raises -- all of it
    stays, where the person changing the tool reads it and the model
    never pays for it."""
    over = []
    for tool in TOOLS:
        name = tool['function']['name']
        words = len(tool['function']['description'].split())
        cap = _cap(name)
        if words > cap:
            over.append('%s: %d words for a cap of %d' % (name, words, cap))
    assert not over, \
        ('these descriptions are over the T7 budget of %d words plus %d '
         'per action; move what does not fit into the comment above the '
         'entry: %s'
         % (BASE_WORDS, WORDS_PER_ACTION, '; '.join(over)))


def test_the_cap_counts_the_actions_the_model_is_actually_offered():
    """The cap is granted per action, so an action the enum offers and the
    table does not know is a free sentence, and an action the table spells
    and the enum hides is a call the model is never told it may make --
    both are a cap measured against a group that is not the group on the
    wire. The two lists are the same list, in the same order.

    And a name with no discriminant answers itself: no action to tell
    apart, so ``BASE_WORDS`` and nothing added."""
    for tool in TOOLS:
        name = tool['function']['name']
        discriminant = discriminatorOf(name)
        actions = actionsOf(name)
        if discriminant is None:
            assert actions == (), \
                '%s answers no discriminant yet answers %s' % (name, actions)
            assert _cap(name) == BASE_WORDS
            continue
        enum = tool['function']['parameters']['properties'] \
            .get(discriminant, {}).get('enum')
        assert enum is not None, \
            '%s is a group whose %s offers no values to choose from' \
            % (name, discriminant)
        assert list(enum) == list(actions), \
            ('the %s enum answers %s while the table spells %s: the cap '
             'and the refusal would be measured against two different '
             'groups' % (name, list(enum), list(actions)))


# --- the rules the descriptions no longer carry ------------------------

def test_the_in_app_block_says_the_three_shared_rules():
    """One window per ask, a screenshot is not readable, and a destructive
    or shared write is asked for and not taken -- in the block the panel,
    viz_web, viz_cli and viz_gateway all send. The destructive bullet names
    the three spelled calls that erase bookkeeping and the shared scope,
    because the rule is only actionable if the model can see which calls it
    is talking about: `list_windows` there would send it to a name the very
    next call refuses for."""
    text = _plain(SYSTEM_INSTRUCTIONS)
    assert _ONE_WINDOW in text, 'the block lost the one-window rule'
    assert _PICTURES in text and _NEVER_PNG in text, \
        'the block lost the rule about what a screenshot is'
    for spelling in ('manage_window(action="close")',
                     'manage_case(action="close")',
                     'manage_session(action="new")',
                     'scope="shared"'):
        assert spelling in text, \
            'the destructive bullet no longer names %s' % spelling
    assert 'unless the user explicitly asks for it in their prompt' in text, \
        'the destructive bullet lost the condition that makes it a rule'


def test_the_mcp_block_says_the_two_that_apply_to_it():
    """The endpoint's caller is the user's own program: the destructive
    gate belongs to the loop, which is where a model decides (test_135
    says the standalone server maps onto the core directly and the ask is
    that program's), so only the two rules about the model's own reading
    are asked of this copy. They are asked in the same words, because a
    rule that drifts between the faces is a rule a user cannot predict
    from one surface to the other."""
    text = _plain(MCP_INSTRUCTIONS)
    assert _ONE_WINDOW in text, 'the mcp copy lost the one-window rule'
    assert _PICTURES in text and _NEVER_PNG in text, \
        'the mcp copy lost the rule about what a screenshot is'


def test_each_shared_rule_is_said_once_per_copy():
    """Once, not twice: the whole economy of moving a rule into the block
    is that it is paid one time per turn. A rule that appears twice in one
    copy is a rule being rewritten rather than moved, and the second
    wording is the one the model obeys."""
    for label, copy in (('in-app', SYSTEM_INSTRUCTIONS),
                        ('mcp', MCP_INSTRUCTIONS)):
        text = _plain(copy)
        for rule in (_ONE_WINDOW, _PICTURES, _NEVER_PNG):
            assert text.count(rule) == 1, \
                'the %s copy says "%s" %d times' % (label, rule,
                                                    text.count(rule))


def test_no_description_carries_a_shared_rule_back_out():
    """The other half of the trade. A rule put back inside a tool is a
    rule the other tools do not carry -- and on the MCP face, a rule the
    client's own prompt has to re-say. The three phrases below are the
    fingerprints of the moved rules: a description that reads as if it had
    to explain them again is named here, tool by tool."""
    for tool in TOOLS:
        name = tool['function']['name']
        text = _plain(tool['function']['description'])
        for rule in (_ONE_WINDOW, _PICTURES, _NEVER_PNG):
            assert rule not in text, \
                ('%s carries the shared rule "%s" again: it is in the '
                 'block both faces send' % (name, rule))
