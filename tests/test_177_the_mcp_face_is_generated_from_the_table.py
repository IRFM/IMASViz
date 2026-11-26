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
"""The MCP face is generated from the table, so it cannot drift from it.

Before T6, ``mcp_server/tools.py`` spelled this vocabulary a second time:
a hundred decorated functions, each with its own signature, its own
docstring, its own wording for every parameter, kept in step with
``imasviz.VizAgent.tools.TOOLS`` by a guard and by somebody remembering.
The two faces were then measured identical in names and parameters --
which is the whole argument for generating one from the other: the copy
answered nothing the table did not already answer. What the pass took out
is the 1 037 lines that spelled it over again -- the file went from 1 185
lines to 360 -- and, with them, the possibility of a second wording.

What is pinned here is that face **on the wire**, not in the source. An
AST read of that file for its tool list is over: it holds no
``def plot(...)`` any more, and a guard that walks a file looking for
declarations that are no longer there passes by saying nothing -- which is
how ``test_176`` lost its two MCP tests and ``test_175`` its one; both are
rewritten alongside this file. So the guard asks ``list_tools()`` what the
endpoint is actually offering: the table's 23 names, each description and
each parameter note the table's own bytes, each discriminant the table's
actions, each ``required`` list the table's, and not one note invented on
this side of the socket.

Asking the SDK rather than the file is also what makes the generation
measurable, because the generation was measured before it was written:
FastMCP builds its schema from a function assembled at run time -- a hand
set ``__signature__``, a ``Literal`` becoming an enum, an
``Annotated[..., Field(description=...)]`` becoming the note -- on this
node's ``mcp`` and ``pydantic`` 2.14.2. A face that silently lost the
notes would read identically in the source and answer differently to a
caller, which is exactly what an AST guard cannot see.

Three things a schema cannot say stay this server's own, and are pinned by
name. The shape of three answers: a top-level list goes back under
``cases`` / ``idss`` / ``matches`` (the SDK would otherwise answer one
content block per element), and one tool answers a picture. The way a call
reaches the core: as the MEMBER its discriminant names, with the word that
member was written against -- ``window`` becomes ``key``, ``path`` becomes
``leaf`` -- and its discriminant left behind. And what this face does
**not** ask: the destructive gate, which belongs to the loop, where a model
decides and a user has to have asked for it (``test_135``).
"""

import ast
import asyncio
import base64
import json
import os

import pytest

from imasviz.VizAgent.tools import (
    TOOLS,
    actionsOf,
    discriminatorOf,
    missingParameterRefusal,
    resolveCall,
)
from mcp_server.tools import buildServer

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MCP_SOURCE = os.path.join(REPO_ROOT, 'mcp_server', 'tools.py')

TABLE = {tool['function']['name']: tool['function'] for tool in TOOLS}

PNG = b'\x89PNG stub'


class StubCore:
    """The gestures the calls below make, under the signature the real core
    answers them with (``core.py`` 459, 488, 577, 607, 1230, 3186, 3581,
    5159, and 5147 for the ``get_screenshot`` alias the table names).

    A stub whose signature is its own would pin the forwarding against a
    fiction: what these tests say is that the core is handed the word ITS
    Python takes, not the word the schema offered, and a ``path=`` reaching
    a method written against ``leaf=`` has to raise here for the guard to
    mean anything. One gesture is deliberately absent -- ``describe_node``
    -- because one call test watches the generator refuse a gesture this
    session has no answer for.
    """

    def __init__(self):
        self.calls = []

    def _seen(self, name, arguments, answer=None):
        self.calls.append((name, arguments))
        return {'called': name} if answer is None else answer

    def list_cases(self):
        return self._seen('list_cases', {},
                          [{'uri': 'imas:hdf5?path=/x/1/0'}])

    def search_nodes(self, uri, query='', ids_name=None, limit=200):
        self._seen('search_nodes', {'uri': uri, 'query': query})
        return [{'path': query}]

    def select_signals(self, uri, paths, additive=True):
        self._seen('select_signals', {'uri': uri, 'paths': list(paths),
                                      'additive': additive})
        return {'selected': len(paths)}

    def plot_slice(self, uri, leaf, time, occurrence=0,
                   interpolation='linear', into_figure_key=None):
        return self._seen('plot_slice', {'leaf': leaf, 'time': time})

    def show_window(self, key):
        return self._seen('show_window', {'key': key})

    def plot_report(self, figure_key, name=None):
        return self._seen('plot_report', {'figure_key': figure_key})

    def get_screenshot(self, window='app'):
        self._seen('get_screenshot', {'window': window})
        return PNG

    def get_logs(self, uri=None, tail=200):
        return self._seen('get_logs', {'uri': uri, 'tail': tail},
                          {'uri': uri, 'tail': tail})


class DirectDispatcher:
    """Runs the gesture on the calling thread.

    Production hands it to the GUI thread, which is the reason a tool body
    here is only allowed to compute; what this file pins is what the
    dispatcher is handed. The thread hop is ``test_101``, which runs the
    real ``GuiDispatcher`` over a socket.
    """

    def call(self, function):
        return function()


@pytest.fixture(scope='module')
def face():
    """One generated server, listed once: the tests below read its answer,
    they do not rebuild it."""
    core = StubCore()
    server = buildServer(core, DirectDispatcher(), name='guard')
    listed = asyncio.run(server.list_tools())
    return {'server': server, 'core': core,
            'listed': {tool.name: tool for tool in listed}}


# --------------------------------------------------------------- helpers

def _schema(face, name):
    """The ``inputSchema`` the endpoint sends for one tool."""
    return face['listed'][name].inputSchema


def _opened(block):
    """A wire block and its ``anyOf`` branches, as one list.

    Pydantic spells a nullable parameter as alternatives; the table spells
    it as a list of type names. Both say the same thing, and reading both
    through one shape is what lets the comparison below be an equality
    rather than a translation table."""
    return [block] + list(block.get('anyOf', []))


def _jsonTypes(block):
    return set(part['type'] for part in _opened(block) if 'type' in part)


def _values(block):
    spelled = []
    for part in _opened(block):
        spelled.extend(part.get('enum', []))
    return spelled


def _answered(face, name, arguments):
    """The content blocks one call answered."""
    return asyncio.run(face['server'].call_tool(name, arguments))


def _firstText(blocks):
    return next(block.text for block in blocks if block.type == 'text')


def _payload(face, name, arguments):
    return json.loads(_firstText(_answered(face, name, arguments)))


def _refusal(face, name, arguments):
    """The words one refused call came back with.

    In process the SDK raises for a refusal; over the wire it answers with
    ``isError`` and the same sentence, which is ``test_101``."""
    try:
        _answered(face, name, arguments)
    except Exception as exc:
        return str(exc)
    raise AssertionError('%s answered a call it should have refused: %s'
                         % (name, arguments))


# ------------------------------------------------- what the face declares

def test_the_face_declares_the_table_and_nothing_else(face):
    """One tool per entry of ``TOOLS``, and no name this file added beside
    it.

    The second direction is the one that used to need remembering: a name
    only one face answers is a client that works from the page and is
    refused from the socket, or the other way round, with the log naming a
    tool nobody was ever offered."""
    assert set(face['listed']) == set(TABLE), \
        ('mcp only: %s; loop only: %s'
         % (sorted(set(face['listed']) - set(TABLE)),
            sorted(set(TABLE) - set(face['listed']))))


def test_every_description_is_the_table_s_verbatim(face):
    """The sentence a caller reads is the sentence the panel's model reads,
    byte for byte -- which is the half the hand-written face kept apart:
    its docstrings were shorter, and shorter because somebody rewrote them.

    Nothing here says the table's prose is right. It says the two faces
    cannot disagree about it, which is what makes the prose budget of
    ``test_176`` a budget for both faces at once."""
    odd = []
    for name, function in TABLE.items():
        sent = face['listed'][name].description
        if sent != function['description']:
            odd.append('%s: %d chars on the wire for %d in the table'
                       % (name, len(sent or ''),
                          len(function['description'])))
    assert not odd, odd


def test_a_parameter_note_on_the_wire_is_the_note_of_the_table(face):
    """The note, not just the name. This is what ``Annotated[type,
    Field(description=...)]`` was bought for: the loop's schema carries a
    sentence per parameter and a hand-written signature had no place for
    one, so a caller over the socket met ``along``, ``indices`` or
    ``figure_key`` with no explanation at all.

    A block the table leaves silent has no note here either. Inventing one
    is the same drift in the other direction: a word explained two ways is
    a word the caller has to disambiguate, and the schema cannot say which
    explanation binds."""
    odd = []
    for name, function in TABLE.items():
        wire = _schema(face, name)['properties']
        for parameter, block in function['parameters']['properties'].items():
            note = block.get('description')
            sent = wire[parameter].get('description')
            if note and sent != note:
                odd.append('%s.%s: %r on the wire for %r in the table'
                           % (name, parameter, sent, note))
            if not note and sent:
                odd.append('%s.%s: a note this face invented: %r'
                           % (name, parameter, sent))
    assert not odd, odd


def test_a_parameter_is_the_type_and_the_requirement_the_table_spells(face):
    """A type, an enum and a required list read off the block, so a word
    that becomes narrower or gains a value on the loop face is on this
    socket the next time the server is built.

    One licence, and it is the signature's: a word a call may leave out
    needs a default, and the value of "nobody answered it" is ``None``, so
    the wire may add a ``null`` branch the block did not spell. Nothing
    else may move -- and a ``default: null`` under a type that refuses null
    is a schema that contradicts itself, which is what pydantic prints
    here without a word of warning."""
    odd = []
    for name, function in TABLE.items():
        schema = function['parameters']
        wire = _schema(face, name)
        assert sorted(wire.get('required', [])) \
            == sorted(schema.get('required', ())), \
            '%s required %s, the table %s' % (
                name, sorted(wire.get('required', [])),
                sorted(schema.get('required', ())))
        for parameter, block in schema['properties'].items():
            onTheWire = wire['properties'][parameter]
            spelled = block['type']
            spelled = set(spelled if isinstance(spelled, list) else [spelled])
            types = _jsonTypes(onTheWire)
            if types not in (spelled, spelled | {'null'}):
                odd.append('%s.%s: %s on the wire for a block spelling %s'
                           % (name, parameter, sorted(types), sorted(spelled)))
            if onTheWire.get('default', True) is None and 'null' not in types:
                odd.append('%s.%s: a null default under %s'
                           % (name, parameter, sorted(types)))
            if 'default' in block \
                    and onTheWire.get('default') != block['default']:
                odd.append('%s.%s: the wire answers %r, the table %r'
                           % (name, parameter, onTheWire.get('default'),
                              block['default']))
            if 'enum' in block \
                    and _values(onTheWire) \
                    != [value for value in block['enum'] if value is not None]:
                odd.append('%s.%s: %s offered for %s'
                           % (name, parameter, _values(onTheWire),
                              block['enum']))
    assert not odd, odd


def test_a_discriminant_offers_the_actions_the_table_resolves(face):
    """The values of a group's enum are the actions ``resolveCall`` knows,
    in the same order -- and a value outside them never reaches a gesture.

    The order is not decoration: an action list and its refusal are read
    together, and a schema that offered an action the table resolves
    nowhere would be a call refused for its own honesty."""
    for name in TABLE:
        discriminant = discriminatorOf(name)
        if discriminant is None:
            continue
        offered = _values(_schema(face, name)['properties'][discriminant])
        assert offered == list(actionsOf(name)), \
            '%s offers %s; the table resolves %s' % (
                name, offered, list(actionsOf(name)))


# -------------------------------------- the answers that are this server's

def test_a_top_level_list_goes_back_under_the_name_the_loop_uses(face):
    """``list_cases`` answers a list, and the SDK would send that as one
    content block per element -- an answer a caller cannot tell from a call
    that failed. So it goes back under the key the in-app answer gives it,
    and the client of the socket and the model of the panel read the same
    shape."""
    assert _payload(face, 'manage_case', {'action': 'list'}) \
        == {'cases': [{'uri': 'imas:hdf5?path=/x/1/0'}]}
    matches = _payload(face, 'inspect_tree', {'action': 'search',
                                              'uri': 'u', 'query': 'f'})
    assert list(matches) == ['matches'], matches


def test_a_picture_comes_back_as_a_picture_naming_what_it_captured(face):
    """One tool answers bytes, and the instruction block tells its caller
    that a screenshot is not something it can read. The line beside the
    picture says which window was captured, because a PNG with no name in
    front of it is a claim about nothing."""
    blocks = _answered(face, 'get_screenshot', {'window': 'app'})
    image = next(block for block in blocks if block.type == 'image')
    assert image.mimeType == 'image/png'
    assert base64.b64decode(image.data) == PNG
    text = _firstText(blocks)
    assert 'app' in text and str(len(PNG)) in text, text


# ---------------------------------- how a call reaches the core, and how

def test_a_group_call_reaches_the_core_as_its_member_with_its_own_word(face):
    """Two renames, both inherited by the merge, both invisible until a
    gesture is handed a word it never took: the schema offers ``path`` for
    the slice draw and the core method is written against ``leaf``; the
    schema offers ``window`` for every window ask and ``show_window`` takes
    ``key``.

    And the discriminant does not travel. ``mode="slice"`` is the group's
    question, answered; a ``mode=`` reaching ``plot_slice`` would be a
    TypeError about an unexpected keyword where a refusal should be."""
    face['core'].calls.clear()
    _answered(face, 'plot', {'mode': 'slice', 'uri': 'u',
                             'path': 'equilibrium.f', 'time': 3.0})
    _answered(face, 'manage_window', {'action': 'show',
                                      'window': 'SlicesPlot1'})
    assert face['core'].calls == [
        ('plot_slice', {'leaf': 'equilibrium.f', 'time': 3.0}),
        ('show_window', {'key': 'SlicesPlot1'})], face['core'].calls


def test_a_word_the_action_does_not_take_is_refused_by_name(face):
    """The group's schema declares what every action takes and requires
    only its discriminant, so ``generate_report(scope="plot", uri=...)``
    is legal against the schema and is not a call: ``uri`` belongs to the
    other two scopes. The action's own row is what tells them apart, and
    the refusal says so.

    This is the case a per-tool signature used to answer for free -- each
    hand-written ``def`` had only its own parameters -- and it is the cost
    of a merged schema, paid back by the same seam the loop walks."""
    face['core'].calls.clear()
    text = _refusal(face, 'generate_report',
                    {'scope': 'plot', 'figure_key': 'Plot1',
                     'uri': 'imas:hdf5?path=/x'})
    assert 'uri' in text, text
    assert 'generate_report' in text, \
        'the refusal must answer in the spelling the caller has: %s' % text
    assert face['core'].calls == [], 'a refused call reached the core'


def test_a_word_the_action_cannot_answer_without_is_named(face):
    """``manage_selection(action="select", uri=...)`` says what to select
    and not what is selected. The group's schema cannot see that hole --
    ``paths`` is a name its other actions take too -- so the answer comes
    from ``missingParameters``, in the same sentence the panel's model
    reads, naming the call to answer with."""
    face['core'].calls.clear()
    text = _refusal(face, 'manage_selection', {'action': 'select', 'uri': 'u'})
    expected = missingParameterRefusal('select_signals', ['paths'])
    assert expected in text, 'the wire refused with other words:\n%s' % text
    assert face['core'].calls == []


def test_a_gesture_this_session_does_not_answer_is_refused_by_name(face):
    """The table can name a gesture the core of this build has no method
    for -- the ``get_screenshot`` alias was exactly that, once, and the
    loop refused calls to a name that was spelled right. This face checks
    it and says which name is missing, rather than answering
    ``AttributeError`` from inside a Qt slot."""
    text = _refusal(face, 'inspect_tree', {'action': 'node', 'uri': 'u'})
    assert 'describe_node' in text and 'not a gesture' in text, text


def test_a_value_outside_the_enum_costs_the_session_nothing(face):
    """A guessed action is answered before the GUI thread is asked, by the
    schema's own enum, with the values to answer with. A merged group put
    its asks behind one name; the enum is what keeps each of them
    correctable, and a value that got through would be a gesture chosen by
    a word nobody wrote."""
    face['core'].calls.clear()
    text = _refusal(face, 'manage_case', {'action': 'nope'})
    for action in ('open', 'list', 'close'):
        assert "'%s'" % action in text, '%s is not named: %s' % (action, text)
    assert face['core'].calls == [], 'a bad action reached the core'


# --------------------------------------------------------- the two sources

def test_the_default_a_schema_declares_is_the_default_the_gesture_answers_with(
        qapp):
    """The signature mirrors the ``default`` the table declares, so a
    caller reads ``occurrence: 0`` or ``tail: 200`` and may leave the word
    out. That is only honest while the two defaults are the same number,
    and the table's is now load-bearing on two faces where it used to be
    prose beside one.

    Asked of the real core class, method by method: the words the table
    declares a default for, against the parameters of the gesture each of
    its actions answers. A renamed word is skipped on purpose -- the schema
    offers ``path``, the gesture takes ``leaf``, and comparing the two
    would be comparing one ask's spelling against another's."""
    import inspect

    import imasviz.VizAgent.core as core_module
    coreClass = core_module.McpGuiCore

    mismatched = []
    for name, function in TABLE.items():
        discriminant = discriminatorOf(name)
        members = [resolveCall(name, {discriminant: action})[0]
                   for action in actionsOf(name)] if discriminant else [name]
        for parameter, block in function['parameters']['properties'].items():
            if 'default' not in block:
                continue
            for member in members:
                method = getattr(coreClass, member, None)
                if method is None:
                    continue
                taken = inspect.signature(method).parameters.get(parameter)
                if taken is not None and taken.default != block['default']:
                    mismatched.append(
                        '%s.%s (%s): the table says %r, the gesture answers '
                        '%r' % (name, parameter, member, block['default'],
                                taken.default))
    assert not mismatched, mismatched


def test_no_tool_is_written_by_hand_on_this_face():
    """The file declares tools; it does not write one.

    Four readings of the source, all asking that the vocabulary keep one
    home: the table is imported, one loop walks it, no function carries a
    decorator, and no function is named after a tool. A hand-written
    ``@server.tool(name='plot_one')`` coming back is how the drift started
    in the first place, and it would be invisible to the behavioural
    guards above -- those read the union of both spellings and would find
    nothing wrong until a client met two names for one gesture."""
    tree = ast.parse(open(MCP_SOURCE, encoding='utf-8').read())

    imported = set(alias.name
                   for node in ast.walk(tree)
                   if isinstance(node, ast.ImportFrom)
                   and node.module == 'imasviz.VizAgent.tools'
                   for alias in node.names)
    assert 'TOOLS' in imported, \
        'the face no longer takes its vocabulary from the table'

    loops = [node for node in ast.walk(tree)
             if isinstance(node, ast.For)
             and isinstance(node.iter, ast.Name) and node.iter.id == 'TOOLS']
    assert loops, 'nothing walks TOOLS: this face is not generated any more'

    decorated = [node.name for node in ast.walk(tree)
                 if isinstance(node, ast.FunctionDef) and node.decorator_list]
    assert not decorated, \
        ('these tools are declared by hand again, beside the generated '
         'ones: %s' % decorated)

    spelled = [node.name for node in ast.walk(tree)
               if isinstance(node, ast.FunctionDef) and node.name in TABLE]
    assert not spelled, \
        ('a tool of the table has a function of its own here, which is a '
         'second answer for one name: %s' % spelled)
