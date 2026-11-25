# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C
# open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted
# upon downloading the software and/or exercising any of the rights granted
# under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""A merged group answers one name, and its actions say which tool runs.

``tools.FAMILIES`` groups the vocabulary (``test_174``). This file pins the
seam that lets a group be offered under **one** name without losing what the
session is made of:

    a call reaches the core, the guards and the loop's own account as its
    MEMBER, never as its group.

The three reports are the case that pays for it. They are one tool now,
``generate_report(scope=...)``, and the loop still has to know that a
``scope="plot"`` call wrote a file -- because the guard that refuses an
answer standing on a report nobody wrote (``test_143``) keys on
``reports_written``, filled from the report gestures. A loop that read the
call as ``generate_report`` would fill nothing and would refuse an honest
answer about a file that stands on disk; a loop that let the group name
reach the core would be dispatching a name the core has no method for.

Both halves are pinned here, and so is what makes the seam safe to keep:

* the actions of an offer cover its members once each, and no member of a
  merged group is offered any more -- the coup is clean, and a member
  spelled out is refused by naming the call that took its place;
* the discriminant of a group is a parameter NO member of that group takes.
  ``add_note(scope, ...)`` already answers ``scope``, so the journals group
  can only be merged under ``action``; a group merged under a word two of
  its own tools take is one word answering two questions, and the model
  cannot be told which is which;
* an action's own parameters are still what its call is measured against:
  the offered schema can only declare what every action needs, so without
  that row ``generate_report(uri)`` reaches Python as a TypeError about a
  positional argument instead of a refusal naming what is missing;
* prose that INSTRUCTS a call names only names the model is offered. The
  two vocabularies are real, and a re-anchor that says ``plot_report(...)``
  after the merge tells the model to make a call it will be refused for.
"""

import importlib.util
import os
import re

import pytest

from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.llm_client import LLMResponse
from imasviz.VizAgent.tools import (
    ACTION_PARAMETERS,
    FAMILIES,
    TOOLS,
    TOOL_PARAMETERS,
    argumentsForMember,
    callSpelling,
    callSpellings,
    discriminatorOf,
    membersOf,
    missingParameterRefusal,
    missingParameters,
    offeredNames,
    resolveCall,
    unknownParameters,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL_NAMES = [tool['function']['name'] for tool in TOOLS]


def _discriminatedOffers():
    """Every offer the table spells with a discriminant, merged or still
    planned: (name, discriminant, actions, the members they answer)."""
    out = []
    for label, _members, offers in FAMILIES:
        for name, discriminant, actions in offers or ():
            if discriminant is not None:
                out.append((name, discriminant,
                            tuple(action for action, _ in actions),
                            tuple(member for _action, member in actions)))
    return out


def _mergedOffers():
    """The offers that ARE merged today: the name is on the wire, so the
    members it answers are off it. A group the table plans to merge and the
    loop still offers member by one is not a merge yet, and pinning it as
    one would refuse tomorrow's work rather than today's mistake."""
    return [one for one in _discriminatedOffers() if one[0] in TOOL_NAMES]


# --- the table, and what is on the wire --------------------------------

def test_a_merged_group_offers_its_name_and_no_longer_its_members():
    """The coup is clean: the group's name is on the wire, the members it
    merged are not. Two names for one gesture is the state where a model
    learns one spelling from a transcript and another from the schema, and
    the log ends up with both."""
    merged = _mergedOffers()
    assert merged, 'the merge machinery is pinned here, so it must be used'
    for name, _discriminant, _actions, members in merged:
        assert name in TOOL_NAMES, '%s is not offered' % name
        for member in members:
            assert member not in TOOL_NAMES, \
                '%s is merged under %s and still offered on its own' \
                % (member, name)


def test_the_offers_are_a_partition_of_the_vocabulary():
    """Every name the loop is offered is one of the table's offers, and
    every tool of the vocabulary is answered by exactly one offer -- as
    itself, or as the action of a merged name.

    A tool no offer answers is a gesture the core can run and the model is
    never offered; an offer answering a tool twice is one name with two
    meanings, which is what the discriminant exists to prevent."""
    answered = {}
    for label, _members, offers in FAMILIES:
        for name, discriminant, actions in (offers
                                            or [(n, None, ())
                                                for n in _members]):
            for member in ([m for _a, m in actions] or [name]):
                answered.setdefault(member, []).append((label, name))
    for member, answers in answered.items():
        assert len(answers) == 1, \
            '%s is answered by %s' % (member, answers)
    assert set(answered) == set(name for _l, group, _o in FAMILIES
                                for name in group), \
        'a tool of the vocabulary is answered by no offer'
    spelled = set()
    for label, _members, offers in FAMILIES:
        for name, _discriminant, _actions in (offers or [(n, None, ())
                                                         for n in _members]):
            spelled.add(name)
    assert spelled == set(offeredNames())
    # A group that is not merged yet is still offered member by member, so
    # the wire list is not the offer list -- but every name on it is a tool
    # the table answers, under one offer and one only.
    unspelled = sorted(set(TOOL_NAMES) - spelled)
    assert not unspelled or all(name in answered for name in unspelled), \
        ('the loop offers names the table answers nowhere: %s'
         % ', '.join(unspelled))


def test_the_discriminant_of_a_group_is_not_a_parameter_of_its_members():
    """One word, one question. ``add_note`` takes a ``scope`` (personal or
    shared journal), so the journals group is merged under ``action``: a
    group whose discriminant a member already takes is a call where the
    same word says two things, and no answer can tell the model which one
    it read."""
    for name, discriminant, _actions, _members in _discriminatedOffers():
        assert discriminatorOf(name) == discriminant
        for member in membersOf(_labelOf(name)):
            taken = set(TOOL_PARAMETERS.get(member, {})
                        .get('properties', {}))
            assert discriminant not in taken, \
                ('%s is merged under "%s", which the %s tool already takes'
                 % (name, discriminant, member))


def _labelOf(offerName):
    for label, _members, offers in FAMILIES:
        if any(offer[0] == offerName for offer in offers or ()):
            return label
    raise KeyError(offerName)


# --- the seam: resolveCall ---------------------------------------------

def test_a_group_call_reaches_the_core_as_its_member():
    """``generate_report(scope="plot", figure_key="Plot1")`` is a
    ``plot_report(figure_key="Plot1", name=None)`` call, and the
    discriminant does not travel with it: the core method takes the
    parameters of the gesture it answers, not the ones of the name the
    model typed."""
    member, args = resolveCall(
        'generate_report',
        {'scope': 'plot', 'figure_key': 'Plot1', 'name': 'flux'})
    assert member == 'plot_report'
    assert args == {'figure_key': 'Plot1', 'name': 'flux'}
    for other, expected in (({'scope': 'case_loaded', 'uri': 'imas:hdf5'},
                             'case_report'),
                            ({'scope': 'case_ids', 'uri': 'imas:hdf5'},
                             'case_ids_report')):
        assert resolveCall('generate_report', other)[0] == expected


def test_a_merged_group_may_ask_its_own_word_for_a_parameter():
    """``plot(mode="slice", path=...)`` reaches ``plot_slice`` as
    ``leaf=...``. A group that answers one name must name one idea with one
    word, and the gesture behind that name was written against another: the
    drawing's "single" mode asks for a ``path`` and its "slice" mode asked
    for a ``leaf``, two words for the same leaf in one schema -- the
    confusion the merge exists to remove.

    The rename happens once, on the way in, AFTER the parameter check and
    before the call. Ask it the other way round and a refusal names a
    parameter the model was never told it may type.
    """
    member, args = resolveCall('plot', {'mode': 'slice', 'uri': 'imas:hdf5',
                                        'path': 'equilibrium.f', 'time': 3.0})
    assert member == 'plot_slice'
    assert unknownParameters(member, args) == [], \
        'the check is asked with the spelling the model typed'
    assert argumentsForMember(member, args) == {
        'uri': 'imas:hdf5', 'time': 3.0, 'leaf': 'equilibrium.f'}, \
        'the gesture is handed the names its own Python takes'

    # And what it answers back is the offered word, never the spelled one.
    text = missingParameterRefusal(
        member, missingParameters(member, {'uri': 'imas:hdf5', 'time': 3.0}))
    assert 'path' in text and 'leaf' not in text, text

    # One way only: the schema offers one word for the leaf.
    offered = {tool['function']['name']:
               tool['function']['parameters']['properties']
               for tool in TOOLS}
    assert 'leaf' not in offered['plot'], \
        'the drawing offer gives two words for one leaf again'


def test_resolve_call_touches_nothing_it_is_handed():
    """The seam runs twice on one call -- ``resolveCall`` for the dispatch,
    ``gestureOf`` for the turn's account of what it did. A resolver that
    popped the discriminant out of the caller's dictionary would answer the
    second pass with a different gesture than the first, and the guard
    would be asked about a call that never happened."""
    args = {'scope': 'plot', 'figure_key': 'Plot1'}
    before = dict(args)
    resolveCall('generate_report', args)
    assert args == before


def test_an_action_that_is_not_one_of_the_group_is_refused_by_name():
    """A model that guesses an action reads the ones that exist. A refusal
    that only says "invalid value" leaves it guessing again, and every
    guess is a turn of the twelve the loop is allowed."""
    for bad in ('report', 'html', ''):
        with pytest.raises(ValueError) as raised:
            resolveCall('generate_report', {'scope': bad})
        text = str(raised.value)
        assert 'scope' in text, 'the refusal must name the parameter'
        for action in ('"plot"', '"case_loaded"', '"case_ids"'):
            assert action in text, '%s is not among the named actions' % action


def test_an_action_without_its_discriminant_is_refused_as_incomplete():
    """``generate_report(figure_key="Plot1")`` is a call that says what to
    report and not which report: refused with the actions named, not run on
    a default nobody chose."""
    with pytest.raises(ValueError) as raised:
        resolveCall('generate_report', {'figure_key': 'Plot1'})
    text = str(raised.value)
    assert 'scope' in text
    assert '"case_ids"' in text


def test_a_member_of_a_merged_group_is_refused_and_names_the_call():
    """Old spelling, new answer. The name may still be in a prompt the user
    saved, a journal line, or the model's memory of an earlier session; the
    refusal is the way back to the one that works, spelled as the schema
    offers it."""
    with pytest.raises(ValueError) as raised:
        resolveCall('plot_report', {'figure_key': 'Plot1'})
    text = str(raised.value)
    assert 'plot_report' in text
    assert 'generate_report' in text, 'the call that took its place is named'
    assert 'scope="plot"' in text


def test_a_name_that_is_neither_a_tool_nor_a_group_answers_itself():
    """The seam must not become the place that decides an unknown name is a
    gesture: the loop refuses it by name, in its own words, and a resolver
    that rewrote it would hide the reason."""
    member, args = resolveCall('draw_a_curve', {'path': 'x'})
    assert member == 'draw_a_curve'
    assert args == {'path': 'x'}


# --- an action is still measured against its own parameters ------------

def test_an_action_takes_the_parameters_its_call_has_to_give():
    """The offered schema can only declare what every action needs, so the
    row of the action is what says that ``scope="plot"`` without a
    ``figure_key`` is an incomplete call. Without it, Python's TypeError
    about a missing positional argument is the answer the model reads."""
    assert missingParameters('plot_report', {'name': 'x'}) == ['figure_key']
    assert missingParameters('case_report', {'uri': 'imas:hdf5'}) == []
    text = missingParameterRefusal('plot_report', ['figure_key'])
    assert 'figure_key' in text
    assert 'generate_report' in text, \
        'the refusal spells the call the model can actually make'
    assert 'scope="plot"' in text


def test_a_stray_parameter_of_a_group_call_is_the_action_that_takes_it():
    """``uri`` is a legal name for ``generate_report`` and a stray for the
    ``plot`` action: the group's schema cannot tell them apart, the
    action's row can."""
    assert unknownParameters('plot_report', {'figure_key': 'P',
                                             'uri': 'imas:hdf5'}) == ['uri']
    assert unknownParameters('case_report', {'uri': 'imas:hdf5'}) == []


def test_every_merged_action_has_a_row_and_the_row_is_in_the_offered_schema():
    """A row naming a parameter the group's schema does not declare is a
    call the model is never told it may make; an action with no row is a
    call measured against nothing. Both are refused here, because both are
    invisible until a model trips on them."""
    for name, discriminant, _actions, members in _mergedOffers():
        schema = TOOL_PARAMETERS[name]
        declared = set(schema.get('properties', {}))
        assert discriminant in declared and discriminant in \
            schema.get('required', [])
        for member in members:
            row = ACTION_PARAMETERS.get(member)
            assert row is not None, \
                '%s is merged and has no parameter row' % member
            extra = set(row[0]) - declared
            assert not extra, \
                ('%s takes %s, which %s does not declare'
                 % (member, ', '.join(sorted(extra)), name))


# --- what the loop hands the guards, and what it says out loud ---------

class FakeDispatcher:
    def call(self, function, timeout=300.0):
        return function()


class RecordingCore:
    """The three reports of the core, under their own names. What a report
    answers is a ``saved_to``, because that is the field the loop keeps to
    ground an answer about a report."""

    def __init__(self):
        self.calls = []

    def plot_report(self, figure_key, name=None):
        self.calls.append(('plot_report', figure_key, name))
        return {'saved_to': '/tmp/flux.html', 'traces': 3}

    def case_report(self, uri, name=None):
        self.calls.append(('case_report', uri, name))
        return {'saved_to': '/tmp/case.html', 'curves': 7}

    def case_ids_report(self, uri, name=None):
        self.calls.append(('case_ids_report', uri, name))
        return {'saved_to': '/tmp/ids.html', 'idss': 4}


def _oneTurn(core, tool, args, answer='Le rapport est dans flux.html.',
             mode='hide'):
    class ScriptedLLM:
        def __init__(self):
            self.turns = [
                LLMResponse(content='', tool_calls=[{'name': tool,
                                                     'args': args}],
                            finish_reason='tool_calls'),
                LLMResponse(content=answer, tool_calls=None,
                            finish_reason='stop'),
            ]

        def chat(self, messages, tools=None, **kwargs):
            assert self.turns, 'no more scripted responses'
            return self.turns.pop(0)

    agent = AgentLoop(core=core, llm=ScriptedLLM(),
                      dispatcher=FakeDispatcher(),
                      main_window=None, api=None)
    agent.tools_mode = mode
    lines = []
    agent.transcriptLine.connect(lines.append)
    errors = []
    agent.askFinished.connect(errors.append)
    agent.ask('un rapport')
    return ' '.join(lines), errors


def test_a_group_call_grounds_an_answer_about_the_report_it_wrote(qapp):
    """The whole point of the seam, measured on the guard that would
    otherwise break. The model calls ``generate_report(scope="plot")``, the
    core writes a file, the answer names it -- and the turn must stand,
    because the loop recorded a report gesture. A loop keying its account
    on the typed name would record nothing and refuse the honest answer."""
    core = RecordingCore()
    transcript, errors = _oneTurn(
        core, 'generate_report',
        {'scope': 'plot', 'figure_key': 'Plot1'})
    assert core.calls == [('plot_report', 'Plot1', None)]
    assert errors == [None], \
        'a report the session wrote must not read as a fabrication: %s' \
        % transcript
    assert 'REFUSAL' not in transcript


def test_the_transcript_keeps_the_spelling_the_model_typed(qapp):
    """A transcript line is a string the model reads back on the next turn,
    and the loop's account of the turn wears the OFFERED spelling -- the
    member name lives where the guards and the core are asked, not in front
    of a model. A line saying ``case_ids_report: saved to ...`` would teach
    a name the very next call is refused for: the two vocabularies are real,
    and only one of them is in front of the model."""
    core = RecordingCore()
    transcript, _errors = _oneTurn(
        core, 'generate_report', {'scope': 'case_ids', 'uri': 'imas:hdf5'},
        mode='verbose')
    assert 'generate_report' in transcript, \
        'the transcript names what was called: %s' % transcript
    assert 'case_ids_report' not in transcript, \
        'the transcript taught the model a name it is never offered: %s' \
        % transcript


def test_the_parameter_refusal_of_a_group_call_is_the_action_s(qapp):
    """A call refused for its parameters is refused in the spelling the
    model typed, and answers with what the action takes -- not with a
    Python traceback and not with a call the model was never offered."""
    core = RecordingCore()
    transcript, errors = _oneTurn(
        core, 'generate_report', {'scope': 'plot'})
    assert core.calls == [], 'a refused call must not reach the core'
    assert 'REFUSAL' in transcript
    assert 'figure_key' in transcript
    assert errors == [None]


def test_a_refused_action_is_named_and_costs_the_core_nothing(qapp):
    """The action refusal goes through the loop like every other refusal:
    named in the transcript, the turn continues, the core is not called."""
    core = RecordingCore()
    transcript, errors = _oneTurn(
        core, 'generate_report', {'scope': 'global'})
    assert core.calls == []
    assert 'scope' in transcript and 'case_ids' in transcript
    assert errors == [None]


# --- prose that instructs a call names only what is offered ------------

def test_the_spelling_of_a_call_is_the_one_the_model_may_type():
    """The loop's re-anchor text tells the model what to answer with. Spelled
    by hand, it is the sentence that rots on the day a group is merged: the
    model obeys, is refused for a name it was never offered, and reads a
    refusal for its own honesty. So the spelling comes from the table, and
    no name it pronounces is one that left the wire."""
    for label, _members, _offers in FAMILIES:
        spelled = callSpellings(label)
        # The names being CALLED, not every word of the spelling: an action
        # value like "plot" is a word the vocabulary holds too, and it is
        # not a call.
        for head in re.findall(r'([a-z_]+)\(', spelled):
            assert head in TOOL_NAMES, \
                ('the %s instruction calls %s, which is not offered: %s'
                 % (label, head, spelled))
    assert callSpelling('plot_report') == \
        'generate_report(scope="plot", figure_key)'
    assert callSpelling('case_report') == \
        'generate_report(scope="case_loaded", uri)'


def test_a_merged_member_is_still_vocabulary_but_never_a_spelling():
    """The three old report names survive as VOCABULARY -- the stop-list of
    the fabrication guard, the journal's account of what a turn did -- and
    as nothing a model is asked to type."""
    for member in ('plot_report', 'case_report', 'case_ids_report'):
        assert member not in TOOL_NAMES
        assert member not in callSpelling(member), \
            'the spelling of a merged member names itself, not its group'


def test_the_mcp_face_answers_the_same_name(qapp):
    """The MCP endpoint is a second face of the same vocabulary, and it is
    written by hand: a group merged on one face and not the other is a
    client that works from the page and refuses from the endpoint. The two
    faces are not identical lists -- the loop offers the prompt catalogue
    and the endpoint does not -- but a merged name has to be on both."""
    path = os.path.join(REPO_ROOT, 'scripts', 'tool_schema_size.py')
    spec = importlib.util.spec_from_file_location('tool_schema_size', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    declared = {tool['name'] for tool in module._mcpFace(
        os.path.join(REPO_ROOT, 'mcp_server', 'tools.py'))}
    for name, _discriminant, _actions, members in _mergedOffers():
        assert name in declared, '%s is merged but not declared by mcp_server' % name
        for member in members:
            assert member not in declared, \
                '%s still answers its own name on the MCP face' % member
