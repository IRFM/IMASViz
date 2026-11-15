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

"""The edit of a journal note: the note keeps its id, the fields move.

The missing surface the user named: the notes the journals list cannot
be changed once written — a page with Read, Delete and Add, and nothing
that changes the line in place, which left the user deleting and
re-writing a note to correct one word, and paying a new id to the
other writers that read the deleted line under its old one. The edit
is the answer: the note keeps the file name it reads under (a new line
would be an ``add_note``), the fields the caller names take the place
of the ones it held (a field left out keeps it, an empty one clears
it), and the two a note does not go without — the author and the body
— are the named refusal when the edit empties either, leaving the
note on disk untouched.

Everything is driven against a private HOME (``tmp_path``), the same
shape ``test_131`` and ``test_133`` hold: the store is one read of the
disk it is under, and the core and the loop dispatch of this file are
the same calls the page's Edit button and the agent's own tool call
reach.
"""

import pytest

from imasviz.VizAgent import journals
from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.core import McpGuiCore
from imasviz.VizAgent.journals import JournalStore

USER = 'writer'


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A private HOME, the same shape test_131 and test_133 hold: the
    store reads ``$HOME`` when it is called, not at import."""
    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('USER', USER)
    return home


def _note(home, **fields):
    author = fields.pop('author', USER)
    return JournalStore.add_note(
        'personal', 'Plasma instability after 0.4 s of the shot.',
        author=author, **fields)


class FakeDispatcher:
    def call(self, function, timeout=300.0):
        return function()


def _loop(core):
    return AgentLoop(core=core, llm=object(), dispatcher=FakeDispatcher(),
                     main_window=None, api=None)


def test_the_edit_keeps_the_id_and_replaces_what_is_named(home):
    """The same note, under the same id: the file name of the note is
    what the other writers read it under, and it is not a field the
    edit moves — a field the caller names takes the place of the one
    the note held, and a field it left out keeps the one it held."""
    note = _note(home, machine='WEST', campaign='2026-06', shot='54924',
                 date='2026-06-03', title='Choc 54924')

    edited = JournalStore.edit_note(
        'personal', note['id'],
        text='The plasma came unstable at 0.6 s, not 0.4.',
        shot='55001', title='Choc 55001')

    # The same id and the same place: not a new line.
    assert edited['id'] == note['id']
    assert edited['path'] == note['path']
    assert edited['edited'] is True
    # The named fields took the place of the ones the note held...
    assert edited['text'] == 'The plasma came unstable at 0.6 s, not 0.4.'
    assert edited['shot'] == '55001'
    assert edited['title'] == 'Choc 55001'
    # ...and the fields it left out kept the ones the note held.
    assert edited['machine'] == 'WEST'
    assert edited['campaign'] == '2026-06'
    assert edited['date'] == '2026-06-03'
    assert edited['author'] == USER

    # The read under the id the other writers use answers the edit:
    # the old body is gone from the place it was read under.
    read = JournalStore.read_note('personal', note['id'])
    assert read['id'] == note['id']
    assert '0.6 s' in read['text']
    assert '0.4 s' not in read['text']
    assert read['shot'] == '55001'
    assert read['title'] == 'Choc 55001'
    assert read['machine'] == 'WEST'


def test_the_edit_leaves_the_line_whole_when_it_names_nothing(home):
    """An edit that names no field is the note it held: the one the
    caller asks of without saying a word is the same line the reader
    read before, the same body under the same id."""
    note = _note(home, machine='WEST', shot='54924')
    edited = JournalStore.edit_note('personal', note['id'])
    read = JournalStore.read_note('personal', note['id'])
    assert edited['text'] == read['text'] == note['text']
    assert edited['machine'] == read['machine'] == 'WEST'
    assert edited['shot'] == read['shot'] == '54924'


def test_the_edit_clears_a_field_the_caller_leaves_empty(home):
    """The form the page wears: a field the user left empty is one they
    took off the note — the empty value of the form is the clear, and
    the clear is what the core answers to the caller, whatever the
    note held before."""
    note = _note(home, machine='WEST', campaign='2026-06', title='Choc 54924')
    edited = JournalStore.edit_note(
        'personal', note['id'], campaign='', title='')
    read = JournalStore.read_note('personal', note['id'])
    assert read['campaign'] is None, \
        'a campaign left empty on the form is cleared from the note: %r' \
        % read['campaign']
    assert read['title'] is None, \
        'a title left empty on the form is cleared from the note: %r' \
        % read['title']
    # The fields the form did not touch stand where they were.
    assert read['machine'] == 'WEST'
    assert read['text'] == note['text']


def test_an_edit_that_emptying_the_author_is_refused_by_name(home):
    """The one a note does not go without: author. An edit that empties
    it is the named refusal the write earns — a note with no author is
    not a note of this journal — and the note on disk is the one it
    was: a refused edit takes nothing away and puts nothing on."""
    note = _note(home, machine='WEST')
    with pytest.raises(ValueError) as exc:
        JournalStore.edit_note('personal', note['id'], author='')
    refusal = str(exc.value)
    assert 'author' in refusal, \
        'the refusal names the field it is about: %r' % refusal
    read = JournalStore.read_note('personal', note['id'])
    assert read['author'] == USER
    assert read['machine'] == 'WEST'
    assert read['text'] == note['text']


def test_an_edit_that_emptying_the_body_is_refused_by_name(home):
    """The one a note does not go without: body. An edit that empties
    it is the named refusal the write earns, and the note on disk is
    the one it was."""
    note = _note(home, machine='WEST')
    with pytest.raises(ValueError) as exc:
        JournalStore.edit_note('personal', note['id'], text='')
    refusal = str(exc.value)
    assert 'body' in refusal, \
        'the refusal names the field it is about: %r' % refusal
    read = JournalStore.read_note('personal', note['id'])
    assert 'instability' in read['text']


def test_editing_a_note_the_journal_does_not_hold_is_refused(home):
    """A note id the journal does not hold is a refusal by name, the
    same shape the delete earns: the ids it does hold are named, and
    nothing is written where there is nothing to edit."""
    _note(home, machine='WEST')
    with pytest.raises(ValueError) as exc:
        JournalStore.edit_note('personal', 'a-note-that-is-not-there',
                               text='a body for nothing')
    refusal = str(exc.value)
    assert 'a-note-that-is-not-there' in refusal, \
        'the refusal names the id the caller asked of: %r' % refusal
    assert 'the one its file name' not in refusal


def test_the_core_answers_edit_note(home):
    """The core the loop dispatches against carries the name: the
    same rule test_116 pins for the TOOLS list — a name the loop or
    the page may call is a method the core answers."""
    core = McpGuiCore.__new__(McpGuiCore)
    note = _note(home, machine='WEST')
    answer = core.edit_note('personal', note['id'], text='an edited body.')
    assert answer['id'] == note['id']
    assert answer['edited'] is True
    read = JournalStore.read_note('personal', note['id'])
    assert read['text'] == 'an edited body.'


def test_the_loop_dispatches_the_personal_edit_to_the_core(home):
    """The agent's own edit of a PERSONAL note on a plain request is
    not a refusal: the gate holds for the shared journal only, and
    the dispatch reaches the core with the fields it was named — the
    same ``AgentLoop._dispatch`` the page's Save button reaches
    through, with the same note answered on the disk it is under."""
    note = _note(home, machine='WEST', shot='54924')
    loop = _loop(McpGuiCore.__new__(McpGuiCore))
    answer = loop._dispatch(
        'edit_note',
        {'scope': 'personal', 'note_id': note['id'],
         'text': 'edited by the loop.'},
        requested_by='model',
        user_prompt='change that line about the plasma')
    assert answer['id'] == note['id']
    read = JournalStore.read_note('personal', note['id'])
    assert read['text'] == 'edited by the loop.'
    # The fields the loop did not name kept the ones the note held.
    assert read['machine'] == 'WEST'
    assert read['shot'] == '54924'


def test_the_loop_refuses_an_unknown_parameter_of_edit_note(home):
    """A field the edit does not take is refused by naming the one the
    caller gave and the ones the tool holds — the same guard test_119
    pins for the page's direct calls, because the loop and the page
    run the one ``_dispatch``; a ``bogus`` the caller invented is the
    named refusal, not a ``TypeError`` the caller cannot read."""
    note = _note(home, machine='WEST')
    loop = _loop(McpGuiCore.__new__(McpGuiCore))
    with pytest.raises(ValueError) as exc:
        loop._dispatch('edit_note',
                       {'scope': 'personal', 'note_id': note['id'],
                        'bogus': 'a word'},
                       requested_by='model',
                       user_prompt='edit that note')
    refusal = str(exc.value)
    assert 'bogus' in refusal, \
        'the refusal names the parameter the caller gave: %r' % refusal
    for held in ('scope', 'note_id', 'text', 'author', 'machine',
                 'campaign', 'shot', 'date', 'title'):
        assert held in refusal, \
            'the refusal names the field the tool holds: %r' % held
    # A refused edit is not a run of it: the note is where it was.
    read = JournalStore.read_note('personal', note['id'])
    assert 'instability' in read['text']


def test_the_edit_invalidates_the_cache_of_the_body_the_note_held(home):
    """A search after the edit ranks the line the reader reads after:
    the cache of the body the note held is out with the body, and the
    one the edit put in (when it had a vector) is out the same — the
    old vector is not the answer the new body earned, and the next
    search of the note asks for it or reads what the disk holds."""
    note = _note(home, machine='WEST')
    folder = JournalStore.personalDirectory()
    old_digest = journals._hashBody(JournalStore.read_note(
        'personal', note['id'])['text'])
    new_body = 'a body the vectors no longer cover.'
    new_digest = journals._hashBody(new_body)

    # A run that had searched the note holds a vector for both bodies
    # the note will wear (the one it holds now and the one the edit
    # asks for): both are the derived cache, and both are gone with
    # the edit.
    journals._writeCache(folder, old_digest, [0.1, 0.2])
    journals._writeCache(folder, new_digest, [0.3, 0.4])

    JournalStore.edit_note(
        'personal', note['id'], text=new_body)

    assert journals._readCache(folder, old_digest) is None, \
        'the vector of the body the note held is a cache of that body: ' \
        'the edit out its body'
    assert journals._readCache(folder, new_digest) is None, \
        'a vector the edit would read was the one the search of before ' \
        'held: not the answer the edit earned'


def test_the_search_after_the_edit_ranks_the_edited_line(home):
    """The end the edit is for: the search the reader runs after the
    edit ranks the body the edit wrote (the new words are in it), and
    the one the note was before stands out of the ranked list — the
    words it held are not in the note the disk now holds."""
    note = _note(home, machine='WEST')
    JournalStore.edit_note(
        'personal', note['id'],
        text='the torquer was misaligned on the vacuum line.')
    notes = JournalStore.list_notes('personal')
    ranked = journals.rankByKeyword(notes, 'torquer misaligned')
    assert [n.id for n in ranked] == [note['id']], \
        'the search of the new words ranks the note the edit wrote'
    empty = journals.rankByKeyword(notes, 'instability')
    assert empty == [], \
        'the word of the body the note held is not in it any more'
