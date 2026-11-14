# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The two journals: the note they read, write, and search.

A journal is a folder of Markdown notes, one file per note. The personal
journal is under :file:`$HOME/.imasviz/journals`; the shared one is
under the folder :file:`QVizPreferences.SharedJournalDir` names (an AFS
path, the rule ``~/.imasviz`` the configurations and the sessions use) —
an unnamed one is a refusal by name, the rule ``_namedReport`` applies
to the ``~/.imasviz`` folder.

A note is a small ``key: value`` front matter (the five filters the
application answers, and a title), a blank line, then a Markdown body.
The five filters are ``machine``, ``campaign``, ``shot``, ``date`` and
``author`` — the user's ask on a plasma shot or on a general
observation. A note with none of the first four is a general one, and a
note with all of them answers the ``shot=54924`` filter: a filter left
out asks of nothing, and a filter named asks of that field — a note
that does not name it is not in the answer.

The search is a two-step read:

* the **structured filter** is applied first (AND of the fields the
  caller named); a note that does not name a required field is out of
  the answer, whatever the query says about it;
* the **ranking** of what is left is either by embeddings (when the
  endpoint ``AgentEmbedEndpoint`` is named in the preferences and
  answers) or by keyword (a light BM25, 30 lines, no dependency) — the
  method the search used and the refusal it earned are both in the
  answer, so a run that fell back to the keyword does not present an
  embeddings result as if it had one, and the other way round.

Embeddings are a cache the note does not own: the one the run computes
is kept under :file:`$HOME/.imasviz/journals/.embed/` — or the same
dot-folder under the shared journal's directory when the search is on
the shared one — keyed by the hash of the note's body. So a note the
run writes twice costs one file the first time and nothing the second.
The cache is a **derived** artifact, not a shared state: two users of
the same shared journal hold two cache entries (one per user, local to
each), and a fresh clone of the shared journal has no cache until the
first run through it computes it — the read answers the same note on
the same body, so the two cache entries are content-identical (same
text, same model), and the last writer is the one a later run reads.
"""

import hashlib
import json
import math
import os
import re
import time

FRONT_MATTER_KEYS = ('scope', 'author', 'title', 'machine', 'campaign',
                     'shot', 'date')

# A note's id is its file name, without the ``.md`` extension. The one
# this writer spells is the one the reader reads back: a stable, a slug
# the folder can name and the search can sort. ``id_re`` matches it.
_ID_RE = re.compile(r'^[a-z0-9][a-z0-9_\-]{0,63}$')


def _noteIdFor(date, title, body, existing=()):
    """The id one write of one note takes.

    A stable id under the guard the folder has: the day, the time this
    write made it, the slug of the title (or 'note' when unnamed), and
    the short hash of the body — so the same note written in the same
    minute of the same day is still one file, not two. ``existing`` is
    the ids the folder already holds, and an id that collides with one
    of them takes a suffix (``-2``, ``-3``, ...) of the same slug, not
    a fresh one: the collision is one the caller names, not one the
    writer hides."""
    slug = _slug(title or '') or 'note'
    stamp = time.strftime('%Y%m%d-%H%M')
    digest = hashlib.sha256((body or '').encode('utf-8')).hexdigest()[:8]
    base = '%s_%s_%s_%s' % ((date or 'note'), slug, stamp, digest)
    id_ = base
    suffix = 2
    while id_ in set(existing):
        id_ = '%s-%d' % (base, suffix)
        suffix += 1
    return id_


def _slug(text, limit=48):
    """The id the slug is: lowercase alpha-num and dashes, at most
    ``limit`` characters of them."""
    text = (text or '').strip().lower()
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    if len(text) > limit:
        text = text[:limit].rstrip('-')
    return text


# ------------------------------------------------------------------- read

def _parseFrontMatter(text):
    """The front matter of one note, or ``(None, text)`` when the file
    is not a note of this journal.

    A note is a ``key: value`` block, one field per line (in the order
    ``FRONT_MATTER_KEYS`` spells it), a blank line (or the end of the
    block when it holds no body), and then the body. A file with
    neither a front matter nor a body is not a note: the
    ``QVizPromptHistory`` refusal it is — a shape the journal does not
    answer. A field the front matter spells but not one of the five it
    asks of is refused by name at the read, not invented.
    """
    lines = (text or '').splitlines()
    fields = {}
    index = 0
    for index, line in enumerate(lines):
        line = line.rstrip()
        if not line:
            break
        if line.lstrip().startswith('#'):
            break
        if ':' not in line:
            return None, text
        key, _, value = line.partition(':')
        key = key.strip().lower()
        value = value.strip()
        if key not in FRONT_MATTER_KEYS:
            return None, text
        fields[key] = value
    body = '\n'.join(lines[index + 1:]).strip()
    if not fields.get('author'):
        # The one the journal refuses for a note: a note without an
        # author is not a note of this shape, and the read does not hide
        # it.
        return None, text
    return fields, body


def _iso(text):
    """The ISO 8601 date one line spells, or ``None`` when it is not a
    date of that shape — a filter comparison the search makes, and the
    one that refuses it when it is not the shape the filter takes."""
    text = (text or '').strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
        return text
    return None


def _noteFromText(text, scope, id, path):
    """One note read off its file, or ``None`` when the file is not a
    note of this journal — the shape ``QVizPromptHistory`` refuses for
    a file that is not a list. A note with no author is one the journal
    does not answer, and the read does not hide it."""
    fields, body = _parseFrontMatter(text)
    if fields is None:
        return None
    return JournalNote(
        id=id, scope=scope, path=path,
        author=fields.get('author'),
        machine=fields.get('machine'),
        campaign=fields.get('campaign'),
        shot=fields.get('shot'),
        date=fields.get('date'),
        title=fields.get('title'),
        text=body)


# ------------------------------------------------------------------- write

def _renderNote(author, machine, campaign, shot, date, title, body):
    """One note to file: the front matter, one field per line, in the
    order ``FRONT_MATTER_KEYS`` spells it, only the fields the note
    names (an empty one is not a field the note answers), then a blank
    line, then the body."""
    lines = ['author: %s' % author]
    for key in ('title', 'machine', 'campaign', 'shot', 'date'):
        value = {'title': title, 'machine': machine, 'campaign': campaign,
                 'shot': shot, 'date': str(date) if date else None}[key]
        if value not in (None, ''):
            lines.append('%s: %s' % (key, value))
    lines.append('')
    return '\n'.join(lines) + '\n' + (body or '').rstrip() + '\n'


def _hashBody(text):
    """The key the cache reads under: the hash of the note's body
    only — the title and the filters are one note's own, and the body
    is the one the run ranks. A note's two writes (an original and an
    overwrite) cost the same key, and the run's second answer is a
    cache hit on the first's write."""
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()[:32]


def _cachePathFor(scopeFolder, digest):
    """The one file the cache holds for one note: the digest, and a
    ``.json`` extension — one the reader knows is not a note's own
    ``.md``, and the one ``_invalidateCache`` on a write removes."""
    folder = os.path.join(scopeFolder, '.embed')
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, digest + '.json')


def _invalidateCache(scopeFolder, digest):
    """The entry the cache holds for one note, gone. A write of the
    note is one the run makes, and a read of it answers the note the
    run wrote, not the one the run read before writing: a note's two
    writes (an original and an overwrite) cost the same digest, and
    the second write invalidates the first's cache entry."""
    path = _cachePathFor(scopeFolder, digest)
    if os.path.isfile(path):
        try:
            os.unlink(path)
        except OSError:
            pass


# ------------------------------------------------------------------- rank

def _tokens(text):
    """The tokens one text holds, lowercase and stripped of what a
    search does not rank on — punctuation and a single character that
    is not the number of a shot."""
    return [t for t in re.findall(r'[a-z0-9]+', (text or '').lower())
            if len(t) >= 2]


def _unit(vec):
    """A vector to unit length: the cosine the search computes is the
    dot product of two unit vectors, and a vector that is all zeros
    answers ``None`` (a zero vector has no direction, and a cosine with
    it is not a score)."""
    if not vec:
        return None
    norm = math.sqrt(sum(float(x) * float(x) for x in vec))
    if norm == 0.0:
        return None
    return [float(x) / norm for x in vec]


def rankByKeyword(notes, query, limit=None):
    """The ranked list a keyword search returns, no dependency.

    A light BM25: each query token's count in the note's haystack (title
    + machine + campaign + author + body) is the term score, weighted by
    how rare the token is across the set — the IDF the token earns
    against the ``len(notes)`` it appears in. Two notes with the same
    score keep their mtime order (newest first), so a search that
    matches nothing ranks the newest first, and the notes its tokens
    did not reach at all are left out of the ranked list — a search
    that matches nothing is the empty answer the caller names, not a
    hidden absence a caller has to guess at."""
    tokens = _tokens(query)
    if not tokens:
        # A query with no useful token is a filter, not a search: the
        # notes are returned in their natural order (mtime, newest first),
        # the same list the caller gets for a ``search_journals`` that
        # names a filter and no query.
        ordered = list(notes)
        return ordered if limit is None else ordered[:limit]
    n = len(notes)
    if not n:
        return []
    # df(t) = the count of notes holding t at least once. A token in
    # every note has the lowest idf (``log(1 + 0.5/0.5) = log(2)``), a
    # token in one of them the highest (``log(1 + (n-1+0.5)/0.5)``).
    df = dict.fromkeys(tokens, 0)
    scored = []
    for note in notes:
        haystack = ' '.join([
            note.title or '', note.machine or '', note.campaign or '',
            note.author or '', note.text or '',
        ]).lower()
        t_counts = {}
        for t in tokens:
            count = haystack.count(t)
            if count:
                t_counts[t] = count
                df[t] += 1
        score = 0.0
        for t, cnt in t_counts.items():
            idf = math.log(1.0 + (n - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * (cnt * 2.0) / (cnt + 1.0)
        scored.append((-score, -note.mtime, note))
    scored.sort(key=lambda p: (p[0], p[1]))
    ranked = [note for neg, _, note in scored if -neg > 0.0]
    return ranked if limit is None else ranked[:limit]


def rankByVector(notes, query, embedder, cacheFolders=None, limit=None):
    """The ranked list an embeddings search returns: the cosine between
    the query's vector and the one each note's body carries.

    ``embedder`` is a callable: ``text -> list[float]`` — the one the
    caller built for this run (a stand-in in the test, the
    ``EmbeddingClient`` in the field). The query's vector is asked
    once, and the notes' are read through the local cache, keyed by
    ``sha256(body)``. ``cacheFolders`` is a mapping ``scope -> folder``
    (``{'personal': ..., 'shared': ...}``); the cache for a note is the
    one keyed by that note's own ``scope``, so a search that spans both
    journals reads each against its own cache folder, and a note whose
    scope maps to no folder is vectorised and not cached (a cache it
    could not own is not a cache it does not write). A note the
    embedder could not vector (a refusal from the endpoint) is dropped
    from the ranked list — the caller reads that as one the search did
    not rank, not an empty answer. A zero or negative score is not in
    the ranked list either: a vector with no direction or one opposite
    the query is not one the query asks of.
    """
    if not notes:
        return []
    try:
        qvec = _unit(embedder(query))
    except Exception as e:
        # A query the embedder refused is one the ranking cannot rank:
        # the refusal is the caller's to name, and an empty ranked list
        # is not the answer a rankByVector that could not rank should
        # give — the caller names it, not hides it.
        raise ValueError('the query could not be vectorised: %s' % e) from e
    if qvec is None:
        raise ValueError(
            'the query vectorised to an empty vector: the embedder does '
            'not answer a direction for this query.')
    cacheFolders = cacheFolders or {}
    scored = []
    for note in notes:
        digest = _hashBody(note.text)
        folder = cacheFolders.get(note.scope)
        vec = None
        if folder is not None:
            vec = _readCache(folder, digest)
        if vec is None:
            try:
                vec = _unit(embedder(note.text))
            except Exception:
                continue
            if vec is not None and folder is not None:
                _writeCache(folder, digest, vec)
        if vec is None:
            continue
        cos = float(sum(a * b for a, b in zip(qvec, vec)))
        if cos >= 0.0:
            scored.append((cos, -note.mtime, note))
    scored.sort(key=lambda p: (-p[0], p[1]))
    result = [note for _, _, note in scored]
    return result if limit is None else result[:limit]


# ------------------------------------------------------------------ cache

def _readCache(folder, digest):
    """The vector the cache holds for one note, or ``None`` when it
    does not — the cache is a derived artifact, and the run that does
    not hold one for a note is the one that computes it (the search
    reads, not the cache). A cache entry the run cannot read is a
    missing one, not an empty vector, and the search recomputes it."""
    path = _cachePathFor(folder, digest)
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        if data and data.get('vector'):
            return [float(x) for x in data['vector']]
    except (OSError, ValueError):
        pass
    return None


def _writeCache(folder, digest, vec):
    """The one the cache holds for a note, written: a file with the
    vector and the hash of the text it was computed on — so a cache
    entry the endpoint's model change does not invalidate is the one
    the run recomputes on its next search. A cache write that fails is
    a search that still answers: the vector is there, the file is not —
    the next search recomputes, and the search's answer is the same,
    not one short of it."""
    path = _cachePathFor(folder, digest)
    try:
        with open(path, 'w') as f:
            json.dump({'vector': [float(x) for x in vec]}, f)
    except OSError as e:
        import logging
        logging.getLogger('logPanel').info(
            "the journal's cache could not be written to %s: %s"
            % (path, e))


# ------------------------------------------------------------------- note

class JournalNote:
    """One note of one journal, as the search and the read return it.

    ``id`` is the file name, without the ``.md`` extension — the stable
    id the read, the write, and the ``read_note`` answer by. ``scope``
    is ``personal`` or ``shared``. The five filters are the structured
    fields of the front matter (``author`` required on a write, the
    others optional). ``text`` is the body after the front matter.
    ``mtime`` is the file's modification time, and the read order is by
    it (newest first is the answer a ``search_journals`` gives when it
    ranks nothing else, and the one a ``list_notes`` always gives).
    """
    def __init__(self, id, scope, path, author, machine=None, campaign=None,
                 shot=None, date=None, title=None, text='', mtime=0.0):
        self.id, self.scope, self.path = id, scope, path
        self.author, self.machine, self.campaign = author, machine, campaign
        self.shot, self.date, self.title = shot, date, title
        self.text, self.mtime = text, mtime

    def asDict(self):
        """The JSON the tools and the surfaces hand out: the five
        filters, the title, the body, and the mtime — one the reader
        sorts by when the search does not."""
        return {
            'id': self.id, 'scope': self.scope, 'path': self.path,
            'author': self.author, 'machine': self.machine,
            'campaign': self.campaign, 'shot': self.shot,
            'date': str(self.date) if self.date else None,
            'title': self.title, 'text': self.text,
            'mtime': self.mtime,
        }

    def asSearchResult(self, limit=320):
        """The one a search result hands back: the five filters, the
        title, the one ``snippet`` (the body bounded to ``limit``, so
        the reader sees the note is the one they want without a full
        read), and the id — the one ``read_note`` asks for the full
        body."""
        return {
            'id': self.id, 'scope': self.scope, 'author': self.author,
            'machine': self.machine, 'campaign': self.campaign,
            'shot': self.shot,
            'date': str(self.date) if self.date else None,
            'title': self.title,
            'snippet': self.snippet(limit=limit),
            'mtime': self.mtime,
        }

    def snippet(self, limit=320):
        """The one line the search result shows the reader: the body
        bounded to ``limit`` characters — enough to tell the reader the
        note is the one they want, not a full read of the file. A note
        with no body is one the title answers, and the title is the
        one the snippet reads when the body is empty."""
        text = (self.text or '').strip()
        if not text and self.title:
            text = (self.title or '').strip()
        if not text:
            return ''
        text = text.replace('\n', ' ')
        if len(text) > limit:
            text = text[:limit - 1].rstrip() + '\u2026'
        return text


# ------------------------------------------------------------------ store

class JournalStore:
    """The two journals and their notes, on disk.

    The model is ``QVizPromptHistory``: every path is resolved under
    :file:`$HOME` (the personal journal) or under
    :file:`SharedJournalDir` (the shared one), the ``No HOME`` refusal
    on the personal and the "the folder the shared journal is named at
    is not named / is not a directory" on the shared, and the "a file
    that is not this shape is a refusal by what it is" on every read.
    The two journals are independent: a personal note is not in the
    shared one and the other way round, and ``scope=None`` is the union
    of the two (the default of a ``search_journals`` that asks of
    nothing else).
    """
    @staticmethod
    def personalDirectory():
        home = os.environ.get('HOME')
        if not home:
            raise ValueError(
                'No HOME in the environment: the personal journal has '
                'no folder to sit under.')
        folder = os.path.join(home, '.imasviz', 'journals')
        os.makedirs(folder, exist_ok=True)
        return folder

    @staticmethod
    def sharedDirectory():
        from imasviz.VizUtils import QVizPreferences
        path = (QVizPreferences.SharedJournalDir or '').strip()
        if not path:
            raise ValueError(
                'The shared journal has no folder named: set '
                'SharedJournalDir in ~/.imasviz/preferences to point it '
                'at a shared directory (AFS) the writers can reach. '
                'The personal one is under ~/.imasviz/journals.')
        folder = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(folder):
            raise ValueError(
                'The shared journal named "%s" is not a directory: '
                'create it, or name one that is.' % folder)
        return folder

    @classmethod
    def folderFor(cls, scope):
        if scope == 'personal':
            return cls.personalDirectory()
        if scope == 'shared':
            return cls.sharedDirectory()
        raise ValueError(
            '"scope=%r" is not a journal: its two are personal and '
            'shared.' % scope)

    @staticmethod
    def _notePath(folder, note_id):
        """The file of one note, guarded the way ``McpGuiCore._namedReport``
        guards a report: a name that escapes the folder is refused by
        name, and ``.``/``..``/a path are not the name of a note. The
        ``id_re`` matches what this writer spells, so the read that
        follows the write and the write that follows the read are one
        pair, not two."""
        note_id = (note_id or '').strip()
        if not note_id:
            raise ValueError('a note id is a name, not the empty string.')
        if os.path.sep in note_id or '/' in note_id or '\\' in note_id \
                or note_id in ('.', '..') or note_id.startswith('.'):
            raise ValueError(
                '"%s" names a place, not a note: name one inside %s '
                '(a note is its file name, without the extension).'
                % (note_id, folder))
        if not _ID_RE.match(note_id):
            raise ValueError(
                '"%s" is not the id of a note: a note id is the one '
                'its file name leads with (lowercase letters, digits, '
                '_ and -, at most 64 characters, and not starting with '
                '- or a digit the slug would not spell).' % note_id)
        path = os.path.join(folder, note_id + '.md')
        if os.path.dirname(os.path.realpath(path)) != os.path.realpath(folder):
            raise ValueError('"%s" would be read outside %s.' % (note_id, folder))
        return path

    @classmethod
    def list_notes(cls, scope=None, machine=None, campaign=None, shot=None,
                   date_from=None, date_to=None, author=None):
        """The notes in the journals, filtered and newest first.

        ``scope=None`` is the union of the two (the default a
        ``search_journals`` without a scope asks of), ``scope='personal'``
        and ``scope='shared'`` are the one the caller names. A filter
        (``machine``, ``campaign``, ``shot``, ``author``) narrows to
        the notes that name that field: a note that does not name it
        is excluded, and a filter left out is no filter at all.
        ``date_from``/``date_to`` are ISO 8601 (YYYY-MM-DD) and ask of
        the notes that name a date in that range, inclusive — a note
        with no date is out of the answer, the same rule the fields
        above answer. Empty (a filter that matched nothing) is an
        answer, and the caller reads it as one, not a refusal.

        An ``asked`` is a refusal the journal it names does not exist for,
        and a ``both`` (or no ask) is a search that spans the two --
        a journal the search does not answer with in the ``both``
        shape is one it skips, not one it refuses for: the other
        journal still answers, and the reason it is not in the
        answer is in the log. The one an explicit ``asked`` names,
        and it is not there, is the same reason raised to the caller
        as the refusal it was asking for.
        """
        scopes = cls._scopes(scope)
        both = scope in (None, 'both')
        notes = []
        for sc in scopes:
            try:
                folder = cls.folderFor(sc)
            except ValueError as e:
                if not both:
                    raise
                # A journal that is not available (the shared one, no
                # folder named) is one the search skips, not one it
                # refuses for: the other journal still answers, and the
                # reason the two are not in the answer together is in
                # the log, not in the search's refusal.
                import logging
                logging.getLogger('logPanel').info(
                    'the %s journal is not available: %s' % (sc, e))
                continue
            for name in sorted(os.listdir(folder)):
                if not name.endswith('.md') or name.startswith('.'):
                    continue
                path = os.path.join(folder, name)
                if not os.path.isfile(path):
                    continue
                note = _loadNote(sc, name[:-3], path)
                if note is not None:
                    notes.append(note)
        notes = _applyFilters(notes, machine=machine, campaign=campaign,
                              shot=shot, date_from=date_from, date_to=date_to,
                              author=author)
        notes.sort(key=lambda note: note.mtime, reverse=True)
        return notes

    @staticmethod
    def _scopes(scope):
        if scope in (None, 'both'):
            return ('personal', 'shared')
        if scope in ('personal', 'shared'):
            return (scope,)
        raise ValueError(
            '"scope=%r" is not a journal: its two are personal and '
            'shared (or both / left out for the two asked at once).'
            % scope)

    @classmethod
    def read_note(cls, scope, note_id):
        """The full text of one note of one journal, by its id (the file
        name without ``.md``). Not in the journal is refused by name,
        naming the ids it does hold. A note whose file is there but
        does not parse as one the journal answers (no author) is
        refused too, the same rule ``_loadNote`` applies for a
        ``list_notes`` that would not hide it."""
        folder = cls.folderFor(scope)
        path = cls._notePath(folder, note_id)
        if not os.path.isfile(path):
            held = sorted(name[:-3] for name in os.listdir(folder)
                          if name.endswith('.md') and not name.startswith('.'))
            raise ValueError(
                'No note "%s" in the %s journal: it holds %s.'
                % (note_id, scope, ', '.join(held) or 'none at all'))
        note = _loadNote(scope, note_id, path)
        if note is None:
            raise ValueError(
                'Note "%s" in the %s journal is not one this shape '
                'answers: its front matter has no author, the one a '
                'note of this journal names.' % (note_id, scope))
        return note.asDict()

    @classmethod
    def add_note(cls, scope, text, author=None, machine=None, campaign=None,
                 shot=None, date=None, title=None):
        """One new note in one journal, and its id.

        The author is required on every write: ``author`` is the one
        the caller named, or ``$USER`` when the caller left it out — a
        run with no ``$USER`` in the environment is refused by name,
        because the write is visible to whoever reads the journal, and
        a writer it cannot attribute to is one the journal does not
        hold. A note with no body is the shape this journal refuses,
        as a note without an author: the file is not written, and
        the reason is named.
        """
        if scope not in ('personal', 'shared'):
            raise ValueError(
                '"scope=%r" is not a journal: its two are personal and '
                'shared.' % scope)
        author = (author or os.environ.get('USER') or '').strip()
        if not author:
            raise ValueError(
                'A note needs its author named: no `author` given, and '
                'no $USER in the environment to fall back to — the write '
                'is visible to whoever reads the journal, and a writer '
                'it cannot attribute to is one the journal does not hold.')
        body = (text or '').strip()
        if not body:
            raise ValueError(
                'A note needs its body: the one you named is empty — a '
                'note that is only its filters (a `machine:` line and no '
                'text after it) is the shape this journal does not hold.')
        folder = cls.folderFor(scope)
        existing = [n[:-3] for n in os.listdir(folder)
                    if n.endswith('.md') and not n.startswith('.')]
        note_id = _noteIdFor(date, title, body, existing=existing)
        path = os.path.join(folder, note_id + '.md')
        if os.path.exists(path):
            # The same note written twice costs one file, not two: the
            # one on disk is the answer, and the second write is the
            # one ``read_note`` answers, not the one the write just made.
            # The id is the same, so the read is the same.
            existing_note = cls.read_note(scope, note_id)
            return {'id': note_id, 'path': path, 'author': author,
                    'note': existing_note, 'overwritten': False}
        rendered = _renderNote(author, machine, campaign, shot, date,
                               title, body)
        with open(path, 'w') as f:
            f.write(rendered)
        _invalidateCache(folder, _hashBody(body))
        return {
            'id': note_id, 'path': path, 'author': author,
            'machine': machine, 'campaign': campaign, 'shot': shot,
            'date': str(date) if date else None, 'title': title,
            'text': body, 'overwritten': True,
        }

    @classmethod
    def delete_note(cls, scope, note_id):
        """One note of one journal, gone: the file is removed, and the
        entry the cache holds for it drops out of the search. The note
        is one the folder holds — a note it does not hold is refused by
        name, naming the ones it does — and the cache is invalidated
        on a write too: the run's next search does not rank a note the
        run deleted, because the note's file is not there."""
        folder = cls.folderFor(scope)
        path = cls._notePath(folder, note_id)
        if not os.path.isfile(path):
            held = sorted(name[:-3] for name in os.listdir(folder)
                          if name.endswith('.md') and not name.startswith('.'))
            raise ValueError(
                'No note "%s" in the %s journal to delete: it holds %s.'
                % (note_id, scope, ', '.join(held) or 'none at all'))
        note = _loadNote(scope, note_id, path)
        if note is not None:
            _invalidateCache(folder, _hashBody(note.text))
        os.unlink(path)
        return {'id': note_id, 'deleted': True,
                'author': (note and note.author) or '?'}

    @staticmethod
    def stats():
        """The one line a ``journal_stats`` of the core gives: how
        many notes the two journals hold, the state of the embeddings
        (is the endpoint named in the preferences, and if so, what
        model it names — the two fields a ``search_journals`` asks of
        to decide whether it ranks by embeddings or by keyword), and
        the folders the personal and the shared are each under. A run
        that is asking for a note the journal holds is one that is
        asking for this first, and the answer says if it is there, and
        where."""
        result = {
            'personal': {'folder': None, 'notes': 0},
            'shared': {'folder': None, 'notes': 0},
            'embeddings': {'endpoint_named': False,
                           'endpoint': '', 'model': ''},
        }
        for scope in ('personal', 'shared'):
            try:
                folder = JournalStore.folderFor(scope)
                count = len([n for n in os.listdir(folder)
                             if n.endswith('.md') and not n.startswith('.')])
                result[scope] = {'folder': folder, 'notes': count}
            except ValueError as e:
                result[scope] = {'folder': None, 'notes': 0,
                                 'refusal': str(e)}
        try:
            from imasviz.VizUtils import QVizPreferences
            endpoint = (QVizPreferences.AgentEmbedEndpoint or '').strip()
            result['embeddings']['endpoint_named'] = bool(endpoint)
            result['embeddings']['endpoint'] = endpoint
            result['embeddings']['model'] = \
                (QVizPreferences.AgentEmbedModel or '').strip()
        except Exception:
            pass
        return result


def _loadNote(scope, id, path):
    """The one note of a folder, or ``None`` when the file is not a
    note of this journal — the shape ``QVizPromptHistory`` refuses for
    a file that is not a list. A note with no author is one the journal
    does not answer, and the read does not hide it: the reason is in
    the log, and the ``list_notes`` is the one that answers the empty
    result (or the refusal of ``read_note``)."""
    try:
        with open(path) as f:
            text = f.read()
    except OSError as e:
        import logging
        logging.getLogger('logPanel').info(
            'journal note %s could not be read: %s' % (path, e))
        return None
    note = _noteFromText(text, scope=scope, id=id, path=path)
    if note is None:
        import logging
        logging.getLogger('logPanel').info(
            'journal note %s has no author in its front matter and is '
            'not in the list' % path)
        return None
    try:
        note.mtime = os.path.getmtime(path)
    except OSError:
        note.mtime = 0.0
    return note


def _applyFilters(notes, machine=None, campaign=None, shot=None,
                  date_from=None, date_to=None, author=None):
    """The structured-filter half of a search: the AND of the fields
    the caller named, on each note's front matter.

    One filter named is one the notes answer on that field, and a note
    that does not name it is out of the answer — a filter the note
    does not answer with is not a match, whatever else the note holds.
    A filter left out (``None``) is no filter at all: the note's field
    is not asked of. ``date_from``/``date_to`` ask of the note's date,
    and a note with no date is out of the range — a range is one the
    note's date is inside of, and a date the note does not name is not
    in the range.
    """
    def matches(note):
        if machine is not None and machine != '':
            if (note.machine or '').lower() != str(machine).lower():
                return False
        if campaign is not None and campaign != '':
            if (note.campaign or '').lower() != str(campaign).lower():
                return False
        if shot is not None and shot != '':
            if str(note.shot) != str(shot):
                return False
        if author is not None and author != '':
            if (note.author or '') != author:
                return False
        d_from = _iso(date_from) if date_from else None
        d_to = _iso(date_to) if date_to else None
        if d_from is not None and not note.date:
            return False
        if d_to is not None and not note.date:
            return False
        if d_from is not None and note.date:
            if str(note.date) < d_from:
                return False
        if d_to is not None and note.date:
            if str(note.date) > d_to:
                return False
        return True
    return [note for note in notes if matches(note)]
