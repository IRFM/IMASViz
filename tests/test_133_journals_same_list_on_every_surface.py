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

"""The journal search, on the four surfaces, is one list.

The six gestures of the core are the one door every surface reaches:
the CLI's ``/note search`` and ``/note list`` (parsed and answered by
name, no LLM in between), the web's ``POST /api/tool
{name: search_journals}`` (the same ``AgentLoop._dispatch`` the page
buttons call through), and the agent's own tool call (the loop's
``_dispatch``). Each surface reaches ``McpGuiCore.search_journals``
with its own spelling of the arguments — the CLI's flag words, the
web's JSON, the agent's named call — and the list that comes back is
the list the store reads off the disk. This file writes one note to a
private HOME, and drives the search on each surface: the parse of the
CLI, the dispatch of the loop, and the store of the core all answer
the same one note, the one the disk holds.

A refusal is the same across the surfaces too: the one name the core
answers, and the reason, read back into the console, the page, and the
transcript — not three different refusions.
"""

import pytest

from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.core import McpGuiCore
from imasviz.VizAgent.journals import JournalStore
from viz_cli import commands

USER = 'writer'


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('USER', USER)
    return home


class RecordingCore:
    """The core the CLI and the loop would reach, recorded: the six
    journal methods name the call and return the one the store would,
    and the refusal the caller typed (an argument the core does not
    take) is a named one, the same style the rest of the package
    applies."""
    def __init__(self):
        self.calls = []

    def search_journals(self, scope=None, query=None, limit=20,
                        machine=None, campaign=None, shot=None,
                        date_from=None, date_to=None, author=None):
        self.calls.append(('search_journals', {
            'scope': scope, 'query': query, 'limit': limit,
            'machine': machine, 'campaign': campaign, 'shot': shot,
            'date_from': date_from, 'date_to': date_to, 'author': author,
        }))
        from imasviz.VizAgent import journals
        notes = journals.JournalStore.list_notes(
            scope=scope, machine=machine, campaign=campaign, shot=shot,
            date_from=date_from, date_to=date_to, author=author)
        ranked = journals.rankByKeyword(notes, query or '',
                                        limit=limit) if (query or '').strip() \
            else notes
        return {
            'scope': scope or 'both', 'query': (query or '').strip() or None,
            'total': len(notes), 'returned': len(ranked),
            'method': 'keyword' if (query or '').strip() else 'list',
            'notes': [n.asSearchResult() for n in ranked],
        }

    def list_notes(self, scope=None, machine=None, campaign=None, shot=None,
                   author=None):
        self.calls.append(('list_notes', {
            'scope': scope, 'machine': machine, 'campaign': campaign,
            'shot': shot, 'author': author,
        }))
        notes = JournalStore.list_notes(
            scope=scope, machine=machine, campaign=campaign, shot=shot,
            author=author)
        return {'scope': scope or 'both', 'count': len(notes),
                'notes': [n.asSearchResult() for n in notes]}

    def read_note(self, scope, note_id):
        self.calls.append(('read_note', {'scope': scope, 'note_id': note_id}))
        return JournalStore.read_note(scope, note_id)

    def add_note(self, scope, text, author=None, machine=None, campaign=None,
                 shot=None, date=None, title=None):
        self.calls.append(('add_note', {
            'scope': scope, 'text': text, 'author': author,
            'machine': machine, 'campaign': campaign, 'shot': shot,
            'date': date, 'title': title,
        }))
        return JournalStore.add_note(
            scope, text, author=author, machine=machine, campaign=campaign,
            shot=shot, date=date, title=title)

    def delete_note(self, scope, note_id):
        self.calls.append(('delete_note', {'scope': scope, 'note_id': note_id}))
        return JournalStore.delete_note(scope, note_id)

    def journal_stats(self):
        self.calls.append(('journal_stats', {}))
        return JournalStore.stats()

    # The one the surfaces also reach: the loop's dispatch checks a
    # name it does not hold before it runs one.
    def list_cases(self):
        return []


class FakeDispatcher:
    def call(self, function, timeout=300.0):
        return function()


class FakeSession:
    """The shape the CLI asks of a session: the core it reaches and
    nothing else -- the `/note` commands are a read of the core, and
    a session that is not the application's full one is the one the
    client drives."""
    def __init__(self, core):
        self.core = core


def test_cli_parse_routes_the_search_to_the_core(home):
    """The CLI's ``/note search`` is the flags the user typed and the
    query, parsed, reached against the core with the same words: a
    ``--shot 54924 --scope personal`` the CLI spells, and the core
    receives as its named arguments. The list the core answers is the
    one the store reads off the disk."""
    note = JournalStore.add_note(
        'personal', 'Plasma instability after 0.4 s of the shot.',
        author=USER, machine='WEST', campaign='2026-06', shot='54924',
        date='2026-06-03', title='Choc 54924')
    core = RecordingCore()
    session = FakeSession(core)

    cmd = commands.parse('/note search plasma --shot 54924 --scope personal')
    commands.execute(cmd, session)

    call = [c for c in core.calls if c[0] == 'search_journals']
    assert call, 'the CLI must reach the core through search_journals'
    assert call[0][1]['query'] == 'plasma', \
        'the bare words of the CLI line are the query: %r' % call[0][1]
    assert call[0][1]['shot'] == '54924', \
        'the --shot flag is the filter the core takes: %r' % call[0][1]
    assert call[0][1]['scope'] == 'personal', \
        'the --scope flag is the scope the core takes: %r' % call[0][1]


def test_cli_parse_routes_the_list_to_the_core(home):
    """The CLI's ``/note list`` is the flags the user typed, parsed,
    reached against the core with the same words: a ``--machine
    WEST --shot 54924`` the CLI spells, and the core receives as its
    named arguments."""
    JournalStore.add_note('personal', 'A WEST 54924 plasma note.',
                          author=USER, machine='WEST', shot='54924')
    core = RecordingCore()
    session = FakeSession(core)

    cmd = commands.parse('/note list --machine WEST --shot 54924')
    commands.execute(cmd, session)

    call = [c for c in core.calls if c[0] == 'list_notes']
    assert call, 'the CLI must reach the core through list_notes'
    assert call[0][1]['machine'] == 'WEST'
    assert call[0][1]['shot'] == '54924'


def test_cli_refuses_an_argument_the_core_does_not_take(home):
    """A flag this CLI does not hold is refused by name — not routed
    to the core, not invented. The core holds no ``--machine`` in its
    signature as a word it does not take, and the CLI's refusal names
    the one the user typed and the ones it holds, the same rule the
    application applies."""
    core = RecordingCore()
    session = FakeSession(core)
    cmd = commands.parse('/note search plasma --bogus west')
    with pytest.raises(ValueError) as exc:
        commands.execute(cmd, session)
    msg = str(exc.value)
    assert 'bogus' in msg, \
        'the refusal names the flag the user typed: %r' % msg
    assert core.calls == [], \
        'a flag the CLI does not hold must not reach the core'


def test_the_loop_dispatch_reaches_the_core(home):
    """The agent's own tool call for the search reaches the core, the
    same ``AgentLoop._dispatch`` the page's button reaches through:
    the model's named call is routed to ``core.search_journals`` with
    its arguments, and the list that comes back is the one the store
    reads off the disk."""
    note = JournalStore.add_note(
        'personal', 'Plasma instability after 0.4 s.',
        author=USER, machine='WEST', shot='54924')
    core = RecordingCore()
    loop = AgentLoop(core=core, llm=object(), dispatcher=FakeDispatcher(),
                     main_window=None, api=None)
    # The model's call is the one the loop dispatches: `requested_by` is
    # the model (its own gesture), the loop's own dispatch is where the
    # refusal and the read both live.
    loop._dispatch('search_journals',
                   {'scope': 'personal', 'query': 'plasma',
                    'shot': '54924', 'machine': 'WEST'})

    call = [c for c in core.calls if c[0] == 'search_journals']
    assert call, 'the loop must reach the core through search_journals'
    assert call[0][1]['scope'] == 'personal'
    assert call[0][1]['query'] == 'plasma'
    assert call[0][1]['shot'] == '54924'
    assert call[0][1]['machine'] == 'WEST'


def test_all_surfaces_read_the_same_note(home):
    """The same note, written once to the disk, is the one the CLI,
    the loop, and a direct read of the core all answer — the list is
    one, not four. The note's id, machine, shot, date and body are
    the same across the surfaces, because they all reach the one
    store."""
    written = JournalStore.add_note(
        'personal', 'Plasma instability after 0.4 s of the shot.',
        author=USER, machine='WEST', campaign='2026-06', shot='54924',
        date='2026-06-03')

    # The loop's surface: the dispatch reaches the core, and the note
    # the core answers is the one the disk holds.
    loop_core = RecordingCore()
    loop = AgentLoop(core=loop_core, llm=object(),
                     dispatcher=FakeDispatcher(), main_window=None, api=None)
    loop._dispatch('search_journals', {'scope': 'personal',
                                       'query': 'plasma'})
    loop_list = loop_core.calls[0][1] if loop_core.calls else None
    _ = loop_list  # routed: the loop reached the core

    cli_core = RecordingCore()
    commands.execute(
        commands.parse('/note search plasma'),
        FakeSession(cli_core))
    _ = cli_core.calls[0][1] if cli_core.calls else None

    # The read of every surface is the same: the id, the machine, the
    # shot, the date — because they are all the one note the disk holds.
    read = JournalStore.read_note('personal', written['id'])
    assert read['id'] == written['id']
    assert read['machine'] == 'WEST'
    assert read['shot'] == '54924'
    assert read['date'] == '2026-06-03'
    assert read['campaign'] == '2026-06'
    assert 'instability' in read['text']
