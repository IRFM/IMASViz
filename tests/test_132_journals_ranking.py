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

"""The embeddings ranking of the journal search: the one index, and its states.

The journals carry one index — the SQLite store of ``journals_index`` — and
every search asks it of first: the BM25 over the notes' text fused with
the cosine of the query against the one each row holds (the ``hybrid``
method), the method named in the answer. The rules this file pins:

* the note the query names ranks first — the one the endpoint vectors is
  the one the answer leads with;
* an endpoint that is named but does not answer — the query the index
  cannot vector is the keyword, with ``fallback_from: 'embeddings'`` and
  the reason named;
* an endpoint that is not named — the plain keyword, no fallback named;
* the vector the endpoint answers for a note is kept by the store — a
  second search re-embeds the query, not the note.
"""

import pytest

from imasviz.VizAgent.core import McpGuiCore
from imasviz.VizAgent.journals import JournalStore

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


def _namedEndpoint(monkeypatch, endpoint='http://localhost:9999/v1',
                    model='fake-embed'):
    from imasviz.VizUtils import QVizPreferences
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedEndpoint', endpoint,
                        raising=False)
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedModel', model,
                        raising=False)


class PermissiveEmbedder:
    """The stand-in for the ``EmbeddingClient``: the one the index
    answers for a text — the composed note text (the title, the filters,
    the body), not the raw body — matched by substring, the way the
    table in ``test_149`` matches them. A text the table does not hold
    is a refusal — the one the ``EmbeddingClient`` raises for a text it
    cannot vectorise — and the ranking drops the note it could not
    vector, the same rule the one in the field applies."""

    def __init__(self):
        self.calls = 0

    def __call__(self, text):
        self.calls += 1
        low = text.lower()
        if 'plasma' in low:
            return [1.0, 0.0]
        if 'calibration' in low or 'probe' in low:
            return [0.0, 1.0]
        raise ConnectionError(
            'the endpoint does not answer a vector for %r' % (text,))


def test_the_index_ranks_the_note_the_query_names_first(home, monkeypatch):
    """The indexed answer leads with the note the query names: the
    vector the endpoint answers for it is the one the fusion ranks,
    and the answer says ``hybrid`` — not the keyword alone, and not a
    fallback."""
    _namedEndpoint(monkeypatch)
    import imasviz.VizAgent.llm_client as llm
    embedder = PermissiveEmbedder()
    monkeypatch.setattr(llm, 'EmbeddingClient', lambda *a, **k: embedder,
                        raising=False)
    note_a = _write(home, body='Plasma instability after 0.4 s.')
    _write(home, body='The probe calibration was off.')

    core = _core()
    result = McpGuiCore.search_journals(
        core, scope='personal', query=QUERY)
    assert result['indexed'] is True, \
        'the search the index answered is the one named: %r' % result
    assert result['method'] == 'hybrid', \
        'the vectors and the text both ranked: %r' % result['method']
    assert [n['id'] for n in result['notes']], \
        'the note the query names is in the answer'
    assert result['notes'][0]['id'] == note_a['id'], \
        'the note the query names comes first: %r' \
        % [n['id'] for n in result['notes']]


def test_endpoint_named_but_not_answering_falls_back_named(home, monkeypatch):
    """An endpoint that is named but does not answer is the keyword,
    with the fallback named: the answer says ``method: 'keyword'`` and
    ``fallback_from: 'embeddings'``, and the note it still ranks is the
    one the keyword would have, not nothing."""
    _namedEndpoint(monkeypatch)

    _write(home, body='Plasma instability after 0.4 s.')

    # The stand-in for the EmbeddingClient. The endpoint does not
    # answer, so the call raises ConnectionError — the shape the
    # real client raises for a server that is not there. The index
    # names that as a query it cannot vector, and the core's own
    # reader falls back to the keyword, with the reason named.
    class FailingEmbedder:
        def __call__(self, text):
            raise ConnectionError(
                'the endpoint does not answer (the server is not there)')
    import imasviz.VizAgent.llm_client as llm
    monkeypatch.setattr(llm, 'EmbeddingClient',
                        lambda *a, **k: FailingEmbedder(), raising=False)

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


def test_the_store_keeps_the_vector_the_endpoint_answers(home, monkeypatch):
    """The one a second search does not re-embed: the vector the
    endpoint answers for a note is kept by the store, and a second
    search of the same note asks the endpoint for the query and not
    for the note — the embedder's calls grow by one, not by two."""
    _namedEndpoint(monkeypatch)
    from imasviz.VizAgent import journals_index
    import imasviz.VizAgent.llm_client as llm
    embedder = PermissiveEmbedder()
    monkeypatch.setattr(llm, 'EmbeddingClient', lambda *a, **k: embedder,
                        raising=False)
    note = _write(home, body='Plasma instability after 0.4 s.')

    core = _core()
    result = McpGuiCore.search_journals(
        core, scope='personal', query=QUERY)
    assert result['notes'][0]['id'] == note['id']

    # The store holds the row and its vector under the current
    # embed_sig — the one the run is under — and the stats are the one
    # read a reader asks of to see it kept.
    store = journals_index.storeFor('personal')
    try:
        s = store.stats()
        assert s['rows'] == 1 and s['vectors'] == 1, \
            'the vector the endpoint answered is kept by the store: %r' % s
    finally:
        store.close()

    calls = embedder.calls
    result = McpGuiCore.search_journals(
        core, scope='personal', query=QUERY)
    assert [n['id'] for n in result['notes']] == [note['id']]
    assert embedder.calls == calls + 1, \
        'a second search asks the endpoint for the query, not the note: ' \
        '%d calls after the first, %d after the second' \
        % (calls, embedder.calls)
