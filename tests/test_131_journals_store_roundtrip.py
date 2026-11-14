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

"""The journal store: a note round-trips, and a shape it holds is refused by name.

The store is the one place the two journals live (the personal under
``$HOME/.imasviz/journals``, the shared under
``$HOME/<SharedJournalDir>``), and every write, read and filter is a
pure read of that disk. This file drives the store against a private
HOME (``tmp_path``) so no test touches the user's real journals, and
pins the contract the six gestures and the four surfaces rely on:

- a note that names the five filters the user asked for
  (machine / campaign / shot / date / author) round-trips -- the add,
  the list and the read all answer the same fields;
- a general note that names no filter still round-trips -- a filter
  it does not carry is still matched by the query over its body;
- a filter a note does not have excludes it from the answer;
- an explicit ask for a scope that is not on this node is refused by
  name -- the one that does answer is the one the node holds;
- a write with no author (``$USER`` cleared and no named author) is
  refused by name -- a writer it cannot attribute to is one the journal
  does not hold;
- a hand-written file that is not a note of this journal (no author
  line) is not in the list, and a read of it is refused by name.
"""

import os

import pytest

from imasviz.VizAgent.journals import JournalStore, rankByKeyword

USER = 'writer'


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A private HOME, so no test writes under the user's real journals.

    The store reads ``$HOME`` when each method is called (not at
    import), which is what ``monkeypatch.setenv('HOME', ...)`` gives the
    test here. The personal directory (``$HOME/.imasviz/journals``) is
    created by the first write of the personal scope.
    """
    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('USER', USER)
    return home


def _write(home, scope='personal', body='The plasma was very unstable '
           'after 0.4 s of the shot.', **fields):
    author = fields.pop('author', USER)
    return JournalStore.add_note(
        scope, body, author=author, **fields)


def test_a_note_with_all_filters_roundtrips(home):
    """A shot note (machine, campaign, shot, date, author) is the answer
    a reader expects: every filter the user asked for is carried by the
    note, and a search that names them finds it, and the one that names
    a field the note does not have does not.
    """
    note = _write(
        home,
        machine='WEST', campaign='2026-06', shot='54924',
        date='2026-06-03', title='Choc 54924',
    )
    assert note['id'] and note['path'].endswith('.md')

    # The read, by id, is the full body under the same id the add named.
    read = JournalStore.read_note('personal', note['id'])
    assert read['id'] == note['id']
    assert read['machine'] == 'WEST'
    assert read['campaign'] == '2026-06'
    assert read['shot'] == '54924'
    assert read['date'] == '2026-06-03'
    assert read['title'] == 'Choc 54924'
    assert 'unstable' in read['text']

    # The filter, in each of its shapes, answers one note -- the one
    # that carries it.
    assert len(JournalStore.list_notes('personal', machine='WEST')) == 1
    assert len(JournalStore.list_notes('personal', machine='west')) == 1, \
        'a filter is a word match -- the same answer in either case'
    assert len(JournalStore.list_notes('personal', machine='JET')) == 0, \
        'a machine the note does not carry is not a match'
    assert len(JournalStore.list_notes('personal', shot='54924')) == 1
    assert len(JournalStore.list_notes('personal', shot='12345')) == 0
    assert len(JournalStore.list_notes('personal', campaign='2026-06')) == 1
    assert len(JournalStore.list_notes(
        'personal', date_from='2026-06-01', date_to='2026-06-30')) == 1
    assert len(JournalStore.list_notes(
        'personal',
        date_from='2026-07-01', date_to='2026-07-31')) == 0, \
        'a date the note does not carry is not in the window'
    assert len(JournalStore.list_notes('personal', author=USER)) == 1
    assert len(JournalStore.list_notes('personal', author='nobody')) == 0


def test_a_general_note_roundtrips(home):
    """A general observation that names no machine, campaign, shot or
    date still round-trips: the write, the list, and the read all
    see it. A filter it does not carry excludes it, and the query
    over its body is where it is matched."""
    note = _write(home, body='A general observation, nothing to do '
              'with a plot or a case.')
    assert note['id']
    read = JournalStore.read_note('personal', note['id'])
    assert read['machine'] is None
    assert read['campaign'] is None
    assert read['shot'] is None
    assert read['date'] is None
    assert 'general observation' in read['text']

    # The one note in the journal, and the one its body answers.
    assert len(JournalStore.list_notes('personal', machine='WEST')) == 0
    assert len(JournalStore.list_notes('personal')) == 1
    assert all(n.id == note['id'] for n in
               JournalStore.list_notes('personal'))


def test_filters_are_anded(home):
    """Two filters on one answer is the AND the user asked for -- a
    machine and a shot the note does not both carry is not a match,
    even if the note carries one of them."""
    _write(home, machine='WEST', shot='54924',
           body='A WEST 54924 note.')
    _write(home, machine='JET', shot='70000',
           body='A JET 70000 note.')

    # A WEST + 54924: one -- the WEST note. Not the JET one.
    assert len(JournalStore.list_notes('personal', machine='WEST',
                                       shot='54924')) == 1
    # A WEST + 70000: zero -- the WEST note is not 70000, and the JET
    # one is not WEST.
    assert len(JournalStore.list_notes('personal', machine='WEST',
                                       shot='70000')) == 0


def test_shared_not_set_is_a_named_refusal(home, monkeypatch):
    """An explicit ask for the shared journal, on a node that does not
    hold one (``SharedJournalDir`` not set), is refused by name: the
    refusal names the shared scope and the reason -- not a silent
    empty list. The unscoped ask degrades to the personal one the node
    does hold, without costing a refusal."""
    from imasviz.VizUtils import QVizPreferences
    monkeypatch.setattr(QVizPreferences, 'SharedJournalDir', '', raising=False)
    with pytest.raises(ValueError) as exc:
        JournalStore.sharedDirectory()
    assert 'shared journal' in str(exc.value) or \
        'SharedJournalDir' in str(exc.value), \
        'the refusal names the shared scope -- not a silent %r' % exc.value
    with pytest.raises(ValueError) as exc:
        JournalStore.list_notes('shared')
    assert 'shared journal' in str(exc.value) or \
        'SharedJournalDir' in str(exc.value), \
        'a list that names the shared scope on a node without one is ' \
        'refused by name, not emptied: %r' % exc.value
    # The personal one is the one that answers, and an unscoped ask
    # degrades to it: no refusal, just the personal list.
    _write(home, body='A personal note on a node without the shared side.')
    both = JournalStore.list_notes(None)
    assert len(both) == 1
    assert all(n.scope == 'personal' for n in both)


def test_no_author_is_a_named_refusal(home):
    """A write with no ``author`` -- the one the caller named and the
    one ``$USER`` answers -- is refused by name, not written: a writer
    it cannot attribute to is one the journal does not hold. The
    refusal names the ask, and a file is not created."""
    monkeypatch_user = os.environ.get('USER')
    try:
        os.environ.pop('USER', None)
        with pytest.raises(ValueError) as exc:
            JournalStore.add_note('personal', 'a body', author=None)
        msg = str(exc.value).lower()
        assert 'author' in msg, \
            'the refusal must name the missing author -- %r' % msg
    finally:
        if monkeypatch_user is not None:
            os.environ['USER'] = monkeypatch_user
        else:
            os.environ.pop('USER', None)
    files = [n for n in os.listdir(JournalStore.personalDirectory())
             if n.endswith('.md')]
    assert files == [], \
        'a refused write must not leave a file: %r' % files


def test_a_handwritten_file_without_an_author_is_not_in_the_list(home):
    """A note of this journal is one that names its author in the front
    matter. A hand-written file that does not carry an author line is
    not a note the journal answers -- the list does not hide it, and
    the read of it is refused by name. The refusal names the file."""
    _write(home, body='A real note.')
    folder = JournalStore.personalDirectory()
    path = os.path.join(folder, 'noauthor.md')
    with open(path, 'w') as f:
        f.write('machine: WEST\n\nA body that has no author line at all.\n')

    noted = JournalStore.list_notes('personal')
    assert all(n.path != path for n in noted)


def test_keyword_ranking_orders_the_matches(home):
    """A note the query names comes before the one the query does not
    name; a query that names no note at all answers the empty list,
    not a refusal the reader reads like a crash."""
    note_a = _write(home, machine='WEST',
                    body='Plasma instability at 0.4 s.')
    note_b = _write(home, machine='JET',
                    body='The probe calibration was off.')
    ranked = rankByKeyword(
        JournalStore.list_notes('personal'),
        'plasma instability WEST')
    assert ranked, 'a query that matches a note must not answer empty'
    assert ranked[0].id == note_a['id']
    assert rankByKeyword(
        JournalStore.list_notes('personal'),
        'zorkleplasm') == []
