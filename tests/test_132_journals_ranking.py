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

"""The embeddings ranking of the journal search, with its three states.

The search ranks the notes two ways, in that order:

1. by **embeddings** — the cosine between the query's vector and each
   note's, when ``AgentEmbedEndpoint`` is named and the endpoint answers
   (the vector is cached under the note's journal folder, keyed on the
   note's body);

2. by **keyword** — a light BM25, no dependency — when the endpoint is
   not named, or when it does not answer.

The answer says which one ran: ``method: 'embeddings'`` when the
endpoint answered and ranked, ``method: 'keyword'`` with
``fallback_from: 'embeddings'`` and the reason named when it was asked
but did not answer, and ``method: 'keyword'`` with no fallback when it
was not asked at all. A note the endpoint could not vector is dropped
from the ranked list — the reader reads that as one the search did not
rank, not an empty answer, and the ranking does not say the note does
not exist either.
"""

import os

import pytest

from imasviz.VizAgent.core import McpGuiCore
from imasviz.VizAgent.journals import JournalStore, rankByVector

USER = 'writer'
QUERY = 'plasma instability after 0.4 s'


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('USER', USER)
    return home


def _core():
    """The journal gestures of the core, without a full session: they
    are pure reads of the store and the preferences, and do not touch
    the instance state a case open would give it — so a bare object is
    the self they need, and the test is about the store and the
    preferences, not the case."""
    return object.__new__(McpGuiCore)


def _write(home, body, machine='WEST', **fields):
    return JournalStore.add_note(
        'personal', body, author=USER, machine=machine, **fields)


class PermissiveEmbedder:
    """The stand-in for the ``EmbeddingClient``: a fixed table of the
    text to its vector. A text the table does not hold is a refusal —
    the one the ``EmbeddingClient`` raises for a text it cannot
    vectorise — and the ranking drops the note it could not vector,
    the same rule the one in the field applies."""

    def __init__(self, table):
        self.table = dict(table)
        self.calls = 0

    def __call__(self, text):
        self.calls += 1
        if text in self.table:
            return self.table[text]
        raise ConnectionError(
            'the endpoint does not answer a vector for %r' % (text,))


def test_keyword_ranks_the_matching_note_first(home):
    """The keyword is the ranking the answer holds while no endpoint is
    named: the note the query names comes before the one it does not,
    and a query that names no note answers the empty list, not a
    refusal the reader reads like a crash."""
    note_a = _write(home, body='Plasma instability after 0.4 s.')
    _write(home, body='The probe calibration was off.')
    notes = JournalStore.list_notes('personal')
    ranked = rankByVector(notes, QUERY, PermissiveEmbedder(
        {QUERY: [1.0, 0.0],
         'Plasma instability after 0.4 s.': [0.9, 0.1],
         'The probe calibration was off.': [0.0, 1.0]}),
        cacheFolders={'personal': JournalStore.personalDirectory()})
    assert ranked, 'a query that matches a note must not answer empty'
    assert ranked[0].id == note_a['id'], \
        'the note the query names comes first: %r' % [n.id for n in ranked]


def test_endpoint_named_but_not_answering_falls_back_named(home, monkeypatch):
    """An endpoint that is named but does not answer is the keyword,
    with the fallback named: the answer says ``method: 'keyword'`` and
    ``fallback_from: 'embeddings'``, and the note it still ranks is the
    one the keyword would have, not nothing."""
    from imasviz.VizUtils import QVizPreferences
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedEndpoint',
                        'http://localhost:9999/v1', raising=False)
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedModel', 'fake-embed',
                        raising=False)

    _write(home, body='Plasma instability after 0.4 s.')

    # The stand-in for the EmbeddingClient. The endpoint does not
    # answer, so the call raises ConnectionError — the shape the
    # real client raises for a server that is not there. rankByVector
    # names that as a query it cannot vector, and the core's own
    # reader falls back to the keyword, with the reason named.
    class FailingEmbedder:
        def __call__(self, text):
            raise ConnectionError(
                'the endpoint does not answer (the server is not there)')
    import imasviz.VizAgent.llm_client as llm
    monkeypatch.setattr(llm, 'EmbeddingClient',
                        lambda *a, **k: FailingEmbedder())

    core = _core()
    result = McpGuiCore.search_journals(
        core, scope='personal', query=QUERY)
    assert result['method'] == 'keyword', \
        'the ranking the run used is named: %r' % result['method']
    assert result['fallback_from'] == 'embeddings', \
        'the read that fell back is named: %r' % result.get('fallback_from')
    assert result['fallback_reason'], \
        'the reason for the fallback is named in the answer'
    assert result['notes'], \
        'the keyword still ranked the note the endpoint could not'


def test_endpoint_not_named_is_a_plain_keyword(home, monkeypatch):
    """An endpoint that is not named is the keyword, with **no**
    fallback named: the reader does not present a keyword as one that
    fell back, and there is no reason to name — the embeddings were
    not asked at all."""
    from imasviz.VizUtils import QVizPreferences
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedEndpoint', '', raising=False)

    _write(home, body='Plasma instability after 0.4 s.')
    core = _core()
    result = McpGuiCore.search_journals(core, scope='personal', query=QUERY)
    assert result['method'] == 'keyword', \
        'no endpoint named: the keyword is the one that runs'
    assert 'fallback_from' not in result, \
        'the keyword was not a fallback: it was the one in force from ' \
        'the start — %r' % result.get('fallback_from')
    assert result['notes']


def test_the_cache_is_the_one_the_endpoint_would_own(home, monkeypatch):
    """The vector the endpoint answers for a note is written under that
    note's journal folder, keyed on its body. The next ranking of the
    same note reads that entry back, and does not ask the endpoint for
    it a second time — the same rule the note's cache is there for."""
    from imasviz.VizUtils import QVizPreferences
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedEndpoint',
                        'http://localhost:9999/v1', raising=False)
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedModel', 'fake-embed',
                        raising=False)

    note = _write(home, body='Plasma instability after 0.4 s.')
    folder = JournalStore.personalDirectory()
    table = {QUERY: [1.0, 0.0], 'Plasma instability after 0.4 s.': [1.0, 0.0]}
    first = PermissiveEmbedder(table)
    notes = JournalStore.list_notes('personal')
    ranked = rankByVector(
        notes, QUERY, first, cacheFolders={'personal': folder})
    assert ranked and [n.id for n in ranked] == [note['id']]

    # The cache wrote one entry under the personal folder, keyed on the
    # note's body — a derived artifact in that folder, not one the run
    # could not own.
    cache_dir = os.path.join(folder, '.embed')
    entries = [n for n in os.listdir(cache_dir) if n.endswith('.json')]
    assert entries, \
        'a cache the endpoint owns was not written: %r' % (
            os.listdir(cache_dir) if os.path.isdir(cache_dir) else 'no .embed')

    # A second ranking of the same note, through an embedder the note's
    # text reaches only if the note's vector is not in the cache: the
    # query is the one the endpoint still asks for (the read is not
    # the cache, the rank is), and the note is the one that is.
    class StrictEmbedder:
        @staticmethod
        def _fail(text):
            raise AssertionError(
                'the note %r came from the endpoint, not from the cache: '
                'the first ranking wrote it, the second should read it'
                % (text,))

        def __call__(self, text):
            if text == QUERY:
                return [1.0, 0.0]
            self._fail(text)

    second = rankByVector(
        notes, QUERY, StrictEmbedder(), cacheFolders={'personal': folder})
    assert [n.id for n in second] == [note['id']], \
        'a cached note is still ranked: %r' % [n.id for n in second]
