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

"""The window of a plugin is asked for, not taken.

The report: « charge l'equilibre, trace la pression pour psi=0, 30 60 et
100 sur une nouvelle figure » drew its four curves, and an
Equilibriumcharts window beside them. Nothing in the application opens a
plugin window on a load -- ``manage_idss(action="load")`` runs
``QVizLoadOccurrence`` and no plugin -- so that window was the model
reaching for ``plugin(action="run")`` on an ask that names no plugin. A
plugin entry draws a window of its own, over what the ask was drawing, and
it is the one gesture of the tool set whose whole answer IS a window.

So the gate a close and a shared journal write already wear is extended to
it, and the rule goes into both instruction copies too: the teaching and
the enforcement, as the destructive gestures have them. The gesture the
USER reaches for (``requested_by='user'``, the menu line, the page's
button) owes no word -- the click is the ask, and a user clicking a plugin
line is asking for its window by definition.

The word list is narrower than the closure list on purpose, and that is
the part this file keeps narrow. Two spellings open the gate: the word a
plugin window is asked under in either language, and the exact name of the
plugin **the call itself** addresses. What is deliberately kept out is the
generic noun for what such a window shows -- a "graphique", a "profil", a
"courbe", a "surface". Those are what ``plot`` and
``equilibrium(action="surfaces")`` already answer: a gate that opened on
them would let the reported ask through, which is what the report was. And
the read of what a case offers is never refused -- ``plugin(action="list")``
opens no window and is asked before the ask is settled -- which is why the
table names the run and not the group.

Two vocabularies again, as for the journals: the gate reads the GESTURE
behind the action (``PLUGIN_WINDOW_GESTURES`` names ``run_plugin``), while
every ask and every refusal here is spelled the way the tool set offers it
(``plugin(action="run")``); a refusal naming ``run_plugin`` would send the
model to a name it is refused for asking.

One asymmetry to keep, and it is the one test_176 already records for the
destructive rule: the ENFORCEMENT stands on the loop, where a model decides
and a user is reading the answer. The standalone MCP endpoint maps a call
onto the core directly (test_135), so on that face the rule is carried by
the instructions alone -- which is why the teaching is asked of both copies
and the gate of one.
"""

import pytest

from imasviz.VizAgent import agent as agent_module
from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.tools import SYSTEM_INSTRUCTIONS, TOOLS
from mcp_server.tools import INSTRUCTIONS as MCP_INSTRUCTIONS

# The ask that came back with a window nobody asked for, verbatim.
_REPORTED_ASK = ("charge l'equilibre, trace la pression pour psi=0, 30 60 "
                 "et 100 sur une nouvelle figure")

# The rule, in the words both instruction copies carry. Quote-free on
# purpose: the in-app copy spells a call with double quotes and the MCP
# copy with single ones, and what must not drift is the rule, not its
# markup.
_FIELD_UP = 'the calls that set the field up are never an ask'
_PLUGIN_RUN = 'a plugin window is: never call'
_LOADING = 'loading an ids never asks for a window'


class RecordingPluginCore:
    """The core one plugin ask reaches: the two actions of the group,
    recorded, and nothing else. A refused run must not leave a call
    behind -- the window it would have drawn is the whole complaint -- so
    the test reads the record and sees the gate did what it named."""

    def __init__(self):
        self.calls = []

    def list_plugins(self, uri, ids_name):
        self.calls.append(('list_plugins', {'uri': uri,
                                            'ids_name': ids_name}))
        return {'entries': [{'plugin': 'equilibriumcharts', 'number': 0,
                             'label': 'Equilibrium overview'}]}

    def run_plugin(self, uri, plugin, entry, occurrence=0, ids_name=None,
                   time=None):
        self.calls.append(('run_plugin', {'plugin': plugin, 'entry': entry}))
        return {'ran': True, 'drawn': ['EquiPlotView:1'], 'reused': None}


class FakeDispatcher:
    def call(self, function, timeout=300.0):
        return function()


@pytest.fixture
def loop():
    core = RecordingPluginCore()
    agent = AgentLoop(core=core, llm=object(), dispatcher=FakeDispatcher(),
                      main_window=None, api=None)
    return agent, core


def _run(agent, plugin='equilibriumcharts', entry=0, requested_by='model',
         user_prompt=_REPORTED_ASK):
    """One ``plugin(action="run")`` as the model spells it, on a given ask."""
    return agent._dispatch(
        'plugin',
        {'action': 'run', 'uri': 'imas:hdf5?path=west/3/54924/0',
         'plugin': plugin, 'entry': entry},
        requested_by=requested_by, user_prompt=user_prompt)


# --- the gate ----------------------------------------------------------

def test_a_plugin_window_nobody_asked_is_refused(loop):
    """The reported turn: a model reaching for an entry on an ask that
    names no plugin is refused, the core is never asked, and the refusal
    names the call as the tool set offers it, the plugin it would have
    drawn, that an IDS load opens nothing, and the word that unblocks it."""
    agent, core = loop
    with pytest.raises(ValueError) as exc:
        _run(agent)
    refusal = str(exc.value)
    assert core.calls == [], \
        'a refused plugin run must not reach the core: %r' % core.calls
    assert 'plugin(action="run")' in refusal, \
        ('the refusal names the call it refused in the spelling the tool '
         'set offers it, not the gesture behind it: %r' % refusal)
    assert 'equilibriumcharts' in refusal, \
        'the refusal names the plugin whose window was refused: %r' % refusal
    assert 'loading an ids never opens one' in refusal.lower(), \
        ('the refusal says what the ask did not ask for: a load opens no '
         'plugin window, which is the belief this refusal answers: %r'
         % refusal)
    assert 'plugin' in refusal and 'plugin(action="list")' in refusal, \
        'the refusal names the ask that unblocks it: %r' % refusal


def test_the_reported_ask_is_the_one_this_gate_answers(loop):
    """Non-vacuity: the exact words of the report, and the exact call that
    was made on them, are refused. A gate written against a paraphrase of a
    bug report is a gate nobody can re-run on the report."""
    agent, core = loop
    assert 'equilibre' in _REPORTED_ASK and 'pression' in _REPORTED_ASK \
        and 'plugin' not in _REPORTED_ASK, \
        'the ask of the report names a load and a plot, and no plugin'
    with pytest.raises(ValueError):
        _run(agent, user_prompt=_REPORTED_ASK)
    assert core.calls == [], \
        'the ask of the report must draw no plugin window: %r' % core.calls


def test_a_run_the_user_named_by_the_plugin_it_addresses_runs(loop):
    """The unblock is a name. The ask says the plugin the call addresses,
    with no other word, and the run goes through -- and a name spelled with
    a space answers a name spelled with an underscore, because what the
    gate compares is a name, not its punctuation."""
    agent, core = loop
    _run(agent, user_prompt='lance equilibriumcharts')
    assert core.calls == [('run_plugin', {'plugin': 'equilibriumcharts',
                                          'entry': 0})], \
        'a plugin the user named by name is asked for: %r' % core.calls

    agent._dispatch('plugin', {'action': 'run', 'uri': 'u',
                               'plugin': 'VizProfiles_plugin', 'entry': 0},
                    requested_by='model',
                    user_prompt='ouvre VizProfiles plugin sur le wall')
    assert core.calls[-1][1]['plugin'] == 'VizProfiles_plugin'


def test_an_ask_that_names_another_plugin_does_not_license_this_one(loop):
    """The name matched is the name of the plugin the CALL addresses, not
    any registered name. An ask that names ``VizSpectral`` does not license
    a run of ``equilibriumcharts``: it licenses that other entry, and a gate
    reading the registry would let this one through on the wrong words."""
    agent, core = loop
    with pytest.raises(ValueError):
        _run(agent, user_prompt='ouvre VizSpectral')
    assert core.calls == [], \
        'a name for another plugin is not an ask for this one: %r' % core.calls


def test_the_word_plugin_or_extension_in_either_language_opens_the_gate(loop):
    """The other spelling: the word a plugin window is asked under. Either
    language, and no name needed -- the ask that says "the plugin" without
    naming which is answered by naming the entries back, not refused."""
    agent, core = loop
    for ask in ('lance le plugin des graphiques d\'equilibre',
                "ouvre l'extension qui va avec l'equilibre",
                'run the plugin that draws the equilibrium charts'):
        _run(agent, user_prompt=ask)
        assert core.calls, 'an ask naming a plugin is asked for: %r' % ask


def test_generic_words_for_what_a_window_shows_do_not_open_the_gate(loop):
    """The narrowness, pinned. A "graphique", a "profil", a "courbe" or a
    "surface" is what ``plot`` and ``equilibrium(action="surfaces")``
    already answer: opening the gate on those words would let the reported
    ask through, and the rule the user asked for is the one that keeps the
    generic nouns out."""
    agent, core = loop
    for ask in ('ouvre les surfaces de flux',
                'affiche les profils de l\'equilibre',
                'trace un graphique de la pression',
                'ouvre la fenetre des evenements'):
        with pytest.raises(ValueError):
            _run(agent, user_prompt=ask)
        assert not core.calls, \
            'a generic noun for a window is not an ask for a plugin: %r' % ask


def test_listing_the_plugins_of_a_case_is_never_refused(loop):
    """The gate is keyed on the run, not on the group. ``list_plugins``
    opens no window and is asked before the ask is settled -- refusing it on
    the same words would leave the model no way to name the entries back to
    the user, which is what the refusal asks it to do."""
    agent, core = loop
    agent._dispatch('plugin', {'action': 'list',
                               'uri': 'imas:hdf5?path=west/3/54924/0',
                               'ids_name': 'equilibrium'},
                    requested_by='model', user_prompt=_REPORTED_ASK)
    assert core.calls == [('list_plugins',
                           {'uri': 'imas:hdf5?path=west/3/54924/0',
                            'ids_name': 'equilibrium'})], \
        'the read of what a case offers runs on an ask that names no ' \
        'plugin: %r' % core.calls


def test_a_run_the_user_reached_for_owes_no_word(loop):
    """The gesture the user's own hand reaches (``requested_by='user'``) is
    the ask: a plugin line clicked in a menu, or a run the page was asked to
    replay. The same core, the same arguments, no refusal."""
    agent, core = loop
    _run(agent, requested_by='user')
    assert core.calls and core.calls[0][0] == 'run_plugin', \
        'a run the user reached for runs: %r' % core.calls


def test_the_gate_names_the_run_and_not_the_group():
    """The table the gate reads, in the shape it must keep: the one gesture
    that draws a window, and not its group's read. A rewrite that put
    ``list_plugins`` in the table would refuse the only call that can name
    the entries back."""
    assert agent_module.PLUGIN_WINDOW_GESTURES == ('run_plugin',)
    assert 'list_plugins' not in agent_module.PLUGIN_WINDOW_GESTURES


def test_the_ask_words_are_the_two_of_either_language():
    """The word table itself, asked of the function that reads it -- the
    same shape as ``_userAskedForAClosure`` and ``_userAskedForAPublish``.
    A word the model recites is not the ask; the ask the user gave in other
    words is one this gate refuses by design, and the refusal says so."""
    fn = agent_module._userAskedForAPluginWindow
    assert fn('lance le plugin', 'equilibriumcharts')
    assert fn('Open the extension for this case', 'equilibriumcharts')
    assert fn('equilibriumcharts', 'equilibriumcharts')
    # Nothing asked for a window, whatever else the ask drew.
    assert not fn(_REPORTED_ASK, 'equilibriumcharts')
    assert not fn('charge l\'equilibre', 'VizProfiles_plugin')
    assert not fn('', 'equilibriumcharts')
    assert not fn('', '')


# --- both instruction copies carry the rule ----------------------------

def _plain(text):
    """Collapsed and with the backticks off, as test_147 and test_176 read
    the two copies: they are wrapped for reading and mark a call
    differently, and what is pinned is a sentence."""
    return ' '.join(text.replace('`', '').split()).lower()


def test_both_copies_tell_the_model_which_calls_are_never_an_ask():
    """The teaching half of the fix, on both faces: the prerequisite calls
    are free, and a plugin window is not. A rule enforced only in the loop
    is a rule the model meets as a refusal; said in the block it reads, it
    is a call it never makes."""
    for label, copy in (('in-app', SYSTEM_INSTRUCTIONS),
                        ('mcp', MCP_INSTRUCTIONS)):
        text = _plain(copy)
        for phrase in (_FIELD_UP, _PLUGIN_RUN, _LOADING):
            assert phrase in text, \
                'the %s copy lost the plugin rule: %s' % (label, phrase)
        for call in ('manage_case(action="open")', 'manage_idss(action="load")',
                     'plugin(action="list")'):
            assert call.replace('"', "'") in text.lower() or call in text, \
                ('the %s copy no longer names %s among the calls that are '
                 'never an ask' % (label, call))


def test_the_plugin_rule_is_said_once_per_copy():
    """Once, not twice -- the economy test_176 asks of the other three
    shared rules. A rule said twice in one copy is a rule being rewritten
    rather than moved, and the second wording is the one the model obeys."""
    for label, copy in (('in-app', SYSTEM_INSTRUCTIONS),
                        ('mcp', MCP_INSTRUCTIONS)):
        text = _plain(copy)
        for phrase in (_FIELD_UP, _PLUGIN_RUN, _LOADING):
            assert text.count(phrase) == 1, \
                'the %s copy says "%s" %d times' % (label, phrase,
                                                    text.count(phrase))


def test_no_tool_description_carries_the_plugin_rule_back_out():
    """The other half of the trade test_176 pins: a rule the block says is
    a rule no tool carries. The ``plugin`` entry in particular must not
    start explaining when it may be run -- the run's own sentence is about
    what its actions answer, and the ask is the block's."""
    for tool in TOOLS:
        name = tool['function']['name']
        text = _plain(tool['function']['description'])
        for phrase in (_FIELD_UP, _PLUGIN_RUN, _LOADING):
            assert phrase not in text, \
                ('%s carries the plugin rule "%s" again: it is in the '
                 'block both faces send' % (name, phrase))
