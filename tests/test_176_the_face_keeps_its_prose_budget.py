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
tree with ``python3 scripts/tool_schema_size.py``: 23 tools, a 30 064
character payload, of which 8 571 are descriptions (1 457 words) and
15 692 parameter blocks -- 7 997 characters / 1 399 words of that is the
notes themselves. The plumbing (149 characters per tool before a
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

The budget is asked of the table, and since T6 the table is what **both**
faces send: the endpoint builds its tool list by walking ``TOOLS``, so the
sentence a client over the socket reads is the same bytes the panel's model
reads -- ``test_177`` pins that note by note, on ``list_tools()`` rather
than on a file. The endpoint used to carry a prose of its own: 23
docstrings, 25 078 characters before T7 and 8 619 after, paid on every
``tools/list`` round-trip and kept in step with the table by a guard that
could only compare two wordings it could both read. One cap measured on
the table is therefore a cap measured on two faces, and there is no second
wording left to measure.

What does not fit goes in the comment above the entry, which is read by
the person changing the tool and costs the model nothing. That is the
trade the T7 pass made on twenty tools, and the facts are still there:
the slice cost of ``manage_idss(action="load")``, the profile names
``equilibrium`` brings back, what a session file holds.

The notes on the **parameters** pay a budget of their own, and it is
degressive because the wire format has no reference: a word several tools
take is sent once per tool that takes it, so ``SHARED_WORD_CAP`` is 15
(``uri`` alone is paid fourteen times), and a word one tool takes may
afford its concrete example, so ``OWN_WORD_CAP`` is 25. A word several
tools take has **one** wording, spelled once in ``SHARED_NOTES`` and
referenced by the schemas that take it: the saving is in the source only
-- the payload still carries a copy per tool -- so what that table buys
is the consistency the guards below pin, and a second wording of ``uri``
is a word the model learns twice. The table is exactly the vocabulary of
the block's ADDRESSING section, so a shared word is answered up there as
well; a word whose meaning moves with the tool that takes it (``path``,
``name``, ``dd_version``, or a discriminant such as ``mode``) is not in
it and stays spelled where it is used.

And what a note no longer says is what the call already **enforces**:
which action takes which word, and what a call requires, is answered by
the ``ACTION_PARAMETERS`` rows through ``missingParameters`` and
``unknownParameters``, both refusals naming the action, the word and the
call to answer with. Three notes were dropped outright on that ground
(``plot``'s ``mode``, ``transform_curve``'s and ``configure_axes``'
``operation`` -- the enum and the description spell them already) and 37
blocks now carry none. Prose that recites an enforced rule is paid every
turn and answers nothing the refusal did not already answer.

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
    SHARED_NOTES,
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

# The budget for the note on a parameter, as T7-bis settled it. The
# format has no reference, so a word several tools take is sent once per
# tool that takes it -- ``uri`` is paid fourteen times a turn -- and a
# long shared note is fourteen long notes. A word one tool takes costs
# one copy, so it may afford the example that settles its spelling.
SHARED_WORD_CAP = 15
OWN_WORD_CAP = 25


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


# The endpoint's prose IS the table's: test_177 pins, on list_tools(), that
# the schema it sends carries these very descriptions and these very notes.
# A cap measured here is therefore measured for both faces at once, and a
# second wording is no longer something this file could read even if it
# wanted to compare one.

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


# --- what a parameter note may say ------------------------------------

def _notesByParameter():
    """Every parameter note the loop sends, under its parameter name, as
    ``{name: [(tool, noteOrNone), ...]}`` -- one entry per schema that
    takes the word, which is one payment per turn.

    A block with no note is listed and is not a gap: a word the
    ADDRESSING block of the instruction already answers needs nothing
    beside it (``mode`` of ``plot``, the ``operation`` of the two curve
    tools went that way). Silence is legal; a second wording is not."""
    notes = {}
    for tool in TOOLS:
        name = tool['function']['name']
        for parameter, block in \
                tool['function']['parameters'].get('properties', {}).items():
            notes.setdefault(parameter, []).append(
                (name, block.get('description')))
    return notes


def _addressing():
    """The ADDRESSING section of the in-app block -- the vocabulary the
    loop teaches once instead of by twenty-three schemas. The shared
    notes are supposed to be that vocabulary's spelling, so this is the
    half of the table they are checked against."""
    text = SYSTEM_INSTRUCTIONS
    start = text.index('### ADDRESSING')
    return text[start:text.index('### STRICT RULES')]


def test_a_parameter_note_pays_its_word_cap():
    """A note is fixed cost, and how much of it depends on how many
    schemas carry the word: the wire has no reference, so ``uri`` --
    taken by fourteen tools -- is fourteen notes, while ``ip_path`` is
    one. Hence the degressive cap: ``SHARED_WORD_CAP`` for a word
    several tools take, ``OWN_WORD_CAP`` for a word one tool takes, which
    is what lets the physics parameters keep their concrete spelling.

    What goes over is shortened, not moved to the comment: unlike a
    description, a parameter has no place beside it the model reads. The
    facts that do not fit belong in the comment **above the tool**, which
    is where several of them already are."""
    over = []
    for parameter, taken in _notesByParameter().items():
        cap = SHARED_WORD_CAP if len(taken) > 1 else OWN_WORD_CAP
        for note in {note for _name, note in taken if note}:
            words = len(note.split())
            if words > cap:
                over.append('%s: %d words for a cap of %d, taken by %d'
                            % (parameter, words, cap, len(taken)))
    assert not over, \
        ('these notes are over the parameter budget of %d words shared / '
         '%d of one tool: %s' % (SHARED_WORD_CAP, OWN_WORD_CAP,
                                 '; '.join(sorted(over))))


def test_a_shared_word_is_spelled_once_or_not_at_all():
    """A word several tools take has ONE wording, in ``SHARED_NOTES``,
    and a schema that takes it either references that table or carries no
    note. A second wording is what the table exists to refuse: a model
    that meets ``occurrence`` phrased three ways has three things to
    learn, and a call refused on a spelling the schema did not use is a
    refusal it cannot answer.

    A drifted note is not cosmetic either: the drifted copy is the one
    the cap above counts, and the table's wording is the one every other
    tool pays."""
    notes = _notesByParameter()
    for parameter, wording in SHARED_NOTES.items():
        taken = notes.get(parameter)
        assert taken is not None, \
            ('SHARED_NOTES spells %s while no schema takes that word any '
             'more: the table is the list of shared words, not a museum'
             % parameter)
        odd = [name for name, note in taken if note not in (None, wording)]
        assert not odd, \
            ('%s is phrased elsewhere than SHARED_NOTES by %s: one word, '
             'one wording' % (parameter, ', '.join(odd)))


def test_a_shared_word_is_a_word_several_tools_take():
    """The table buys one thing -- a wording written once in the source
    for several schemas -- so a word only one tool takes does not belong
    in it: it adds a level of indirection between the tool and its own
    note, and the next reader of that tool has to look elsewhere for a
    wording used once.

    This is also what keeps the table small enough to read as the
    vocabulary it claims to be."""
    notes = _notesByParameter()
    lonely = sorted(word for word in SHARED_NOTES
                    if len(notes.get(word, [])) < 2)
    assert not lonely, \
        ('these words are taken by one tool, so they are not shared and '
         'their note belongs in that schema: %s' % ', '.join(lonely))


def test_the_instruction_answers_every_shared_word():
    """The table is exactly the vocabulary of the ADDRESSING block: a
    word is shared because the block already teaches what it addresses,
    and the note is its spelling at the parameter level. A word that
    enters the table without being answered up there is a private
    definition smuggled into a shared name -- the model reads the block,
    not a note it meets fourteen times.

    Pinned the other way by test_147, which asks that the block teaches
    the addressing vocabulary; this one asks that the notes do not
    contradict it."""
    block = _addressing()
    untaught = sorted(word for word in SHARED_NOTES
                      if '`%s`' % word not in block)
    assert not untaught, \
        ('these shared words are not answered by the ADDRESSING block, so '
         'they are not shared vocabulary: %s' % ', '.join(untaught))

