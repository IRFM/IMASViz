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

"""The journals' eager index, seen from the core.

The one ``test_131`` answers on the *lazy* path is here joined by the *eager*
one the user asked for: the note is in the index **the moment** it is added,
edited or deleted, so the search that follows is the answer the index gives,
not the read the run builds on the fly. The rules the tests pin, a stand-in
``EmbeddingClient`` (a fixed table) in place of the one under a llama-server,
and a private ``HOME`` (the ``journals``'s shape, ``test_131``'s harness):

* **add** → the note is indexed on the spot (``indexed: True`` on the next
  search, ranked on the text it was added with);
* **edit** → the changed note is re-indexed under its new text;
* **delete** → the note is out of the index;
* **reindex_journals** → the journal in step, idempotent on an unchanged
  source;
* **guard** → an index written under an ``embed_sig`` the run is not under is
  named (``guarded``) and the keyword alone stands;
* **``journal_stats``** → the indexes' rows, vectors, and the one a scope
  answers;
* **refusals** → an ``add_note`` on an endpoint the run cannot reach is
  written into the ``journals`` store and the note is not lost (the index is
  simply behind, and the search still finds it).

``test_148`` holds the engine these gestures drive; this holds the surface.
"""

import os

import pytest

import imasviz.VizAgent.llm_client as llm
from imasviz.VizAgent import agent, journals, core

AUTHOR = 'tester'


class TableEmbedder:
    """The one the core is handed for an ``EmbeddingClient``: a fixed table of
    the text to its vector. A text the table does not point at is a refusal for
    the whole search (the one the run would answer), so the table names every
    note the test writes and the one it searches."""
    def __call__(self, text):
        if 'plasma' in text:
            return [1.0, 0.0]
        if 'probe' in text or 'calibration' in text:
            return [0.0, 1.0]
        raise ConnectionError(
            'the endpoint did not answer a vector for %r' % (text,))


@pytest.fixture
def privateHome(tmp_path, monkeypatch):
    """A ``~/.imasviz`` of the test (the two notes folders and, for the
    shared one, the folder the preferences name)."""
    imasviz_dir = os.path.join(str(tmp_path), 'home', '.imasviz')
    monkeypatch.setenv('HOME', os.path.join(str(tmp_path), 'home'))
    shared = os.path.join(str(tmp_path), 'shared-journal')
    os.makedirs(shared, exist_ok=True)
    from imasviz.VizUtils import QVizPreferences
    monkeypatch.setattr(QVizPreferences, 'SharedJournalDir', shared,
                        raising=False)
    return imasviz_dir


@pytest.fixture
def api(privateHome, monkeypatch):
    """A core with no LLM, the table embedder in place of the one under a
    llama-server, and the endpoint the preferences name (the one
    ``_noteEmbedder`` reads to decide whether to vector)."""
    monkeypatch.setattr(agent, 'LLM_CLIENT', None, raising=False)
    from imasviz.VizUtils import QVizPreferences
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedEndpoint',
                        'http://127.0.0.1:8081/v1', raising=False)
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedModel', 'test-embed',
                        raising=False)
    monkeypatch.setattr(llm, 'EmbeddingClient', lambda: TableEmbedder(),
                        raising=False)
    return core.McpGuiCore()


def _firstId(res):
    """The id of the first note a ``search_journals`` answer ranks (the two
    paths, indexed and lazy, both answer ``notes`` a ``id`` under)."""
    return res['notes'][0]['id']


def test_add_indexes_the_note_on_the_spot(api, privateHome):
    """The rule the user asked for: an ``add_note`` is a write into the store
    *and* a write into the index. The search that follows does not build the
    read from scratch (``indexed: True``), the note is ranked on the text it
    was added with, and the stats hold one row under the note's id — the two
    now agree (the lazy path of ``test_131`` and the eager one)."""
    out = api.add_note('personal', 'plasma instability after 0.4 s',
                       author=AUTHOR, machine='WEST')
    assert out.get('id') and out['text']
    # The eager index: the store (the lazy read's file) and the derived index
    # (the eager one) hold the same note.
    assert journals.JournalStore.list_notes(scope='personal')
    stats = api.journal_stats()
    assert stats['indexes']['personal']['rows'] == 1
    # And a search right after is the one the index answers.
    res = api.search_journals(query='plasma instability')
    assert res['indexed'] is True
    assert _firstId(res) == out['id']


def test_edit_is_re_indexed_under_the_new_text(api, privateHome):
    """The one a search after the edit must find: the note moved from
    'plasma' to 'calibration', so the words a later search types are the ones
    the edit wrote, and the index is the one the edit put them in. A search
    on the old word does not serve a note the edit took it out of."""
    out = api.add_note('personal', 'plasma instability after 0.4 s',
                       author=AUTHOR)
    note_id = out['id']
    api.edit_note('personal', note_id, text='the probe calibration was off')
    # The new word is in the answer (the index is in step with the edit);
    # the old one is not (the row's text is the one the edit wrote).
    res = api.search_journals(query='calibration')
    assert note_id in [n['id'] for n in res['notes']]
    res_old = api.search_journals(query='instability')
    assert note_id not in [n['id'] for n in res_old['notes']], \
        'a note the edit took the word out of is not served under it: %r' \
        % [n['id'] for n in res_old['notes']]
    stats = api.journal_stats()
    assert stats['indexes']['personal']['rows'] == 1


def test_delete_removes_the_note_from_the_index(api, privateHome):
    """The one a search after the delete must not find: the note is out of
    the index (the row and its vector are gone, the one row is down to zero),
    and the store's lazy read and the index's eager one agree the note is
    gone."""
    out = api.add_note('personal', 'plasma instability after 0.4 s',
                       author=AUTHOR)
    note_id = out['id']
    api.delete_note('personal', note_id)
    res = api.search_journals(query='plasma instability')
    assert note_id not in [n['id'] for n in res['notes']]
    assert api.journal_stats()['indexes']['personal']['rows'] == 0


def test_reindex_keeps_the_journal_in_step_and_is_idempotent(api):
    """The one a ``reindex_journals`` answers: the source in step. After two
    notes are added, a reindex reports the two in the personal store and
    nothing it purged; a second reindex on the same source keeps what it
    holds rather than rewriting it (the counts stay the source's)."""
    api.add_note('personal', 'plasma instability after 0.4 s',
                 author=AUTHOR, machine='WEST')
    api.add_note('personal', 'the probe calibration was off',
                 author=AUTHOR, machine='WEST')
    first = api.reindex_journals(scope='personal')
    scopes = first['scopes']
    assert scopes['personal']['total'] == 2
    assert scopes['personal']['purged'] == 0
    assert first['embedder_named'] is True, \
        'the endpoint is named in the preferences, so the run vectorized'
    # Idempotent: the same source, nothing re-written (the total is the
    # source's, and the second run keeps what it holds).
    second = api.reindex_journals(scope='personal')
    assert second['scopes']['personal']['total'] == 2
    assert second['scopes']['personal']['upserted'] == 0 \
        or second['scopes']['personal']['kept'] == 2


def test_an_index_under_a_different_embedder_is_guarded(api, privateHome,
                                                          monkeypatch):
    """The guard: an index written under ``embed_sig`` A and a run under B do
    not rank the query in one space against the notes written in the other —
    the answer is ``guarded``, the keyword alone stands (``method: 'keyword'``),
    the reason names the embedder, and the note is still found (the keyword
    reads the same notes)."""
    from imasviz.VizUtils import QVizPreferences
    out = api.add_note('personal', 'plasma instability after 0.4 s',
                       author=AUTHOR)
    note_id = out['id']
    # The run is now under a different model: the stored sig is the one
    # 'test-embed' wrote, and the current one is not it.
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedModel', 'another-model',
                        raising=False)
    res = api.search_journals(query='plasma instability')
    assert res['guarded'] is True, \
        'an index under a different embedder is named, not mixed: %r' % res
    assert res['method'] == 'keyword', \
        'the vectors were ignored, the keyword stands: %r' % res
    assert 'embedder' in res['guard_reason'].lower()
    # The keyword still finds the note (the refusal is the method and the
    # reason, not the absence of the note).
    assert note_id in [n['id'] for n in res['notes']]


def test_journal_stats_answers_the_two_indexes(api):
    """The one a ``journal_stats`` answer (a reader that asks "how far have I
    indexed?"): how many rows and vectors each store holds, its
    ``embed_sig`` and ``dim`` (the fields the two are in step with the run),
    and the one each scope answers."""
    api.add_note('shared', 'plasma instability after 0.4 s',
                 author=AUTHOR, machine='WEST')
    out = api.journal_stats()
    assert out['indexes']['shared']['rows'] == 1
    # The personal one (empty here) is answered too, as its own store.
    assert out['indexes']['personal']['rows'] == 0
    # And the embeddings the preferences name (the two search asks of to
    # decide the method) are the same fields the stats hold.
    assert 'embeddings' in out


def test_a_note_the_embedder_cannot_vector_is_not_lost(api, privateHome,
                                                          monkeypatch):
    """The one ``test_144``'s refusal answers on the lazy path, here on the
    eager one: an ``add_note`` on an endpoint the run cannot reach (the
    embedder refuses) is *still* written into the ``journals`` store (the
    lazy read the search falls back to), and the note is not lost — a
    search on the same text answers it. The write and the search are the two
    the user does not pay for together; the index may be behind, the note is
    not lost, and a ``reindex_journals`` under a reachable endpoint is the
    one that vectors it."""
    class Refusing:
        def __call__(self, text):
            raise ConnectionError('the endpoint refused the note')
    monkeypatch.setattr(llm, 'EmbeddingClient', lambda: Refusing(),
                        raising=False)
    out = api.add_note('personal', 'plasma instability after 0.4 s',
                       author=AUTHOR)
    assert out.get('id')
    assert journals.JournalStore.list_notes(scope='personal')
    # The search answers the note: the index may not have kept a vector, but
    # the keyword (or the lazy path) still finds it.
    res = api.search_journals(query='plasma instability')
    found = [n['id'] for n in res['notes']]
    assert out['id'] in found, \
        'the note the embedder could not vector is still found: %r' % found
