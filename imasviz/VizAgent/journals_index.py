# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The two journals' indexes: one ``rag_store.Store`` under each journal.

The decision the user made — **one SQLite per journal** — is answered here:
the personal one sits under ``~/.imasviz`` (a sibling of the notes folder,
``journal-index.sqlite``), and the shared one under the folder
``QVizPreferences.SharedJournalDir`` names (``journal-index.sqlite`` in it).
This module owns **where** the two live and the small glue that spans them
(a ``scope=None`` search is the two stores, fused), and the notes' text is
what it indexes: the composition of the title, the filters, and the body
(one string the lexical list ranks on, the one the embedder vectors).

The ``journals`` store is untouched: it is the file the writers hold. This
index is the one derived artifact the run adds to it, and it is the one the
search ranks with — the eager one ``add_note`` / ``edit_note`` /
``delete_note`` and ``reindex_journals`` keep in step with it. A store the
run cannot open (the shared one, no folder named) is a refusal by name,
and a search that spans both keeps the one that answers.

A note written or edited outside the run (direct ``JournalStore`` calls)
is not in step with this index: the search answers ``staleIds`` a one-
line check (does the row's stored text hash answer the one the disk
holds?), and a note it names costs one incremental ``reindex`` before the
rank — a note the index holds moved costs one embed, a note the index
does not hold costs the upsert of its text, and a row that holds a
vector the endpoint no longer serves is re-vectorized on the next search
under the same signature or kept.
"""

import os

from imasviz.VizAgent.rag_store import _fuseRRF, hashText


def _personalPath():
    """The personal index: the one sibling of the notes folder it serves.

    ``~/.imasviz/journals`` is the notes (the ``journals`` store answers it);
    the index sits one level up at ``~/.imasviz/journal-index.sqlite``, so it
    is the one the ``journals`` store owns the folder for and the run writes
    it to, not a file in the middle of the notes a reader of the journal
    would not expect."""
    from imasviz.VizAgent import journals
    folder = journals.JournalStore.personalDirectory()
    return os.path.join(os.path.dirname(folder), 'journal-index.sqlite')


def _sharedPath():
    """The shared index: the one under the folder ``SharedJournalDir``
    names (a refusal by name when that is not set — the same rule the
    ``journals`` store refuses the shared journal for)."""
    from imasviz.VizAgent import journals
    folder = journals.JournalStore.sharedDirectory()
    return os.path.join(folder, 'journal-index.sqlite')


def indexPathFor(scope):
    """The one file the index of the journal ``scope`` sits under."""
    if scope == 'personal':
        return _personalPath()
    if scope == 'shared':
        return _sharedPath()
    raise ValueError(
        '"scope=%r" is not a journal: its two are personal and '
        'shared.' % scope)


def _f(obj, key, default=None):
    """One field of a note, whether it is the ``journals`` note (attributes)
    or the ``add_note`` / ``edit_note`` answer (a dict, the keys the same
    names) — the one ``upsertNote`` reads, so a write the run answers on a
    dict and a list the run answers on an object index the same way."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def noteText(note):
    """The one string a note is indexed under: the title, the filters it
    names, and the body — in that order, the words a reader types first and
    the meaning it holds last. A field the note does not name is not a word
    the text holds (a ``machine:`` the note left out is not in the answer a
    search ranks on, the same rule the structured filter applies)."""
    parts = [_f(note, 'title'), _f(note, 'machine'), _f(note, 'campaign'),
             str(_f(note, 'shot')) if _f(note, 'shot') else None,
             _f(note, 'date'), _f(note, 'text')]
    return ' '.join(p for p in parts if p).strip()


def noteMeta(note):
    """The dict the row keeps with the note: the filters the search already
    applied structurally, the title, the scope, and the path — read back on
    the answer so the reader sees the one the search ranked, not just the
    id."""
    return {
        'title': _f(note, 'title'),
        'machine': _f(note, 'machine'),
        'campaign': _f(note, 'campaign'),
        'shot': str(_f(note, 'shot')) if _f(note, 'shot') else None,
        'date': _f(note, 'date'),
        'author': _f(note, 'author'),
        'scope': _f(note, 'scope'),
        'path': _f(note, 'path'),
    }


def _scopes(scope):
    if scope in (None, 'both'):
        return ('personal', 'shared')
    if scope in ('personal', 'shared'):
        return (scope,)
    raise ValueError(
        '"scope=%r" is not a journal to index: its two are personal and '
        'shared (or both / left out for the two at once).' % scope)


def staleIds(scope, notes):
    """The ids of the notes (already filtered by the caller's
    ``list_notes``) whose stored row is not in step with the disk:
    missing from the index, or holding a text hash that is not the one
    the note holds. One read per journal, no re-embed — the search
    calls this before it ranks and pays one incremental ``reindex``
    when it is not empty."""
    out = []
    for sc in _scopes(scope):
        try:
            store = storeFor(sc)
        except ValueError:
            continue
        try:
            rows = store.rowsDigests()
            for note in notes:
                if note.scope != sc:
                    continue
                if rows.get(note.id) != hashText(noteText(note)):
                    out.append(note.id)
        finally:
            store.close()
    return out


def storeFor(scope):
    """The one ``rag_store.Store`` the journal ``scope`` carries, opened at
    the file ``indexPathFor`` names. The shared one raises the named
    refusal the ``journals`` store answers (no folder / not a directory),
    which the caller of a ``scope=None`` read skips and keeps the other."""
    from imasviz.VizAgent import rag_store
    return rag_store.Store.open(indexPathFor(scope), 'journal')


def upsertNote(scope, note, embedder=None):
    """The one note of the journal, in the store: the eager index on an
    ``add_note`` / ``edit_note``. ``embedder`` is the callable the run
    answers (the ``EmbeddingClient`` when the endpoint is named), and
    ``None`` for a store the lexical list alone serves (the note is still
    indexed on its text, and a later ``reindex`` under a named endpoint is
    the one that vectors it — the ``rag_store.upsert`` rule pays the embed
    then, because the row holds no vector under a named ``embed_sig``).
    A store the run cannot open is the named refusal the caller reads; the
    note itself is already on the disk the writers hold, so the write it
    answers is not one the index could not keep — the read falls back to
    the keyword the ``journals`` store ranks, and the next ``reindex`` sets
    the two in step."""
    store = storeFor(scope)
    try:
        return store.upsert(_f(note, 'id'), noteText(note),
                            meta=noteMeta(note), embedder=embedder)
    finally:
        store.close()


def removeNote(scope, note_id):
    """The one line of the store, gone: the eager index on a
    ``delete_note``. Not in the store is the no-op the ``rag_store``
    answers (the note's file is already off the disk the writers hold)."""
    store = storeFor(scope)
    try:
        return store.remove(note_id)
    finally:
        store.close()


def reindex(scope=None, embedder=None):
    """The whole journal, in step with the store: the eager index the
    ``reindex_journals`` runs.

    Walks the notes the ``journals`` store holds (its ``list_notes``
    is the disk the writers read, the one the run trusts), upserts each
    into the journal's store (re-embedding only what moved, under the
    ``embedder`` the run answers), and purges the rows the store holds
    that the journal no longer names (the note the run deleted, the one
    it edited off). A journal the run cannot open (the shared one, no
    folder) is refused by name and does not cost the other; a journal
    that holds no note is not purged (an empty source is not an ask to
    take the store's rows away — the ``reindex`` of ``rag_store`` would
    purge them, and a ``reindex_journals`` on an empty journal must not
    empty one that other writers still read).

    ``embedder`` is one the run answers for the two at once (the same
    ``EmbeddingClient``, the shared and the personal are indexed under
    the same ``embed_sig``), and ``None`` for a reindex the lexical list
    alone serves (the text is in step, and a later reindex under a named
    endpoint is the one that vectors it).
    """
    from imasviz.VizAgent import journals
    import logging
    out = {}
    scopes = _scopes(scope)
    for sc in scopes:
        try:
            notes = journals.JournalStore.list_notes(scope=sc)
        except ValueError as e:
            out[sc] = {'refusal': str(e)}
            logging.getLogger('logPanel').info(
                'the %s journal could not be listed for the index: %s'
                % (sc, e))
            continue
        if not notes:
            # An empty journal is not an ask to purge the store: a journal
            # the writers have emptied on one writer's side is one the
            # other still reads, and a reindex that took its rows away on
            # an empty list would be the silent wipe this refuses.
            out[sc] = {'upserted': 0, 'kept': 0, 'purged': 0, 'total': 0,
                       'skipped_empty': True}
            continue
        records = [{'id': n.id, 'text': noteText(n), 'meta': noteMeta(n)}
                   for n in notes]
        try:
            store = storeFor(sc)
        except ValueError as e:
            out[sc] = {'refusal': str(e)}
            logging.getLogger('logPanel').info(
                'the %s journal could not be indexed: %s' % (sc, e))
            continue
        try:
            out[sc] = store.reindex(records, embedder=embedder)
        finally:
            store.close()
    return out


def search(scope=None, include_ids=None, query=None, embedder=None,
           limit=20):
    """The two journals' ranks, fused: the one a ``scope=None``
    ``search_journals`` asks of, and the one a ``scope`` asks of alone.

    ``include_ids`` is the set of the ids the structured filter has
    already narrowed the notes to (the ``journals`` store's
    ``list_notes`` answered them); the search only ranks within them, so
    a note the filter left out is not in the answer whatever the query
    says. A journal the run cannot open (the shared one, no folder) is
    skipped — the other still answers, and the reason is the log the
    ``reindex`` above keeps.

    The answer holds the ``note_ids`` (the ids, the one the caller maps
    to the ``Journals`` notes it holds) **and** the ``method`` the run
    ranked with (``hybrid``/``embeddings``/``keyword``/``empty``), and
    the ``guarded`` flag when a store's ``embed_sig`` is not the one the
    run is under (its vectors were ignored, the keyword stands, and the
    ``guard_reason`` names it) — the same fields the single-store
    ``rag_store.search`` answers, so the caller reads the two the same
    way.
    """
    import logging
    results = []
    for sc in _scopes(scope):
        try:
            store = storeFor(sc)
        except ValueError as e:
            logging.getLogger('logPanel').info(
                'the %s journal could not be searched: %s' % (sc, e))
            continue
        try:
            results.append((sc,
                            store.search(query, embedder=embedder,
                                         limit=limit, include=include_ids)))
        finally:
            store.close()
    if not results:
        return {'hits': [], 'total': 0, 'method': 'empty', 'note_ids': []}
    if len(results) == 1:
        _sc, r = results[0]
        out = dict(r)
        out['hits'] = [{'id': rid, 'scope': _sc}
                       for rid in r.get('note_ids', [])]
        return out
    # The two journals: fuse their ranked id lists (the RRF the rank is
    # summed over), keep each hit's scope the one it came from.
    id2scope = {}
    for sc, r in results:
        for rid in r.get('note_ids', []):
            id2scope[rid] = sc
    fused = _fuseRRF(*[r.get('note_ids', []) for _sc, r in results])
    # The method is the strongest of the two the run ranked with: a
    # hybrid in either is the answer's hybrid, a vector in either its
    # embeddings, else the keyword.
    rank = {'hybrid': 3, 'embeddings': 2, 'keyword': 1, 'empty': 0}
    method = max((r['method'] for _sc, r in results),
                 key=lambda m: rank.get(m, 0)) if results else 'empty'
    guarded = any(r.get('guarded') for _sc, r in results)
    out = {
        'hits': [{'id': rid, 'scope': id2scope.get(rid)} for rid in fused],
        'total': sum(r.get('total', 0) for _sc, r in results),
        'method': method,
        'note_ids': list(fused),
        'guarded': guarded,
    }
    if guarded:
        reasons = [r.get('guard_reason') for _sc, r in results
                   if r.get('guard_reason')]
        if reasons:
            out['guard_reason'] = '; '.join(reasons)
    return out


def stats(scope=None):
    """The state of the two (or the one) journal indexes: the file each
    sits under, its rows and vectors, its ``embed_sig`` and ``dim`` (the
    fields a ``journal_stats`` answer names), and its ``built_at``. A
    journal the run cannot open answers a ``refusal`` the caller reads as
    the one the index could not open, not a zero it would read as empty."""
    import logging
    out = {}
    for sc in _scopes(scope):
        try:
            store = storeFor(sc)
        except ValueError as e:
            out[sc] = {'refusal': str(e)}
            continue
        try:
            s = store.stats()
        finally:
            store.close()
        out[sc] = s
    return out
