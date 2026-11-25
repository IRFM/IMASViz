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
"""The tools of one group answer which of them a stray parameter belongs to.

Two things are pinned here, and they are different in kind.

**The grouping is the manual's, and it is a partition.** ``tools.FAMILIES``
copies the group rows of the manual's tool table
(``doc/source/manual/agentics.rst``, "The one core and the one tool set").
A group that drifts from its row -- a tool renamed on one side, a new tool
offered and grouped nowhere, a tool claimed by two groups -- is a table
nobody can read, so the doc itself is parsed and asked. The catalogue of
prompts is the one group the manual documents in its own section rather
than in that table: it is grouped here (its six tools answer each other's
parameters) and owes that row to the pass that redraws the table.

**The grouping answers a question the flat schemas cannot.** The loop
offers 84 tools and their 86 parameter names repeat (``figure_key`` in 18
schemas, ``uri`` in 37, ``along`` in 12), so the likelier mistake is a real
parameter put on the wrong neighbour, not a parameter invented out of
nothing. The refusal that only lists what is *not* there -- what
``test_117_dispatch_refuses_unknown_parameters.py`` pins -- leaves the
model guessing which neighbour wanted it. ``time_index`` on ``plot_one``
is the measured case: ``get_signal`` takes it, and said so.

Nothing here changes what the loop is offered: each tool is still offered
by its own name, and each is still validated against its own schema.
"""

import importlib.util
import os
import re

import pytest

from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.llm_client import LLMResponse
from imasviz.VizAgent.tools import (
    FAMILIES,
    TOOLS,
    familyOf,
    siblingTaking,
    unknownParameterRefusal,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANUAL = os.path.join(REPO_ROOT, 'doc', 'source', 'manual', 'agentics.rst')

TOOL_NAMES = [tool['function']['name'] for tool in TOOLS]


def _manualGroups():
    """The tool table of the manual, as {group label: set of tool names}.

    A row is ``* - the label``, then a cell naming the tools in double
    backticks -- which may wrap over lines (the journals row does) -- then
    a prose cell that is not read here.
    """
    with open(MANUAL, encoding='utf-8') as handle:
        lines = handle.read().splitlines()
    start = None
    for number, line in enumerate(lines):
        if (line.startswith('.. list-table::')
                and number + 4 < len(lines)
                and lines[number + 4].strip() == '* - the group'):
            start = number
            break
    assert start is not None, 'the manual no longer draws its tool table'

    groups = {}
    rows = []
    for line in lines[start + 1:]:
        if line.startswith('..'):
            break  # the next directive: the table is over
        if line.startswith('   * - '):
            rows.append([line[len('   * - '):].strip(), []])
        elif rows and line.startswith('     - '):
            rows[-1][1].append(line[len('     - '):])
        elif rows and rows[-1][1]:
            rows[-1][1][-1] += ' ' + line.strip()
    for label, cells in rows:
        names = _names(cells[0]) if cells else set()
        if names:
            groups[label] = names
    return groups


def _names(cell):
    return set(re.findall(r'``([a-z_]+)``', cell))


# --- the grouping -------------------------------------------------------

def test_the_groups_partition_the_tools_on_offer():
    """Every tool offered is in one group, and in only one. A tool added to
    ``TOOLS`` and grouped nowhere is a tool whose stray parameters answer
    nothing; a tool in two groups is a refusal that can point at either."""
    members = [name for _, group in FAMILIES for name in group]
    assert len(members) == len(set(members)), \
        'a tool is claimed by two groups'
    assert set(members) == set(TOOL_NAMES), \
        ('the groups and the tools on offer are not the same list: %s'
         % ', '.join(sorted(set(members) ^ set(TOOL_NAMES))))
    labels = [label for label, _ in FAMILIES]
    assert len(labels) == len(set(labels)), 'two groups share a label'


def test_the_groups_are_the_manual_s():
    """A group row of the manual and a group of the table say the same
    tools. This is what keeps the table in ``tools.py`` from becoming a
    second, quieter account of the surface."""
    manual = _manualGroups()
    spelled = {label: set(group) for label, group in FAMILIES}
    missing = sorted(set(manual) - set(spelled))
    assert not missing, \
        'the manual groups tools the table does not: %s' % ', '.join(missing)
    for label, names in sorted(manual.items()):
        assert spelled[label] == names, \
            ('the %s group is not what the manual draws: %s'
             % (label, ', '.join(sorted(spelled[label] ^ names))))
    for label, names in sorted(manual.items()):
        unknown = sorted(names - set(TOOL_NAMES))
        assert not unknown, \
            'the manual names tools that are not on offer in %s: %s' \
            % (label, ', '.join(unknown))


def test_the_groups_are_in_the_manual_s_order():
    """The manual introduces its table with "the tools, in the order the
    faces group them". The table keeps that order, so a reader who has the
    page open finds a group where they left it. The catalogue of prompts is
    the one group the page documents in its own section rather than in that
    table, so it is left out of the comparison."""
    manual = _manualGroups()
    spelled = [label for label, _ in FAMILIES if label in manual]
    assert spelled == list(manual), \
        ('the groups are not in the order the manual draws them: %s'
         % ' / '.join(spelled))


# --- what the grouping answers -----------------------------------------

def test_a_parameter_a_neighbour_takes_is_answered_by_naming_it():
    """``columns`` is not a ``plot_one`` argument -- it is what a Table Plot
    View takes. The refusal says both: what plot_one takes, and who takes
    ``columns``."""
    text = unknownParameterRefusal('plot_one', ['columns'])
    assert '"columns" is not a parameter of the plot_one tool' in text
    assert 'along_time' in text, 'the parameters that are stay named'
    assert 'plot_table' in text, \
        'the neighbour that takes the stray must be named'
    assert siblingTaking('plot_one', 'columns') == ['plot_table']


def test_the_measured_confusion_names_the_tool_that_takes_it():
    """``time_index`` on ``plot_one`` is the confusion the 2026-11-07 run
    measured (see test_117's docstring). ``get_signal`` takes it: the
    refusal now says so instead of leaving the model to re-guess."""
    text = unknownParameterRefusal('plot_one', ['time_index'])
    assert 'get_signal' in text


def test_a_parameter_no_neighbour_takes_invents_no_neighbour():
    """A parameter nothing in the group takes is one the model invented.
    Sending it off to a tool that does not take it either is worse than
    saying nothing: the model would answer with a call refused again."""
    text = unknownParameterRefusal('plot_one', ['temperature'])
    assert 'temperature' in text
    for other in ('plot_slice', 'plot_table', 'plot_stacked', 'plot_selection',
                  'get_signal'):
        assert other not in text, \
            'the refusal sent the model to %s, which does not take it' % other


def test_a_tool_that_takes_nothing_says_so():
    """``list_cases`` takes no argument: "it takes " is not an answer, and
    the model needs to hear that no argument is the right one. The
    neighbours of its group that do take the stray are named, because a
    ``uri`` put on ``list_cases`` usually means one of them."""
    text = unknownParameterRefusal('list_cases', ['uri'])
    assert 'takes no parameter at all' in text, text
    assert 'open_case' in text and 'close_case' in text
    assert siblingTaking('list_cases', 'uri') == ['open_case', 'close_case']


def test_a_parameter_the_tool_itself_takes_answers_no_neighbour():
    """Asking why ``get_signal`` takes ``time_index`` answers nothing: the
    advice is for a parameter the called tool does not take."""
    assert siblingTaking('get_signal', 'time_index') == []
    assert familyOf('get_signal') == 'the drawing'


def test_a_name_that_is_not_a_tool_is_answered_as_such():
    assert familyOf('draw_a_curve') is None
    assert siblingTaking('draw_a_curve', 'uri') == []


def test_the_advice_stays_inside_the_group():
    """``show_window`` takes ``key`` while the two tools of the *screen*
    group take ``window`` -- one of the spellings the merge of the windows
    will have to settle. Until it does, a ``window`` put on ``show_window``
    is answered by the parameter that is (``key``) and by nothing else:
    pointing across groups at a tool that raises a window instead of
    showing it is a guess about what the caller meant, and a guess is what
    a refusal exists to avoid."""
    text = unknownParameterRefusal('show_window', ['window'])
    assert 'it takes key' in text
    assert siblingTaking('show_window', 'window') == []
    for other in ('focus_window', 'get_screenshot'):
        assert other not in text, \
            'the advice left the group and reached %s' % other


# --- the loop, end to end ----------------------------------------------

class FakeLLMClient:
    def __init__(self, responses):
        self.responses = list(responses)

    def chat(self, messages, tools=None, **kwargs):
        assert self.responses, 'no more scripted responses'
        return self.responses.pop(0)


class RecordingCore:
    """Answers the calls the scripted turns make, and records them: a call
    refused for its parameters must never reach it."""

    def __init__(self):
        self.calls = []

    def plot_one(self, uri, path, along_time=None, along=None,
                 indices=None, into_figure_key=None, time=None,
                 time_interp=None):
        self.calls.append({'uri': uri, 'path': path})
        return {'figure': 'Plot1', 'drawing': True}

    def list_cases(self):
        self.calls.append({'list_cases': True})
        return [{'uri': 'imas:hdf5?path=/fake'}]


class FakeDispatcher:
    def call(self, function, timeout=300.0):
        return function()


def _oneTurnAgent(core, tool, args):
    llm = FakeLLMClient([
        LLMResponse(content='', tool_calls=[{'name': tool, 'args': args}],
                    finish_reason='tool_calls'),
        LLMResponse(content='refused, then.', tool_calls=None,
                    finish_reason='stop'),
    ])
    lines = []
    errors = []
    agent = AgentLoop(core=core, llm=llm, dispatcher=FakeDispatcher(),
                      main_window=None, api=None)
    agent.transcriptLine.connect(lines.append)
    agent.askFinished.connect(errors.append)
    agent.ask('do it')
    return agent, ' '.join(lines), errors


def test_the_loop_names_the_neighbour_it_refused_a_parameter_for(qapp):
    """``plot_one(columns=3)`` through the loop: the refusal the model reads
    names the stray, what the tool takes, and the neighbour that takes the
    stray. The core is never called."""
    core = RecordingCore()
    agent, transcript, errors = _oneTurnAgent(
        core, 'plot_one',
        {'uri': 'imas:hdf5?path=/fake', 'path': 'equilibrium.f',
         'columns': 3})
    refusal = [ln for ln in transcript.splitlines()
               if 'REFUSAL' in ln and 'plot_one' in ln]
    assert refusal, 'the parameter was not refused: %r' % transcript
    assert 'columns' in refusal[0]
    assert 'along_time' in refusal[0]
    assert 'plot_table' in refusal[0], \
        'the loop must name the tool that does take the parameter'
    assert core.calls == [], 'a refused call must not reach the core'
    assert errors == [None]


def test_a_call_the_core_answers_is_not_touched_by_the_grouping(qapp):
    """The grouping changes a refusal message and nothing else: a call with
    its own parameters still reaches the core and answers its figure."""
    core = RecordingCore()
    agent, transcript, errors = _oneTurnAgent(
        core, 'plot_one',
        {'uri': 'imas:hdf5?path=/fake', 'path': 'equilibrium.f',
         'along_time': 1})
    assert core.calls == [{'uri': 'imas:hdf5?path=/fake',
                           'path': 'equilibrium.f'}]
    assert 'REFUSAL' not in transcript
    assert errors == [None]


# --- the measurement script stays true to the surface ------------------

def test_the_measure_script_counts_what_the_loop_actually_offers():
    """``scripts/tool_schema_size.py`` is the number a proposal is quoted
    against. A script that rots quotes a wrong number with authority, so
    its counts are asked against the live surface."""
    path = os.path.join(REPO_ROOT, 'scripts', 'tool_schema_size.py')
    spec = importlib.util.spec_from_file_location('tool_schema_size', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    measured = module.measure()
    assert measured['tools'] == len(TOOLS)
    assert measured['groups'] == len(FAMILIES)
    assert measured['payloadChars'] > 0
    # The two faces are one surface the manual describes; the loop offers
    # what the MCP service does not, and that gap is a fact the script
    # prints rather than hides.
    assert set(measured['loopOnly']) <= set(TOOL_NAMES)
