# Copyright holders : Commissariat à l'Energie Atomique et auxnergies
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

"""The documents corpus: one ``rag_store.Store`` of the user's own writing.

The one the two journals do not hold. The user's documents — the markdown
and text files, and the PDFs when pymupdf is importable — sit in the folder
``QVizPreferences.AgentDocsDir`` names (an empty name is a refusal by name,
the same rule the shared journal answers for its folder). The corpus reads
that folder, extracts the text of each document (``.md`` and ``.txt`` are
read as UTF-8, a ``.pdf`` is extracted through pymupdf), chunks it into
passages (the one size the ``rag_store`` ranks on, the ``rrfK`` fusion is
over the chunks' texts), and indexes the chunks into one store under
``~/.imasviz/docs-index.sqlite`` (``source_type: 'docs'``).

The store is the ``rag_store`` the two journals already carry — the same
engine, the same ``embed_sig`` guard, the same incremental rule (a document
whose text has not moved is a keep, not a re-embed — the ``reindex`` walks
the folder, and a document that leaves the folder is the one the ``purge``
drops). So the surface the core offers is the same three: ``reindex`` (the
folder in step with the store, the one the user runs on adding a document
or changing the endpoint), ``search`` (the rank over the chunks' texts,
the same ``method``/``guarded`` the journals answer), and ``stats`` (how
many documents, how many chunks, its ``embed_sig``, its ``dim``, and when
it was built).
"""

import os

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def docsDirectory():
    """The folder the documents corpus reads from (the one the preferences
    name). Empty is a refusal by name — the same shape the shared journal's
    folder answers for (no folder to sit in until this is set) — and that is
    what a ``readDirectory`` of the whole corpus is, not a zero it would
    read as "no document"."""
    from imasviz.VizUtils import QVizPreferences
    path = (QVizPreferences.AgentDocsDir or '').strip()
    if not path:
        raise ValueError(
            'The documents corpus has no folder named: set AgentDocsDir in '
            '~/.imasviz/preferences to point it at the folder that holds '
            'the documents you want the in-app agent to read (the journals '
            'still answer — the corpus is simply not in step until this is '
            'set).')
    if not os.path.isdir(path):
        raise ValueError(
            '"%s" is the folder the documents corpus is named at, and it '
            'is not a directory: the corpus cannot read a path that does '
            'not hold — point AgentDocsDir at a folder.' % path)
    return path


def docsPath(path):
    """The one document the corpus holds, resolved absolute (its name in
    the folder, the one a search hits back by its ``rel``)."""
    return os.path.abspath(path)


def storePath():
    """The one file the documents store sits under (a sibling of the notes
    folders, ``~/.imasviz/docs-index.sqlite``)."""
    home = os.environ.get('HOME')
    if not home:
        raise ValueError(
            'No HOME in the environment: the documents corpus has no folder '
            'for its store to sit under.')
    folder = os.path.join(home, '.imasviz')
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, 'docs-index.sqlite')


def store():
    """The one ``rag_store.Store`` the documents corpus carries, opened in
    the file ``storePath`` names (a ``docs`` store, not a ``journal`` one —
    the ``stats`` the reader answers hold the type, and the guard the
    ``embed_sig`` applies is the one the run is under).
    """
    from imasviz.VizAgent import rag_store
    return rag_store.Store.open(storePath(), 'docs')


def kindOf(path):
    """The one of its extension the corpus reads as: ``.md``/``.txt`` are
    read as UTF-8, ``.pdf`` is extracted through pymupdf (a name it does not
    hold is a refusal the corpus does not read — the corpus does not hold a
    shape it cannot extract)."""
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.md', '.markdown'):
        return 'markdown'
    if ext in ('.txt', '.text'):
        return 'text'
    if ext == '.pdf':
        return 'pdf'
    return None


def listDocuments():
    """The documents the corpus reads: every ``.md``/``.txt``/``.pdf`` the
    corpus's folder holds (the sub-folders included, the ``.hidden`` and
    ``__pycache__`` left out), newest by modification (the one a reader
    expects in a list), the one each holds (its name, its size, its mtime,
    and its ``rel`` the search answers by)."""
    import time
    folder = docsDirectory()
    docs = []
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [d for d in dirnames
                       if not d.startswith('.') and d != '__pycache__']
        for fname in filenames:
            if fname.startswith('.') or fname.startswith('~'):
                continue
            kind = kindOf(fname)
            if kind is None:
                continue
            path = os.path.abspath(os.path.join(dirpath, fname))
            full = docsPath(path)
            try:
                stat = os.stat(full)
            except OSError:
                continue
            rel = os.path.relpath(full, folder)
            docs.append({
                'path': full,
                'rel': rel.replace(os.sep, '/'),
                'kind': kind,
                'size': stat.st_size,
                'mtime': int(stat.st_mtime),
                'modified': time.strftime('%Y-%m-%d',
                                          time.localtime(stat.st_mtime)),
            })
    docs.sort(key=lambda d: (-d['mtime'], d['rel']))
    return docs


def extractText(path):
    """The text of one document, whether it is a file the corpus reads as
    (``.md``/``.txt``) or a PDF it extracts through pymupdf. A format the
    corpus does not read is a refusal by name (the corpus does not hold a
    shape it cannot extract), and an unreadable file is the same — the
    corpus does not cost a crash to a document it cannot open, but it does
    name the reason."""
    kind = kindOf(path)
    if kind in ('markdown', 'text'):
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    if kind == 'pdf':
        try:
            import fitz  # pymupdf
        except ImportError:
            raise ValueError(
                '"%s" is a PDF and pymupdf (import fitz) is not imported '
                'on this run: the corpus cannot extract a PDF without it — '
                'either remove the PDF from the corpus folder, or import '
                'pymupdf (``pip install pymupdf``) and reindex.' % path)
        doc = fitz.open(path)
        try:
            return '\n'.join(page.get_text() for page in doc)
        finally:
            doc.close()
    raise ValueError(
        '"%s" is not a format the documents corpus reads: it holds '
        '.md/.txt (UTF-8) and .pdf (through pymupdf) — a shape it does not '
        'hold is not one the corpus would cost a crash for.' % path)


def chunkText(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """The passages of one document's text: the run splits them, the
    ``rag_store`` ranks them (the ``rrfK`` fusion is over the chunks'
    texts, and a search that hits a chunk is the one the reader sees). A
    document shorter than one passage is the one passage, and an empty
    document is no passage (a document the corpus cannot extract is a
    refusal the read answers, not a line it would not hold)."""
    text = (text or '').strip()
    if not text:
        return []
    size = max(80, int(size))
    overlap = max(0, min(int(overlap), size - 1))
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def documentChunks(path, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """The passages one document's text is split into (the ``id`` is the
    one a search hits back by, the one a ``removeDocument`` deletes — the
    same name the corpus holds it under, so a search and the delete agree)."""
    rel = os.path.basename(path)
    text = extractText(path)
    chunks = chunkText(text, size, overlap)
    return [{'id': '%s#c%d' % (rel, i), 'text': chunk}
            for i, chunk in enumerate(chunks)]


def upsertDocument(path, embedder=None, size=CHUNK_SIZE,
                   overlap=CHUNK_OVERLAP):
    """The one document of the corpus, in step: the chunks are upserted
    (each re-embedded only when its text moved, or a keep), and the store
    is the one the corpus holds it under. The ``embedder`` is the callable
    the run answers (the ``EmbeddingClient`` when the endpoint is named,
    ``None`` for a corpus the lexical list alone serves — the text is in
    step, and a later reindex under a named endpoint is the one that
    vectors it)."""
    rel = os.path.basename(path)
    chunks = documentChunks(path, size, overlap)
    if not chunks:
        # A document the corpus cannot extract is a refusal the caller
        # reads as "the document is not there", not a crash and not a
        # chunk it would not hold — the corpus does not cost a crash.
        raise ValueError(
            '"%s" is a document the corpus cannot extract into a passage '
            '(the corpus does not hold an empty document): the read does '
            'not pretend it answered when it did not.' % rel)
    s = store()
    upserted = 0
    try:
        for c in chunks:
            out = s.upsert(
                c['id'], c['text'],
                meta={
                    'doc': 'docs',
                    'rel': rel,
                    'chunk': int(c['id'].rsplit('#c', 1)[-1]
                                 if '#c' in c['id'] else 0),
                    'kind': kindOf(path) or 'text',
                },
                embedder=embedder)
            if out.get('upserted'):
                upserted += 1
        return {'document': rel, 'chunks': len(chunks),
                'upserted': upserted}
    finally:
        s.close()


def removeDocument(path):
    """The one document of the corpus, gone: its chunks leave the store. A
    document the corpus never held is the no-op the ``rag_store`` answers
    (its file is already off the disk the corpus holds)."""
    rel = os.path.basename(path)
    prefix = rel + '#c'
    s = store()
    removed = 0
    try:
        for rid in s.keys():
            if rid.startswith(prefix):
                s.remove(rid)
                removed += 1
        return {'document': rel, 'removed': removed}
    finally:
        s.close()


def reindex(embedder=None):
    """The whole corpus, in step with the store: the one a
    ``reindex_documents`` runs.

    Walks the documents the corpus's folder holds (its ``listDocuments`` is
    the disk the corpus reads, the one the run trusts), upserts each into
    the store (re-embedding only what moved, under the ``embedder`` the run
    answers), and purges the rows the store holds that the corpus no longer
    holds (a document that left the folder, the one it edited off). A
    corpus the run cannot read (no folder named, the folder not a directory)
    is a refusal by name and does not cost a partial store, and a corpus that
    holds no document is not purged (an empty source is not an ask to take
    the store's rows away — the one a writer emptied on one side is the one
    the other still reads).

    ``embedder`` is the one the run answers (the ``EmbeddingClient`` when the
    endpoint is named, ``None`` for a corpus the lexical list alone serves —
    the text is in step, and a later reindex under a named endpoint is the
    one that vectors it).
    """
    import logging
    # A corpus the run cannot read (no folder named, the folder not a
    # directory) is the named refusal the caller reads — ``listDocuments``
    # raises it, and it is not caught here, because a store's reindex
    # would purge on the empty read and wipe the corpus the writers hold.
    docs = listDocuments()
    if not docs:
        # A corpus that holds no document is not an ask to purge the store:
        # a corpus the writer emptied on one side is the one the other
        # still reads, and a reindex that took its rows away on an empty
        # list would be the silent wipe this refuses.
        logging.getLogger('logPanel').info(
            'the documents corpus holds no document; the store is kept as '
            'it was (an empty source is not an ask to empty it).')
        return {'documents': 0, 'chunks': 0, 'upserted': 0, 'kept': 0,
                'purged': 0, 'skipped_empty': True}
    records = []
    for doc in docs:
        try:
            for c in documentChunks(doc['path']):
                rel = doc['rel']
                records.append({
                    'id': c['id'],
                    'text': c['text'],
                    'meta': {
                        'doc': 'docs',
                        'rel': rel,
                        'chunk': int(c['id'].rsplit('#c', 1)[-1]
                                     if '#c' in c['id'] else 0),
                        'kind': doc['kind'],
                    },
                })
        except ValueError as e:
            # A document the corpus cannot extract is a refusal that costs
            # its own document, not the corpus: the others still index, and
            # the reason is named.
            logging.getLogger('logPanel').info(
                'the document %s could not be indexed: %s'
                % (doc['rel'], e))
            continue
    s = store()
    try:
        out = s.reindex(records, embedder=embedder)
    finally:
        s.close()
    out['documents'] = len(docs)
    return out


def search(query, embedder=None, limit=8):
    """The corpus's rank: the one a ``search_documents`` asks of. The BM25
    over the chunks' texts fused with the cosine of the query against the
    same (the ``rag_store``'s RRF), the chunks a document's text is split
    into. A store the run cannot read (no folder) is a refusal by name, and
    a search that hits no chunk is the ``empty`` the answer holds (not a
    crash, not a guess)."
    The answer holds the ``hits`` — one per chunk, the one the reader sees
    (the document's ``rel``, the chunk's index, a snippet of its text), the
    ``method`` (``hybrid``/``embeddings``/``keyword``/``empty``), and the
    ``guarded`` flag when a store's ``embed_sig`` is not the one the run is
    under (its vectors were ignored, the keyword stands, and the
    ``guard_reason`` names it) — the same fields the single-store
    ``rag_store.search`` answers, so the caller reads the two the same way.
    """
    # A corpus the run cannot read (no folder named, the folder not a
    # directory) is the named refusal the caller reads, before the store
    # is asked of at all (a search on a stale store would answer the
    # corpus the folder no longer holds, and that is the guess this
    # refuses).
    docsDirectory()
    embedder = _noteEmbedderLike(embedder)
    query = (str(query).strip() if query else '')
    if not query:
        return {'hits': [], 'total': 0, 'method': 'empty', 'query': ''}
    s = store()
    r = s.search(query, embedder=embedder, limit=limit)
    # Read the hit chunks' text for a snippet while the store is still open
    # (``s`` is the open store; ``store`` is the module function that
    # opened it — the two share a name, and this line is the object).
    snippets = {}
    for chunk_id in r.get('note_ids', []):
        text = s.rowOf(chunk_id)
        if text:
            snippets[chunk_id] = (text[:160] + '…') if len(text) > 160 \
                else text
    s.close()
    hits = []
    for chunk_id in r.get('note_ids', []):
        rel, _, idx = chunk_id.rpartition('#c')
        hits.append({
            'rel': rel,
            'chunk': int(idx) if idx.isdigit() else 0,
            'snippet': snippets.get(chunk_id, ''),
        })
    out = {
        'query': query,
        'hits': hits,
        'total': r.get('total', 0),
        'method': r.get('method', 'empty'),
    }
    if r.get('guard_reason'):
        out['guarded'] = True
        out['guard_reason'] = r['guard_reason']
    elif r.get('guarded'):
        out['guarded'] = True
    return out


def _noteEmbedderLike(embedder):
    """The one the run answers for the corpus (the same shape the journals'
    ``core._noteEmbedder`` holds, but a module-level function, because the
    run's embedder is asked of the preferences the corpus is named under).
    A store the run cannot vector (the endpoint not named) is ``None`` —
    the corpus is served on the keyword alone."""
    if embedder is not None:
        return embedder
    from imasviz.VizUtils import QVizPreferences
    endpoint = (QVizPreferences.AgentEmbedEndpoint or '').strip()
    if not endpoint:
        return None
    from imasviz.VizAgent.llm_client import EmbeddingClient
    return EmbeddingClient()


def stats():
    """The state of the corpus: how many documents and chunks it holds, its
    ``source_type``, its ``embed_sig`` and ``dim``, and its ``built_at``.
    A corpus the run cannot read (no folder) answers the ``refusal`` the
    caller reads as the one the index could not open, not a zero it would
    read as empty."""
    s = store()
    try:
        out = s.stats()
    finally:
        s.close()
    try:
        docs = listDocuments()
        out['documents'] = len(docs)
    except ValueError as e:
        out['refusal'] = str(e)
        out['documents'] = 0
    return out


def readDocument(rel):
    """The full text of one document of the corpus, by its ``rel`` (the one
    a search hits back by). Not in the corpus is a refusal by name, naming
    the ones it does; a document it does not read is the same — the corpus
    does not cost a crash to a read it cannot answer, but it does name the
    reason."""
    folder = docsDirectory()
    full = os.path.abspath(os.path.join(folder, rel))
    if not full.startswith(os.path.abspath(folder) + os.sep):
        raise ValueError(
            '"%s" is not a document the corpus reads: the path it names is '
            'not under the corpus folder, and the corpus does not read a '
            'path outside it.' % rel)
    if not os.path.isfile(full):
        docs = [d['rel'] for d in listDocuments()]
        raise ValueError(
            '"%s" is not in the documents corpus. The corpus reads: %s'
            % (rel, ', '.join(docs[:20]) if docs else 'no document'))
    return extractText(full)


def docsEmbedder():
    """The ``EmbeddingClient`` the corpus runs under (the one the
    preferences name, or ``None`` — the corpus served on the keyword alone).
    A module-level function the core asks of, so a test can monkeypatch it
    for a table stand-in (the same shape ``core._noteEmbedder`` holds, but
    for the documents corpus)."""
    from imasviz.VizUtils import QVizPreferences
    endpoint = (QVizPreferences.AgentEmbedEndpoint or '').strip()
    if not endpoint:
        return None
    from imasviz.VizAgent.llm_client import EmbeddingClient
    return EmbeddingClient()
