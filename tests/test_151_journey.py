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

"""The in-app agent's RAG over the user's notes and documents, end to end.

The one ``test_149`` holds for the journals (eager) and ``test_150`` for
the documents corpus, this joins them as the user drives them — a journey
the way ``test_45`` joins the gestures into a continuous one:

* **the note is found the moment it is added** — an ``add_note`` is a write
  and an index in the same turn, and the search that follows is the one
  the index answers (``indexed: True``), not the read the run builds;
* **the corpus is found the moment it is indexed** — the documents the user
  drops in the corpus folder are read by ``reindex_documents``, and
  ``search_documents`` ranks their chunks;
* **a guarded index is named** — the corpus written under an embedding
  endpoint the run is no longer under answers ``guarded`` and the keyword
  alone stands, and ``reindex_documents`` is the one that sets it right.

The stand-in ``EmbeddingClient`` (a fixed table) is in place of the one
under a llama-server, and a private ``HOME``/``AgentDocsDir`` are the two
the corpus the journey reads sit under.
"""

import os

import pytest

import imasviz.VizAgent.llm_client as llm
from imasviz.VizAgent import agent, core

AUTHOR = 'tester'


class TableEmbedder:
    """The one the run is handed for an ``EmbeddingClient``: a fixed table
    of the text to its vector. A text the table does not point at is a
    refusal for the whole search, so the table names every note and passage
    the journey writes and the ones it searches."""
    def __call__(self, text):
        low = text.lower()
        if 'plasma' in low or 'tuning' in low:
            return [1.0, 0.0]
        if 'probe' in low or 'calibration' in low:
            return [0.0, 1.0]
        if 'shot' in low or 'current' in low:
            return [0.7, 0.7]
        raise ConnectionError(
            'the endpoint did not answer a vector for %r' % (text,))


@pytest.fixture
def journey(tmp_path, monkeypatch):
    """A ``~/.imasviz`` of the journey, the documents corpus folder, and a
    core with no LLM and the table embedder in place of the one under a
    llama-server (the endpoint the preferences name, so the run vectors)."""
    os.environ['HOME'] = str(tmp_path)
    docs_dir = os.path.join(str(tmp_path), 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    shared = os.path.join(str(tmp_path), 'shared-journal')
    os.makedirs(shared, exist_ok=True)

    from imasviz.VizUtils import QVizPreferences
    monkeypatch.setattr(QVizPreferences, 'SharedJournalDir', shared,
                        raising=False)
    monkeypatch.setattr(QVizPreferences, 'AgentDocsDir', docs_dir,
                        raising=False)
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedEndpoint',
                        'http://127.0.0.1:8081/v1', raising=False)
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedModel', 'test-embed',
                        raising=False)

    monkeypatch.setattr(agent, 'LLM_CLIENT', None, raising=False)
    monkeypatch.setattr(llm, 'EmbeddingClient', lambda: TableEmbedder(),
                        raising=False)
    api = core.McpGuiCore()
    return {'api': api, 'docs_dir': docs_dir}


def test_the_note_is_indexed_before_the_search_is_asked(journey):
    """The one the user asked for, end to end: a note the journey adds is in
    the index the same turn it is on the disk, and the search asked after
    is the one the index answers (not a read the run builds on the fly).
    The write and the read are the two the user does not have to pay
    together — the note is found the moment it is added."""
    api = journey['api']
    out = api.add_note('personal', 'The plasma came unstable after 0.4 s of '
                       'heating; we lowered the current ramp and it stayed '
                       'stable.', author=AUTHOR,
                       machine='WEST', shot=54924, title='Plasma tuning')
    assert out.get('id')
    # The search right after: the index answers (indexed), and the note is
    # the one it ranks first on the words the writer just wrote.
    res = api.search_journals(query='plasma unstable current ramp')
    assert res['indexed'] is True, \
        'a note added before the search is in the index: %r' % res
    assert res['notes'][0]['id'] == out['id'], res
    # The eager write put it in the store: the stats hold the one row.
    assert api.journal_stats()['indexes']['personal']['rows'] == 1


def test_the_corpus_is_found_the_moment_it_is_indexed(journey):
    """The documents the user drops in the corpus folder are read by
    ``reindex_documents`` and ranked by ``search_documents``: the journey
    writes a markdown and a text, indexes the corpus, and the two searches
    each answer their own document (the one that names it, by its words —
    the hybrid the two lists fuse)."""
    api = journey['api']
    docs_dir = journey['docs_dir']
    with open(os.path.join(docs_dir, 'tuning.md'), 'w') as f:
        f.write('# Plasma tuning\n\nThe plasma came unstable after 0.4 s of '
                'heating. We lowered the current ramp and it stayed '
                'stable. Shot 54924.\n')
    with open(os.path.join(docs_dir, 'probe.txt'), 'w') as f:
        f.write('The probe calibration was off by a factor of two after the '
                'heater was re-wired.\n')
    # Before indexing, the corpus is empty (a search answers nothing, and
    # the stats hold no rows).
    assert api.search_documents('plasma unstable')['hits'] == []
    # The journey indexes the corpus (the user drops the documents and
    # asks the agent to reindex).
    out = api.reindex_documents()
    assert out['documents'] == 2, out
    assert out['embedder_named'] is True, \
        'the endpoint is named, so the run vectorized this pass'
    # The two searches each answer their own document, by its words.
    plasma = api.search_documents('plasma unstable current ramp')
    assert plasma['hits'] and plasma['hits'][0]['rel'] == 'tuning.md', plasma
    probe = api.search_documents('probe calibration heater')
    assert probe['hits'] and probe['hits'][0]['rel'] == 'probe.txt', probe
    # And read_document gives the full text of the one a search hit names.
    text = api.read_document('tuning.md')['text']
    assert 'plasma' in text.lower()


def test_a_guarded_corpus_is_named_and_set_right(journey, monkeypatch):
    """The guard, end to end: the corpus written under an embedding endpoint
    the run is no longer under answers ``guarded`` and the keyword alone
    stands (the vector lists are in a different space), the reason names
    the embedder, and ``reindex_documents`` is the one that sets the two in
    step (after which the same search ranks with the vectors)."""
    api = journey['api']
    docs_dir = journey['docs_dir']
    with open(os.path.join(docs_dir, 'tuning.md'), 'w') as f:
        f.write('# Plasma tuning\n\nThe plasma came unstable after 0.4 s '
                'of heating. We lowered the current ramp and it stayed stable.\n')
    # Index under test-embed (the journey's endpoint).
    assert api.reindex_documents()['documents'] == 1
    # Move the run to another model: the stored sig is not the run's.
    from imasviz.VizUtils import QVizPreferences
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedModel', 'another-model',
                        raising=False)
    guarded = api.search_documents('plasma unstable')
    assert guarded['guarded'] is True, \
        'a corpus under a different embedder is named: %r' % guarded
    assert guarded['method'] == 'keyword', \
        'the vectors are ignored, the keyword stands: %r' % guarded
    assert 'embedder' in guarded['guard_reason'].lower()
    # Still found (the keyword reads the same text): the refusal is the
    # method and the reason, not the absence of the hit.
    assert guarded['hits'] and guarded['hits'][0]['rel'] == 'tuning.md'
    # The reindex sets the two in step (the next pass embeds under the new
    # sig), and the search is no longer guarded.
    api.reindex_documents()
    settled = api.search_documents('plasma unstable')
    # No longer guarded (the reindex embedded under the run's own sig): the
    # `guarded` flag is simply absent, and the run ranks with the vectors
    # (the hybrid, both lists).
    assert settled.get('guarded') is not True, \
        'the reindex set the corpus in step with the run: %r' % settled
    assert settled.get('method') in ('hybrid', 'embeddings'), settled


def test_a_corpus_with_no_folder_is_a_refusal(monkeypatch):
    """A corpus the run cannot read (no folder named) is the named refusal
    the caller reads — ``list_documents``, ``search_documents`` and
    ``read_document`` each say it (the same shape the shared journal answers
    for its folder), not a crash and not a zero it would read as "no
    document"."""
    from imasviz.VizUtils import QVizPreferences
    monkeypatch.setattr(QVizPreferences, 'AgentDocsDir', '', raising=False)
    api = core.McpGuiCore()
    with pytest.raises(ValueError):
        api.list_documents()
    with pytest.raises(ValueError):
        api.search_documents('plasma')
    with pytest.raises(ValueError):
        api.read_document('tuning.md')


def test_documents_stats_names_the_corpus_the_journey_holds(journey):
    """The one a reader asks ("can the agent read my documents?"): how many
    documents and chunks the corpus holds, its ``embed_sig`` and ``dim``,
    and how long the read is. The journey indexed one document, so the stats
    hold it and the run's embedder signature."""
    api = journey['api']
    docs_dir = journey['docs_dir']
    with open(os.path.join(docs_dir, 'tuning.md'), 'w') as f:
        f.write('# Plasma tuning\n\nThe plasma came unstable after 0.4 s of '
                'heating.\n')
    api.reindex_documents()
    s = api.documents_stats()
    assert s['documents'] == 1, s
    assert 'embed_sig' in s
    # And the embeddings the preferences name (the two the search asks of)
    # are the ones the stats hold.
    assert s['embed_sig'], 'the stats name the embedder the corpus ran under'
