# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The persistent RAG index: one SQLite file, the text, its vector, its meta.

The shape is the one ``dal-rag`` proved on this stack, generalized to a
caller that names its own source:

* **one SQLite per journal (or corpus)** — the decision the caller makes by
  naming the file it will hold the index under. This module does not pick a
  place; it is given one (the journals put the personal one under
  ``~/.imasviz`` and the shared one under ``SharedJournalDir``; the documents
  corpus puts its one under its own folder);

* **eager upsert** — ``upsert`` writes the row and, when an embedder is
  handed, its vector on the spot. A second upsert of the same text under the
  same embedder is a no-op (the ``body_hash`` and the ``embed_sig`` are
  unchanged), which is what keeps ``reindex`` incremental: it walks the
  source, re-embeds only what moved, and purges what is gone;

* **search** = the reciprocal rank fusion (``RRF_K = 10``, the ``dal-rag``
  damping) of two lists asked of the same text: a light BM25 over the stored
  text (the algorithm of ``journals.rankByKeyword``, generalized to the stored
  string; no ``FTS5`` to fear) and the cosine of the query's vector against
  the stored one (a normalized matrix, ``dal-rag``'s ``Store.vector``). A
  text that is only in one of the two lists is still in the answer: fusion
  is a rank sum, not an intersection;

* **the model/dim guard**, the one ``dal-rag``'s ``_retrieve`` answers: the
  index records under ``meta`` the ``embed_sig`` (``endpoint|model``) and the
  ``dim`` of the embedder that wrote it, and a search run under a *different*
  embedder ignores the vectors (the lexical list stands alone) and **names**
  it — it never ranks the query in one vector space against the notes written
  in another.

Refusals are named (the style of this repository); a store the caller cannot
open, a text that does not vectorise, and an index the embedder no longer
matches are all said in words, not hidden.

Standard library + numpy (when present, for the matrix; a pure-Python cosine
stands for it when it is not). No new dependency, no ``FTS5`` required.
"""

import hashlib
import json
import math
import os
import sqlite3
import time

# The damping of the rank fusion. The textbook k=60 is tuned for fusing
# dozens of web result lists; with two lists over the notes of a journal it
# flattens the rank so much that a note merely in both lists outranks the
# one that is the #1 of the vectors — the same measurement that set k=10
# in dal-rag.
RRF_K = 10.0


def _embedSig():
    """The one signature the index records against its vectors: the
    endpoint the preferences name, and the model. The ``endpoint|model``
    spelling is the one a change of either trips, and the one the guard
    compares. Left unnamed, the empty string — an index written with no
    endpoint is one the lexical list answers alone."""
    try:
        from imasviz.VizUtils import QVizPreferences
        endpoint = (QVizPreferences.AgentEmbedEndpoint or '').strip()
        model = (QVizPreferences.AgentEmbedModel or '').strip()
    except Exception:
        endpoint, model = '', ''
    return '%s|%s' % (endpoint, model)


def _unit(vec):
    """A vector to unit length, or ``None`` when it has no direction (the
    one a cosine with it would not be a score)."""
    if not vec:
        return None
    norm = math.sqrt(sum(float(x) * float(x) for x in vec))
    if norm == 0.0:
        return None
    return [float(x) / norm for x in vec]


def _tokens(text):
    """The tokens one text holds, lowercase, stripped of what a search does
    not rank on — punctuation and a single character that is not the number
    of a shot. The same rule ``journals._tokens`` applies."""
    import re
    return [t for t in re.findall(r'[a-z0-9]+', (text or '').lower())
            if len(t) >= 2]


def _bm25Rank(rows, query, limit=None):
    """The ranked ``ids`` a light BM25 returns over the stored text, no
    dependency.

    ``rows`` is a list of ``(id, text, mtime)``. The term score of each
    query token is its count in the row's text, weighted by how rare the
    token is across the set (the IDF); two rows with the same score keep
    their mtime order (newest first). The algorithm is the one
    ``journals.rankByKeyword`` applies to the notes, read off their
    ``text`` — this one is generalized to the stored string, so the same
    ranking serves the journals and the documents corpus. A query that
    names no token ranks the newest first, same as ``rankByKeyword``.
    """
    tokens = _tokens(query)
    ordered = list(rows)
    if not tokens:
        ordered.sort(key=lambda r: r[2], reverse=True)
        return [r[0] for r in (ordered if limit is None else ordered[:limit])]
    n = len(rows)
    if not n:
        return []
    df = dict.fromkeys(tokens, 0)
    t_counts = []
    for rid, text, _ in rows:
        haystack = (text or '').lower()
        counts = {}
        for t in tokens:
            count = haystack.count(t)
            if count:
                counts[t] = count
                df[t] += 1
        t_counts.append(counts)
    scored = []
    for (rid, _text, mtime), counts in zip(rows, t_counts):
        score = 0.0
        for t, cnt in counts.items():
            idf = math.log(1.0 + (n - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * (cnt * 2.0) / (cnt + 1.0)
        scored.append((-score, -mtime, rid))
    scored.sort(key=lambda p: (p[0], p[1]))
    ranked = [rid for neg, _m, rid in scored if -neg > 0.0]
    return ranked if limit is None else ranked[:limit]


def _vectorRank(matrix, matrix_ids, qvec, limit=None):
    """The ranked ``ids`` a cosine against the stored vectors returns.

    ``matrix`` is a list of unit vectors (``matrix_ids[i]`` is the id of
    ``matrix[i]``); ``qvec`` is the unit query's vector. A numpy matrix and
    a dot product answer it when numpy is there, and a pure-Python cosine
    stands for it when it is not (the notes of a journal are few, and a
    store that must run where numpy is only in the modules keeps its
    answer). A vector with no direction, or one opposite the query
    (a cosine the search does not want), is out of the list.
    """
    if not matrix or qvec is None:
        return []
    try:
        import numpy as np
        m = np.asarray(matrix, dtype='float32')
        q = np.asarray(qvec, dtype='float32')
        sims = m @ q
        order = tuple(int(i) for i in np.argsort(-sims))
    except Exception:
        dots = []
        for i, vec in enumerate(matrix):
            dots.append((float(sum(a * b for a, b in zip(vec, qvec))), i))
        dots.sort(key=lambda p: (-p[0], p[1]))
        order = tuple(i for _d, i in dots)
    kept = [i for i in order if _dot(matrix[i], qvec) >= 0.0]
    ranked = [matrix_ids[i] for i in kept]
    return ranked if limit is None else ranked[:limit]


def _dot(a, b):
    return float(sum(x * y for x, y in zip(a, b)))


def _fuseRRF(*lists):
    """The reciprocal rank fusion of the ranked ``id`` lists, in the order
    the caller names them (the lexical list first, the vector one second —
    order changes nothing in a rank sum, but it is the one the answer
    reports). A note in both lists outranks one in only the first place
    the other gives it, and the note only the query's vector reached is
    still in the answer. The score is the sum over the lists of
    ``1 / (RRF_K + rank + 1)``; the ids come back newest of the two ranks.
    """
    fused = {}
    for lst in lists:
        for rank, rid in enumerate(lst):
            fused[rid] = fused.get(rid, 0.0) + 1.0 / (RRF_K + rank + 1)
    ordered = sorted(fused, key=lambda rid: (-fused[rid], rid))
    return ordered


class Store:
    """One SQLite index: the rows of its source, their vectors, its meta.

    ``open`` names the file; ``source_type`` is the word the stats and the
    guard report the index is the one of (``'journal'`` for the journals,
    ``'docs'`` for the documents corpus). A store is read and written by
    the caller on its own thread (the GUI thread of the loop), so there is
    no lock between two callers of one file: WAL is on, and two writers of
    the one store are the two sessions of the same user, the shape
    ``dal-rag`` runs.
    """
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS rows(
      id TEXT PRIMARY KEY, text TEXT, body_hash TEXT, mtime REAL,
      meta_json TEXT);
    CREATE TABLE IF NOT EXISTS vectors(
      id TEXT PRIMARY KEY, dim INTEGER, embedding BLOB);
    CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
    """

    def __init__(self, path, source_type='journal'):
        self.path = path
        self.source_type = source_type
        self.conn = sqlite3.connect(path)
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.executescript(self.SCHEMA)
        if not self._meta('source_type'):
            self._setMeta('source_type', source_type)

    @classmethod
    def open(cls, path, source_type='journal'):
        """One store at a file, its tables and its meta.

        The folder is created when it is not there (the personal index sits
        under ``~/.imasviz``, the documents one under its corpus folder —
        both one the caller already owns). A path that names a place that
        cannot hold a file (a file in the middle) is a named refusal, the
        one the caller reads as "the store is not there", not a crash.
        """
        folder = os.path.dirname(os.path.abspath(path))
        if not folder:
            folder = '.'
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as e:
            raise ValueError(
                'the index at %s cannot be opened: its folder could not '
                'be made (%s).' % (path, e))
        if os.path.exists(path) and not os.path.isfile(path):
            raise ValueError(
                'the index at %s is not a file to open: it is not one '
                'this store reads.' % path)
        return cls(path, source_type)

    def close(self):
        try:
            self.conn.commit()
        except sqlite3.Error:
            pass
        self.conn.close()

    # ------------------------------------------------------------------ meta

    def _meta(self, key):
        row = self.conn.execute(
            'SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return row[0] if row else None

    def _setMeta(self, key, value):
        self.conn.execute(
            'INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)',
            (key, str(value)))
        self.conn.commit()

    # ------------------------------------------------------------------ read

    def count(self):
        """The rows the store holds — one line a stats answer names, and
        the one ``search`` reports as ``total``."""
        return self.conn.execute(
            'SELECT COUNT(*) FROM rows').fetchone()[0]

    def has(self, key_id):
        return self.conn.execute(
            'SELECT 1 FROM rows WHERE id=?', (key_id,)).fetchone() is not None

    def keys(self):
        return [r[0] for r in self.conn.execute('SELECT id FROM rows')]

    def rowOf(self, key_id):
        """The stored text of one row, or ``None`` when it is not there."""
        row = self.conn.execute(
            'SELECT text FROM rows WHERE id=?', (key_id,)).fetchone()
        return row[0] if row else None

    def _allRows(self, include=None):
        """The ``(id, text, mtime)`` rows, the shape ``_bm25Rank`` and the
        guard read. ``include``, when named, is the set of the ids the
        caller wants (the journals' structured filter has already narrowed
        the notes, so the search only ranks within them)."""
        rows = [tuple(r) for r in self.conn.execute(
            'SELECT id, text, mtime FROM rows').fetchall()]
        if include is not None:
            wanted = set(include)
            rows = [r for r in rows if r[0] in wanted]
        return rows

    def _vectorOf(self, key_id):
        row = self.conn.execute(
            'SELECT embedding FROM vectors WHERE id=?', (key_id,)).fetchone()
        if not row or not row[0]:
            return None
        try:
            data = json.loads(row[0].decode())
            if data and data.get('vector'):
                return [float(x) for x in data['vector']]
        except (ValueError, UnicodeDecodeError):
            pass
        return None

    # ----------------------------------------------------------------- write

    def upsert(self, key_id, text, meta=None, embedder=None):
        """One row of the store, written (or kept) under its id.

        ``text`` is the one the store indexes and the one it embeds;
        ``meta`` is the dict the caller keeps with the row (the journal's
        filters, the chunk's header — read back on the search, not ranked
        on). ``embedder`` is the callable ``text -> vector`` the run
        answers, or ``None`` for a store the lexical list alone answers
        (the endpoint not named, or refused).

        The incremental rule: a row whose ``body_hash`` and the store's
        ``embed_sig`` are unchanged, and that already holds a vector under
        the embedder its ``embed_sig`` records, is kept as it stands (the
        re-embed it would cost is one the answer does not need). A row that
        moved, or a store under a new embedder, is written and re-vectorized
        — the ``reindex`` is incremental on exactly this, and ``add_note`` /
        ``edit_note`` pay one embed when the body changed, zero when it did
        not.
        """
        text = (text or '').strip()
        if not text:
            raise ValueError(
                'a row with no text does not index: name one.')
        h = hashlib.sha256(text.encode('utf-8')).hexdigest()[:32]
        sig = _embedSig() if embedder is not None else ''

        existing = self.conn.execute(
            'SELECT body_hash FROM rows WHERE id=?', (key_id,)).fetchone()
        if (existing
                and existing[0] == h
                and embedder is not None
                and self._vectorOf(key_id) is not None
                and self._meta('embed_sig') == sig):
            # Unchanged, and already vectorized under the same embedder:
            # the upsert is the keep, not the re-embed.
            if meta is not None:
                self.conn.execute(
                    'UPDATE rows SET meta_json=? WHERE id=?',
                    (json.dumps(meta or {}), key_id))
                self.conn.commit()
            return {'id': key_id, 'upserted': False, 'reason': 'unchanged'}

        vec = None
        dim = None
        if embedder is not None:
            try:
                v = _unit(embedder(text))
            except Exception:
                v = None
            if v is not None:
                vec = v
                dim = len(v)

        now = time.time()
        self.conn.execute(
            'INSERT OR REPLACE INTO rows(id,text,body_hash,mtime,meta_json) '
            'VALUES(?,?,?,?,?)',
            (key_id, text, h, now, json.dumps(meta or {})))
        if vec is not None:
            self.conn.execute(
                'INSERT OR REPLACE INTO vectors(id,dim,embedding) '
                'VALUES(?,?,?)',
                (key_id, dim,
                 json.dumps({'vector': vec, 'dim': dim, 'sig': sig}).encode()))
        else:
            self.conn.execute(
                'DELETE FROM vectors WHERE id=?', (key_id,))
        self._setMeta('embed_sig', sig)
        if dim is not None:
            self._setMeta('dim', str(dim))
        self._setMeta('updated_at', time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                                  time.gmtime()))
        self.conn.commit()
        return {'id': key_id, 'upserted': True, 'dim': dim}

    def remove(self, key_id):
        """The row and its vector, gone. Not in the store is a no-op that
        says so — a ``delete_note`` of a note the store never held does not
        cost a refusal the caller reads as a crash."""
        had_row = self.has(key_id)
        self.conn.execute('DELETE FROM rows WHERE id=?', (key_id,))
        self.conn.execute('DELETE FROM vectors WHERE id=?', (key_id,))
        self.conn.commit()
        return {'id': key_id, 'removed': bool(had_row)}

    def reindex(self, records, embedder=None):
        """The whole source, up to date in the store: incremental on the
        ``upsert`` rule, and purging the orphans.

        ``records`` is the list of the source's rows, each a dict holding
        ``id`` and ``text`` (and ``meta`` when the caller keeps one). Every
        one of them is upserted (re-embedded only when it moved, under the
        embedder the run answers), and the rows the store holds that the
        source no longer names are dropped — the note the run deleted, the
        page the corpus took out of. A store the corpus cannot open for the
        embeddings (the endpoint not named — ``embedder is None``) is still
        indexed on the text alone: the lexical list stands, and the next
        run under a named endpoint re-embeds it (the ``upsert`` rule pays
        the embed then, because the store holds no vector under a named
        ``embed_sig``).

        Returns the one line a ``reindex`` answer names: how many upserted
        (wrote), how many kept (unchanged), how many purged (gone from the
        source), and the count the store holds after.
        """
        records = list(records or [])
        seen = set()
        upserted = 0
        kept = 0
        for rec in records:
            key_id = rec['id']
            seen.add(key_id)
            out = self.upsert(key_id, rec['text'],
                              meta=rec.get('meta'), embedder=embedder)
            if out.get('upserted'):
                upserted += 1
            else:
                kept += 1
        purged = 0
        for key_id in self.keys():
            if key_id not in seen:
                self.remove(key_id)
                purged += 1
        self._setMeta('built_at',
                      time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        return {'upserted': upserted, 'kept': kept, 'purged': purged,
                'total': self.count()}

    # ---------------------------------------------------------------- search

    def search(self, query, embedder=None, limit=20, include=None):
        """The ranked answer of the store, in the shape the caller reads.

        The two lists of the one ``text``: the BM25 over the stored rows
        (always) and the cosine of the query's vector (when the ``embedder``
        answers **and** the store's ``embed_sig`` is the one the run is
        under — the guard the ``dal-rag``'s ``_retrieve`` answers). They
        are fused with ``RRF_K``, and the answer says which one ran

        * ``method: 'hybrid'`` — both lists ranked, the fusion the answer;
        * ``method: 'embeddings'`` — the vectors alone ranked (the text
          token-matched nothing, the query is one the vector answers);
        * ``method: 'keyword'`` — the lexical list alone (the endpoint not
          named / refused, or the guard ignored the vectors);
        * ``guarded: True`` and ``guard_reason`` — the store's ``embed_sig``
          is not the one the run is under: the vectors were ignored (the two
          are in different spaces), the lexical list stands, and the reason
          names the store's sig and the run's — the reindex is the one that
          sets it right.

        An empty store (``total: 0``) is the answer the caller reads as
        "index it first", not a crash. A query the embedder refuses is the
        keyword alone, with the reason named (the same rule the journals'
        fallback answers).
        """
        rows = self._allRows(include=include)
        total = len(rows)
        if not total:
            return {'hits': [], 'total': 0, 'method': 'empty',
                    'note_ids': []}
        query = (query or '').strip()
        # The lexical list: the BM25 when the query names a token, and the
        # newest-first order when it does not (a search with no query is the
        # list the caller reads newest first, the one ``list_notes`` holds).
        if query:
            ranked_lexical = _bm25Rank(rows, query)
        else:
            ranked_lexical = [r[0] for r in sorted(
                rows, key=lambda r: r[2], reverse=True)]

        sig = self._meta('embed_sig')
        cur = _embedSig()
        # The guard: the store's embed_sig is recorded, and it is not the
        # one the run is under — the two spaces do not meet, so the vectors
        # are ignored and the lexical list stands alone.
        guarded = sig is not None and sig != cur
        ranked_vector = []
        vector_refusal = None
        if embedder is not None and not guarded:
            try:
                qvec = _unit(embedder(query))
            except Exception as e:
                qvec = None
                vector_refusal = str(e)
            if qvec is not None:
                vectors = []
                vectors_ids = []
                for rid, _t, _m in rows:
                    vec = self._vectorOf(rid)
                    if vec is not None:
                        uv = _unit(vec)
                        if uv is not None:
                            vectors.append(uv)
                            vectors_ids.append(rid)
                if vectors:
                    ranked_vector = _vectorRank(vectors, vectors_ids, qvec)
        # A query the embedder could not vector is one the lexical list
        # answers alone (it was already computed above); the refusal is
        # named in the answer, so the caller does not read it as a crash.

        lists = [lst for lst in (ranked_lexical, ranked_vector) if lst]
        fused = _fuseRRF(*lists) if lists else []
        id2row = {r[0]: r for r in rows}
        hits = []
        for rid in fused:
            row = id2row.get(rid)
            if row is None:
                continue
            meta = {}
            raw_meta = self._rowMeta(rid)
            if raw_meta:
                try:
                    meta = json.loads(raw_meta)
                except (ValueError, TypeError):
                    meta = {}
            hits.append({
                'id': rid,
                'text': row[1],
                'mtime': row[2],
                'meta': meta,
            })
            if len(hits) >= limit:
                break
        # The method is the one the lists that actually ranked: both, the
        # vector alone (the text token-matched nothing), or the lexical
        # alone (the endpoint refused, or the guard ignored the vectors).
        # The two lists are asked in a fixed order (the vector first, the
        # lexical second), so the contributors come back in that order.
        if ranked_vector and ranked_lexical:
            method = 'hybrid'
        elif ranked_vector:
            method = 'embeddings'
        elif ranked_lexical:
            method = 'keyword'
        else:
            # Neither list ranked the query: the note_ids are empty and the
            # method says so, not a silent empty list the caller reads as a
            # crash.
            method = 'empty'
        out = {
            'hits': hits,
            'total': total,
            'method': method,
            'note_ids': [h['id'] for h in hits],
            'guarded': guarded,
            'embed_sig': sig,
            'current_sig': cur,
        }
        if guarded:
            out['guard_reason'] = (
                'the index was written under embedder %r but the run is '
                'under %r: the two spaces do not meet, so the vectors were '
                'ignored and the keyword answered alone. Reindex under the '
                'current endpoint to set it right.' % (sig, cur))
        if vector_refusal:
            out['vector_refusal'] = vector_refusal
        return out

    def _rowMeta(self, key_id):
        row = self.conn.execute(
            'SELECT meta_json FROM rows WHERE id=?', (key_id,)).fetchone()
        return row[0] if row else None

    # ----------------------------------------------------------------- stats

    def stats(self):
        """The state of the store: how many rows it holds, how many of them
        carry a vector, its ``source_type``, its ``embed_sig`` and ``dim``
        (the fields a ``stats`` / ``journal_stats`` answer names), and when
        it was last built. A store the caller cannot open for the embeddings
        (no ``embed_sig``) reports it as the one the lexical list alone
        served."""
        vectors = self.conn.execute(
            'SELECT COUNT(*) FROM vectors').fetchone()[0]
        return {
            'source_type': self.source_type,
            'path': self.path,
            'rows': self.count(),
            'vectors': vectors,
            'embed_sig': self._meta('embed_sig'),
            'dim': self._meta('dim'),
            'built_at': self._meta('built_at'),
        }
