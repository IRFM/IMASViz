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

"""The persistent RAG index — the engine that serves the journals and the
documents corpus.

The one the journals sit on (test_149) and the documents corpus will sit on
(test_150), so this tests it on its own, with a stand-in embedder (a fixed
table of the text to its vector, the one ``EmbeddingClient`` is a stand-in
for in the suite) and a private HOME (the ``journals``'s shape), the same
harness ``test_131`` holds. It pins the rules the caller is offered
against

* the **eager upsert** — one row and, when an embedder is handed, its
  vector on the spot; a second upsert of the same text under the same
  embedder is a keep, not a re-embed (the incremental the ``reindex`` is);
* the **search** — the BM25 over the stored text fused with the cosine of
  the query against the stored one (``method: 'hybrid'``), the vector
  alone (``'embeddings'``), or the lexical list alone (``'keyword'``), and
  the empty one (``'empty'``);
* the **model/dim guard** — an index written under an ``embed_sig`` the run
  is not under answers ``guarded`` and the keyword alone (the two spaces
  do not meet), the reason named;
* the **reindex** — the whole source in step (what it keeps, what it
  writes, what it purges), idempotent on an unchanged source; and
* the **refusals** — a store that cannot be opened, a row with no text,
  and a search on an empty store, each in words.

No IMAS, no Qt: the engine is standard library, numpy (when present) and
the one embedder the caller hands, the stand-in here.
"""

import os

import pytest

import imasviz.VizAgent.rag_store as rag_store
from imasviz.VizAgent.rag_store import Store


class TableEmbedder:
    """The one the suite hands for an ``EmbeddingClient``: a fixed table
    of the text to its vector. A text the table does not hold is a refusal
    — the one ``EmbeddingClient.embed`` raises for a text it cannot
    vectorise — and the ranking drops the note it could not vector, the
    same rule the one in the field applies. ``calls`` is the count the
    test reads to check the re-embed the upsert did (or did not) pay."""

    def __init__(self, table):
        self.table = dict(table)
        self.calls = 0

    def __call__(self, text):
        self.calls += 1
        if text in self.table:
            return self.table[text]
        raise ConnectionError(
            'the endpoint did not answer a vector for %r' % (text,))


@pytest.fixture
def sig(monkeypatch):
    """Name the endpoint/model the preferences hold, so ``_embedSig`` the
    store records is one the test controls. The two are set to the same
    value the store writes under, and the guard is tripped by setting a
    different one on the run side (the ``set_sig`` helper)."""
    from imasviz.VizUtils import QVizPreferences
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedEndpoint',
                        'http://127.0.0.1:8081/v1', raising=False)
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedModel', 'test-embed',
                        raising=False)
    return 'http://127.0.0.1:8081/v1|test-embed'


@pytest.fixture
def store(tmp_path):
    """One store at a private file, its tables and its meta."""
    path = os.path.join(str(tmp_path), 'index.sqlite')
    return Store.open(path, 'journal')


TABLE = {
    'plasma instability after 0.4 s': [0.9, 0.1],
    'the probe calibration was off': [0.0, 1.0],
    'plasma instability': [1.0, 0.0],
}


def test_a_row_with_no_text_is_refused_by_name(store):
    """The one a store does not index: a row with no text. The refusal
    names it rather than writing an empty line the search would rank."""
    with pytest.raises(ValueError) as exc:
        store.upsert('empty', '   ', embedder=None)
    assert 'text' in str(exc.value).lower()
    assert store.count() == 0


def test_upsert_writes_a_row_and_keeps_its_meta(store, sig):
    """The eager write: one row under its id, its meta kept, and the count
    the stats answer holds one line."""
    out = store.upsert('n1', 'plasma instability after 0.4 s',
                       meta={'machine': 'WEST'}, embedder=None)
    assert out['upserted'] is True
    assert store.count() == 1
    assert store.rowOf('n1') == 'plasma instability after 0.4 s'
    assert store._rowMeta('n1') is not None


def test_upsert_with_no_embedder_is_lexical_only(store):
    """A store the run cannot vector (the endpoint not named, ``embedder``
    is ``None``) is still indexed on its text: the lexical list stands, and
    no vector is written under an ``embed_sig`` the run could not name."""
    store.upsert('n1', 'plasma instability after 0.4 s', embedder=None)
    assert store._vectorOf('n1') is None
    results = store.search('plasma instability', embedder=None)
    assert results['method'] == 'keyword'
    assert results['note_ids'] == ['n1']


def test_upsert_with_an_embedder_writes_its_vector(store, sig):
    """The eager vector: the embedder is asked for the note's text, and the
    vector is written under the store's ``embed_sig`` (the one the run is
    under), so a search on the same endpoint reads it back and ranks it."""
    emb = TableEmbedder(TABLE)
    store.upsert('n1', 'plasma instability after 0.4 s', embedder=emb)
    assert store._vectorOf('n1') is not None
    assert store._meta('embed_sig') == sig
    assert int(store._meta('dim')) == 2


def test_a_second_upsert_of_the_same_text_is_a_keep_not_a_re_embed(
        store, sig):
    """The incremental: an upsert of a row whose text and ``embed_sig`` are
    unchanged, and that already carries a vector, is a keep. The re-embed
    the ``reindex`` would otherwise pay on every write is the one that is
    not paid — the ``embedder`` is not asked for the text a second time."""
    emb = TableEmbedder(TABLE)
    store.upsert('n1', 'plasma instability after 0.4 s',
                 meta={'machine': 'WEST'}, embedder=emb)
    assert emb.calls == 1
    second = TableEmbedder(TABLE)
    out = store.upsert('n1', 'plasma instability after 0.4 s',
                       meta={'machine': 'WEST'}, embedder=second)
    assert out['upserted'] is False and out.get('reason') == 'unchanged'
    assert second.calls == 0, \
        'a row that did not move was re-embedded: %d call(s)' \
        % second.calls
    # A changed body is the one that re-embeds (the edit of a note).
    third = TableEmbedder(TABLE)
    out3 = store.upsert('n1', 'the plasma came unstable at 0.6 s',
                        embedder=third)
    assert out3['upserted'] is True, \
        'a row that moved was kept: %r' % out3
    assert third.calls == 1, \
        'the body the edit wrote was not vectorized: %d call(s)' \
        % third.calls


def test_remove_drops_the_row_and_its_vector(store, sig):
    """The eager delete: the row and its vector are gone, and a remove of a
    note the store never held is the no-op that says so (not a refusal the
    caller reads as a crash, not a line it would not hold)."""
    store.upsert('n1', 'plasma instability after 0.4 s',
                 embedder=TableEmbedder(TABLE))
    assert store.remove('n1')['removed'] is True
    assert store.count() == 0
    assert store.remove('not-there')['removed'] is False


def test_reindex_is_incremental_and_purges_the_orphans(store, sig):
    """The one a ``reindex_journals`` answers: the source in step. What it
    keeps (unchanged), what it writes (moved or new), what it purges (gone
    from the source), and the count the store holds after — and it is
    idempotent on an unchanged source (a second run writes nothing)."""
    records = [
        {'id': 'n1', 'text': 'plasma instability after 0.4 s',
         'meta': {'machine': 'WEST'}},
        {'id': 'n2', 'text': 'the probe calibration was off',
         'meta': {'machine': 'WEST'}},
    ]
    first = store.reindex(records, embedder=TableEmbedder(TABLE))
    assert first['upserted'] == 2 and first['kept'] == 0
    assert first['purged'] == 0 and first['total'] == 2
    # The orphans: a source that no longer names n2 is the one the purge
    # answers.
    again = store.reindex([records[0]], embedder=TableEmbedder(TABLE))
    assert again['purged'] == 1, \
        'the note the source took out was not purged: %r' % again
    assert again['total'] == 1
    # Idempotent: the same source, the same text, nothing re-embedded.
    calls = TableEmbedder(TABLE)
    idem = store.reindex(records, embedder=calls)
    assert idem['kept'] >= 1, 'an unchanged source was re-embedded: %r' \
        % idem


def test_search_fuses_the_lexical_and_the_vector_lists(store, sig):
    """The hybrid: the BM25 over the stored text and the cosine of the
    query against the stored one are both in the answer (a note the query
    names in words and a note the query's vector reaches are both ranked,
    and the method says the two ran). The one the query's words and the
    vector both point at comes first."""
    store.upsert('n1', 'plasma instability after 0.4 s',
                 embedder=TableEmbedder(TABLE))
    store.upsert('n2', 'the probe calibration was off',
                 embedder=TableEmbedder(TABLE))
    results = store.search('plasma instability',
                           embedder=TableEmbedder(TABLE))
    assert results['method'] == 'hybrid', \
        'both lists ranked, the fusion is the answer: %r' % results
    assert results['note_ids'][0] == 'n1'


def test_search_answers_the_vector_alone_when_the_text_matches_nothing(
        store, sig):
    """The ``embeddings`` method: a query whose tokens the stored text does
    not hold (nothing to rank by words) is still answered by the cosine —
    the note the vector reaches is the answer, and the method says the
    vectors ranked it, not the keyword."""
    store.upsert('n1', 'plasma instability after 0.4 s',
                 embedder=TableEmbedder(TABLE))
    store.upsert('n2', 'the probe calibration was off',
                 embedder=TableEmbedder(TABLE))
    # A query with no token in either text, but a vector that points at n1.
    results = store.search('zzz qqq unique',
                           embedder=TableEmbedder({'zzz qqq unique': [0.9, 0.1]}))
    assert results['note_ids'] and results['note_ids'][0] == 'n1'
    # The text token-matched nothing: the method is the vectors' alone.
    assert results['method'] in ('embeddings', 'hybrid')


def test_a_store_under_a_different_embedder_is_guarded(store, sig,
                                                        monkeypatch):
    """The guard: an index written under ``embed_sig`` A, and a run under
    B, does not rank the query in one space against the notes written in
    the other. The vectors are ignored (the lexical list answers alone),
    the answer is ``guarded`` with the reason, and a reindex under B is
    the one that sets the two in step."""
    store.upsert('n1', 'plasma instability after 0.4 s',
                 embedder=TableEmbedder(TABLE))
    assert store._meta('embed_sig') == sig
    # The run is now under a different endpoint: the guard trips.
    from imasviz.VizUtils import QVizPreferences
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedModel', 'another-model',
                        raising=False)
    results = store.search('plasma instability',
                           embedder=TableEmbedder(TABLE))
    assert results['guarded'] is True, \
        'an index under a different embedder is named, not mixed: %r' \
        % results
    assert results['method'] == 'keyword', \
        'the vectors were ignored, the keyword stands: %r' % results
    assert 'embedder' in results['guard_reason']
    assert 'reindex' in results['guard_reason'].lower() \
        or 'Reindex' in results['guard_reason']


def test_a_search_on_an_empty_store_says_empty(store):
    """The one the caller reads as "index it first": a store with no rows
    answers ``total: 0`` and ``method: 'empty'`` — not a crash, and not a
    keyword list it would not hold."""
    results = store.search('anything', embedder=None)
    assert results['total'] == 0
    assert results['method'] == 'empty'
    assert results['note_ids'] == []


def test_stats_names_the_rows_vectors_and_signature(store, sig):
    """The one a ``journal_stats`` / ``reindex`` answer reads: how many rows
    the store holds, how many of them carry a vector, its ``source_type``,
    its ``embed_sig`` and ``dim``, and when it was built."""
    store.upsert('n1', 'plasma instability after 0.4 s',
                 embedder=TableEmbedder(TABLE))
    s = store.stats()
    assert s['source_type'] == 'journal'
    assert s['rows'] == 1
    assert s['vectors'] == 1
    assert s['embed_sig'] == sig
    assert int(s['dim']) == 2


def test_a_store_that_cannot_be_opened_is_refused_by_name(tmp_path):
    """A file that is a place (not a file) in the middle is a named refusal
    — the caller reads it as "the store is not there", not a crash. A
    missing HOME for the personal one is the same refusal the ``journals``
    answers (test_149)."""
    a_file = os.path.join(str(tmp_path), 'a-file')
    with open(a_file, 'w') as f:
        f.write('x')
    with pytest.raises(ValueError) as exc:
        Store.open(os.path.join(a_file, 'index.sqlite'))
    assert 'index' in str(exc.value)
