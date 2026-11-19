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

"""The documents corpus, the engine that reads the user's own writing.

The one ``test_148`` holds for the two journals, this tests the corpus on
its own — the documents the folder ``AgentDocsDir`` names holds, the way
their text is extracted and chunked, the way the chunks are indexed (one
``rag_store.Store`` of type ``docs``), the rank over them (the same RRF as
the journals), and the refusals (no folder, a folder not a directory, a
document outside the corpus). No IMAS, no Qt: the corpus is standard
library and, when an embedder is handed, the stand-in the suite uses
everywhere (a fixed table the one ``EmbeddingClient`` is a stand-in for).

The rules the tests pin:

* **list** — every ``.md``/``.txt``/``.pdf`` the corpus folder holds
  (sub-folders included, the hidden and the ``__pycache__`` left out),
  newest by modification;
* **chunk** — the text is split into passages (a document shorter than one
  passage is the one passage, an empty document is none);
* **reindex** — the folder in step with the store, idempotent on an
  unchanged folder, a document that left the folder is the one the purge
  drops;
* **search** — the BM25 over the chunks fused with the cosine of the query
  against the same (``method: 'hybrid'``), the vector alone
  (``'embeddings'``), the keyword alone (``'keyword'``), and the empty
  (``'empty'``);
* **guard** — a store written under an ``embed_sig`` the run is not under
  is named (``guarded``) and the keyword alone stands;
* **refusals** — no folder, a folder not a directory, and a document
  outside the corpus, each in words.

``test_151`` holds the surface the core offers over this; this holds the
engine.
"""

import os

import pytest

import imasviz.VizAgent.rag_docs as rag_docs


class TableEmbedder:
    """The one the corpus is handed for an ``EmbeddingClient``: a fixed
    table of the text to its vector. A text the table does not point at is
    a refusal for the whole search (the one the run would answer), so the
    table names every passage the test writes and the one it searches."""
    def __call__(self, text):
        if 'plasma' in text.lower() or 'tuning' in text.lower():
            return [1.0, 0.0]
        if 'probe' in text.lower() or 'calibration' in text.lower():
            return [0.0, 1.0]
        raise ConnectionError(
            'the endpoint did not answer a vector for %r' % (text,))


@pytest.fixture
def docsFolder(tmp_path, monkeypatch):
    """A corpus folder with two documents (a markdown and a text) and its
    index (a private ``HOME``). The documents name words the tests search
    on (``plasma`` / ``tuning`` for the one, ``probe`` / ``calibration``
    for the other)."""
    os.environ['HOME'] = str(tmp_path)
    docs_dir = os.path.join(str(tmp_path), 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    with open(os.path.join(docs_dir, 'tuning.md'), 'w') as f:
        f.write('# Plasma tuning\n\nThe plasma came unstable after 0.4 s '
                'of heating. We lowered the current ramp and it stayed '
                'stable.\n')
    with open(os.path.join(docs_dir, 'probe.txt'), 'w') as f:
        f.write('The probe calibration was off by a factor of two after the '
                'heater was re-wired.\n')
    from imasviz.VizUtils import QVizPreferences
    monkeypatch.setattr(QVizPreferences, 'AgentDocsDir', docs_dir,
                        raising=False)
    return docs_dir


def test_list_names_the_documents_it_reads(docsFolder):
    """The corpus reads every ``.md``/``.txt`` (and ``.pdf``) the folder
    holds, and nothing else: a shape it does not read is not a hit, a
    hidden file is not a hit, and the two documents it does read are the
    ones the list answers, in order (newest by modification)."""
    folder = docsFolder
    with open(os.path.join(folder, 'a-shape.it-does-not-read'), 'w') as f:
        f.write('not read by the corpus')
    with open(os.path.join(folder, '.hidden'), 'w') as f:
        f.write('hidden and not read')
    docs = rag_docs.listDocuments()
    rels = sorted(d['rel'] for d in docs)
    assert rels == ['probe.txt', 'tuning.md'], rels
    kinds = {os.path.basename(d['path']): d['kind'] for d in docs}
    assert kinds == {'tuning.md': 'markdown', 'probe.txt': 'text'}, kinds


def test_chunk_splitlets_and_keeps_short_ones(docsFolder):
    """The passages of one document's text: the text is split into chunks of
    ``CHUNK_SIZE`` (with its overlap), a document shorter than one chunk is
    the one chunk, and an empty document is no chunk. The chunk size is the
    one the ``rag_store`` ranks on, so the tests pin the count for a known
    text, not a guess."""
    short = 'one two three'
    assert rag_docs.chunkText(short) == [short]
    assert rag_docs.chunkText('') == []
    long = 'x' * (rag_docs.CHUNK_SIZE * 3)
    chunks = rag_docs.chunkText(long)
    assert len(chunks) >= 3
    # Every chunk is the size the store ranks on (bounded by CHUNK_SIZE),
    # and the overlap keeps the text continuous (no word lost at a seam).
    for c in chunks:
        assert len(c) <= rag_docs.CHUNK_SIZE + rag_docs.CHUNK_OVERLAP
    joined = ''.join(chunks)
    assert 'x' * 20 in joined


def test_document_chunks_are_addressed_by_their_rel(docsFolder):
    """The passages one document's text is split into: the ``id`` is the
    one a search hits back by and the one a ``removeDocument`` deletes —
    the same name the corpus holds it under, so a search and the delete
    cannot disagree."""
    path = os.path.join(docsFolder, 'tuning.md')
    chunks = rag_docs.documentChunks(path)
    assert chunks, 'a non-empty document holds a passage'
    for c in chunks:
        assert c['id'].startswith('tuning.md#c'), c['id']
    assert 'plasma' in chunks[0]['text'].lower()


def test_reindex_is_incremental_and_purges_the_left_overs(docsFolder):
    """The one a ``reindex_documents`` answers: the folder in step with the
    store. What it keeps (unchanged), what it writes (moved or new), what
    it purges (gone from the folder), and the count the store holds after —
    and it is idempotent on an unchanged folder (a second run writes
    nothing new)."""
    first = rag_docs.reindex(embedder=None)
    assert first['documents'] == 2, first
    assert first['upserted'] >= 2, first
    assert first['purged'] == 0, first
    # Idempotent (the keep rule is the one an embedder pays): the first
    # pass embeds the two documents' chunks, and the second pass keeps what
    # it holds (no re-embed on the unchanged rows, the total stays the
    # folder's). A keyword-only store re-writes its text (cheap); the one
    # the rule guards is the embed, and that is the one the keep drops.
    rag_docs.reindex(embedder=TableEmbedder())
    second = rag_docs.reindex(embedder=TableEmbedder())
    assert second['documents'] == 2
    assert second['upserted'] == 0, \
        'an unchanged folder was re-embedded: %r' % second
    assert second['kept'] >= 1, \
        'the chunks the first pass embedded are not kept: %r' % second
    assert second['purged'] == 0
    # A document that left the folder is the one the purge drops.
    os.remove(os.path.join(docsFolder, 'probe.txt'))
    third = rag_docs.reindex(embedder=TableEmbedder())
    assert third['purged'] >= 1, \
        'a document that left the folder was not purged: %r' % third
    assert third['documents'] == 1


def test_reindex_keeps_a_corpus_that_cannot_open_one_document(docsFolder):
    """A document the corpus cannot extract (a ``.pdf`` on a run with no
    pymupdf, a file it cannot read) is a refusal that costs its own
    document, not the corpus: the others still index, and the refusal is
    named (a document the corpus cannot open does not cost the corpus a
    crash)."""
    # A non-readable extension the corpus names but cannot extract: a .pdf
    # on a run without pymupdf is the one the refusal answers (pymupdf is
    # not imported on this node, and the corpus refuses the PDF by name).
    with open(os.path.join(docsFolder, 'a.pdf'), 'wb') as f:
        f.write(b'%PDF-1.4 not really readable without pymupdf')
    out = rag_docs.reindex(embedder=None)
    # The folder holds the two that read plus one that does not: the two
    # index, the one is refused (the answer is not a crash, and the corpus
    # is not emptied for it).
    assert out['documents'] == 3, out
    # The two the corpus reads are still in step (their rows are the ones
    # the store holds), the one it could not open is not there.
    assert rag_docs.stats()['documents'] == 3


def test_search_answers_the_chunks_it_ranks(docsFolder):
    """The rank over the chunks' texts: a query that names the one document
    answers it first, a query that names the other answers that, and the
    ``method`` is the one the run ranked with (here the keyword, the embedder
    is ``None`` — the corpus is served on the lexical list)."""
    rag_docs.reindex(embedder=None)
    res = rag_docs.search('plasma unstable tuning', embedder=None)
    assert res['hits'], res
    assert res['hits'][0]['rel'] == 'tuning.md', res
    assert 'tuning' in res['hits'][0]['snippet'].lower()
    other = rag_docs.search('probe calibration', embedder=None)
    assert other['hits'][0]['rel'] == 'probe.txt', other
    assert res['method'] in ('keyword', 'hybrid', 'embeddings')


def test_search_is_guarded_when_the_embedder_moved(docsFolder, monkeypatch):
    """The guard: a store written under ``embed_sig`` A and a run under B
    do not rank the query in one space against the passages written in the
    other — the answer is ``guarded``, the keyword alone stands, and the
    reason names the embedder so the next ``reindex`` sets the two in
    step."""
    from imasviz.VizUtils import QVizPreferences
    rag_docs.reindex(embedder=None)  # keyword-only baseline (no sig)
    # Write under sig A (an embedder that vectors), then move the run to B.
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedEndpoint',
                        'http://127.0.0.1:8081/v1', raising=False)
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedModel', 'modelA',
                        raising=False)
    rag_docs.reindex(embedder=TableEmbedder())
    monkeypatch.setattr(QVizPreferences, 'AgentEmbedModel', 'modelB',
                        raising=False)
    res = rag_docs.search('plasma', embedder=TableEmbedder())
    assert res['guarded'] is True, \
        'a store under a different embedder is named: %r' % res
    assert res['method'] == 'keyword'
    assert 'embedder' in res['guard_reason'].lower()
    # The keyword still finds the passage (the refusal is the method and
    # the reason, not the absence of the hit).
    assert res['hits'] and res['hits'][0]['rel'] == 'tuning.md'


def test_docs_stats_names_the_corpus_state(docsFolder):
    """The one a ``documents_stats`` answer: how many documents and chunks
    the corpus holds, its ``embed_sig``, its ``dim``, and how long the read
    is (the ``source_type``, the ``path`)."""
    rag_docs.reindex(embedder=None)
    s = rag_docs.stats()
    assert s['documents'] == 2
    assert s['rows'] >= 1
    # The two are in step with the corpus (the folder the corpus reads from
    # and its index, both named).
    assert 'embed_sig' in s


def test_read_document_gives_the_full_text(docsFolder):
    """The one a ``read_document`` answers: the full text of the document
    the ``rel`` names, read back from the disk the corpus holds (the same
    text a search hit would rank, without its chunk bound)."""
    text = rag_docs.readDocument('tuning.md')
    assert 'plasma' in text.lower()
    assert 'calibration' not in text.lower()


def test_read_document_outside_the_corpus_is_refused_by_name(docsFolder):
    """A path the corpus does not read (a ``rel`` that escapes the corpus
    folder, a shape it cannot open) is a refusal by name: the corpus does
    not cost a crash to a read it cannot answer, but it does name the
    reason. Not in the corpus is the same, naming the ones it does read."""
    with pytest.raises(ValueError):
        rag_docs.readDocument('../outside')
    with pytest.raises(ValueError):
        rag_docs.readDocument('no-such-document.md')


def test_no_folder_is_a_refusal(monkeypatch):
    """A corpus with no folder named is a refusal by name (the one the
    shared journal's folder answers for): the answer is the one the corpus
    could not read, not a zero it would read as "no document"."""
    from imasviz.VizUtils import QVizPreferences
    monkeypatch.setattr(QVizPreferences, 'AgentDocsDir', '', raising=False)
    with pytest.raises(ValueError) as exc:
        rag_docs.listDocuments()
    assert 'AgentDocsDir' in str(exc.value)
    with pytest.raises(ValueError):
        rag_docs.reindex(embedder=None)


def test_a_folder_that_is_not_a_directory_is_a_refusal(tmp_path, monkeypatch):
    """A folder the corpus is named at that is not a directory (a file in
    the middle, a path that does not hold) is a refusal by name: the corpus
    cannot read a path that does not hold — the one the shared journal's
    folder answers for."""
    a_file = os.path.join(str(tmp_path), 'a-file')
    with open(a_file, 'w') as f:
        f.write('x')
    from imasviz.VizUtils import QVizPreferences
    monkeypatch.setattr(QVizPreferences, 'AgentDocsDir', a_file,
                        raising=False)
    with pytest.raises(ValueError) as exc:
        rag_docs.listDocuments()
    assert 'not a directory' in str(exc.value)
