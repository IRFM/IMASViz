# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The journal, document and prompt gestures of one IMASViz session.

The journals (the notes, the index, the edits), the documents (the RAG corpus) and the prompts (the reusable text blocks): read the ones the user keeps, index and search them, add or edit them. A refusal is the named `ValueError` the caller gets back.
"""

class JournalOps:
    """The journals, the documents and the prompts."""

    def _noteEmbedder(self):
        """The ``text -> vector`` the journal index answers, or ``None``.

        The one the preferences name (``AgentEmbedEndpoint`` /
        ``AgentEmbedModel``), the ``EmbeddingClient`` the run built for it;
        left unnamed, the index is served on the keyword alone (its text
        is still kept in step, and a ``reindex_journals`` under a named
        endpoint is the one that vectors it). A client the caller cannot
        build is the ``None`` the search answers alone on the keyword —
        the read is never one the endpoint is absent from."""
        from imasviz.VizUtils import QVizPreferences
        endpoint = (QVizPreferences.AgentEmbedEndpoint or '').strip()
        if not endpoint:
            return None
        from imasviz.VizAgent.llm_client import EmbeddingClient
        return EmbeddingClient()

    def _syncJournalWrite(self, scope, answer, kind='add'):
        """Keep the journal's index in step with a write the run answered.

        ``answer`` is the one ``add_note`` / ``edit_note`` holds (a dict
        the ``journals`` store handed back, the keys the note's fields),
        and this upserts it under the journal's store (the text
        ``journals_index.noteText`` composes: the title, the filters, the
        body), re-embedding when the body moved and keeping it otherwise
        (the ``rag_store.upsert`` incremental rule). The write the run is
        answering is never one the index cost a refusal: a store the run
        cannot open (the shared folder not named) or an embedder that
        refuses are logged, and the note stands on the disk the writers
        hold — the search answers the keyword alone if the store does
        not, and rebuilds the index on a miss before it ranks.
        """
        import logging
        try:
            from imasviz.VizAgent import journals_index
            journals_index.upsertNote(
                scope, answer, embedder=self._noteEmbedder())
        except Exception as e:
            logging.getLogger('logPanel').info(
                'the %s %s of note %s did not keep its index in step: %s '
                '(the note itself stands on the disk the writers hold)'
                % (scope, kind, answer.get('id', '?'), e))

    def search_journals(self, scope=None, query=None, limit=20,
                        machine=None, campaign=None, shot=None,
                        date_from=None, date_to=None, author=None):
        """The RAG of the two journals.

        Three steps, in that order:
        0. the structured filter (``machine``/``campaign``/``shot``/
           ``date_from``/``date_to``/``author``) narrows to the notes that
           name each of the fields the caller asked of;
        1. the eager index — the one ``add_note`` / ``edit_note`` /
           ``delete_note`` keep in step and ``reindex_journals`` builds
           (one SQLite per journal under ``~/.imasviz`` and the shared
           folder) — is asked of first: the BM25 over the notes' text
           fused with the cosine of the query against the same
           (the ``rag_store``'s RRF). A note the disk holds but the
           index does not (a write or an edit outside the run, or an
           index left stale) is caught by a one-line staleness check
           and re-indexed before the rank, incrementally;
        2. the ranking of what is left is the one the index answers
           (method ``hybrid`` / ``embeddings`` / ``keyword``); a store
           written under an embedder the run is not under answers
           ``guarded`` with the ``guard_reason`` and its vectors ignored.

        The keyword (a light BM25, no dependency) stands only when the
        index cannot answer at all — the final resort, in which case it
        is named as such, not presented as the indexed answer. An empty
        filter answer is the ``total: 0`` the answer holds, and a store
        that answers with the vectors ignored (the guard), or with the
        query refused, is named in the answer as ``guarded`` /
        ``fallback_from`` + ``fallback_reason`` — the run that read it
        does not present it as an embeddings answer.
        """
        from imasviz.VizAgent import journals
        notes = journals.JournalStore.list_notes(
            scope=scope, machine=machine, campaign=campaign, shot=shot,
            date_from=date_from, date_to=date_to, author=author)
        total = len(notes)
        try:
            limit = max(1, int(limit))
        except (TypeError, ValueError):
            limit = 20
        if not query or not str(query).strip():
            return {
                'scope': scope or 'both', 'query': None, 'total': total,
                'returned': min(total, limit), 'method': 'list',
                'notes': [note.asSearchResult() for note in notes[:limit]],
            }
        query = str(query).strip()
        from imasviz.VizAgent import journals_index
        embedder = self._noteEmbedder()
        # The one-line staleness rule: the index holds a row whose text
        # is not the one the disk holds (a write or an edit outside the
        # run) or a note it does not hold at all — one incremental
        # reindex pays the embed for what moved, and nothing when the
        # index is in step.
        if journals_index.staleIds(scope, notes):
            journals_index.reindex(scope=scope, embedder=embedder)
        include_ids = set(note.id for note in notes)
        indexed = journals_index.search(
            scope=scope, include_ids=include_ids, query=query,
            embedder=embedder, limit=limit)
        if indexed.get('note_ids'):
            by_id = {note.id: note for note in notes}
            answer = {
                'scope': scope or 'both', 'query': query, 'total': total,
                'returned': min(total, len(indexed['note_ids'])),
                'method': indexed['method'],
                'indexed': True,
                'notes': [by_id[rid].asSearchResult()
                          for rid in indexed['note_ids'] if rid in by_id],
            }
            if indexed.get('guard_reason'):
                answer['guarded'] = True
                answer['guard_reason'] = indexed['guard_reason']
            if indexed.get('vector_refusal'):
                # The endpoint was named, the query did not vectorise:
                # the index answered the keyword, and the refusal is
                # named rather than hidden.
                answer['fallback_from'] = 'embeddings'
                answer['fallback_reason'] = indexed['vector_refusal']
            return answer
        # The index could not answer (or answered nothing): the keyword
        # is named as the method, and the answer is the list the disk
        # holds, ranked by what it holds.
        ranked = journals.rankByKeyword(notes, query, limit=limit)
        return {
            'scope': scope or 'both', 'query': query, 'total': total,
            'returned': len(ranked),
            'method': 'keyword',
            'notes': [note.asSearchResult() for note in ranked],
        }

    def read_note(self, scope, note_id):
        """The full body of one note of one journal, by its id (the
        file name without ``.md``). Not in the journal is a refusal by
        name, naming the ids it does hold; a note whose file is there
        but does not parse as one (no ``author``) is the same refusal,
        the shape ``journal`` does not answer is one the read does
        not hide."""
        from imasviz.VizAgent import journals
        return journals.JournalStore.read_note(scope, note_id)

    def list_notes(self, scope=None, machine=None, campaign=None, shot=None,
                   date_from=None, date_to=None, author=None):
        """The notes the two journals hold, filtered (the author is
        the one required on every note, the others optional), newest
        first. ``date_from`` and ``date_to`` bound the shot date the
        note carries (``YYYY-MM-DD``); a note that names no date is
        excluded only when the caller names a window. An empty list is
        the answer the caller reads as an answer, not a refusal: the
        folder holds no note of the shape the filters ask of, and that
        is what the answer says."""
        from imasviz.VizAgent import journals
        notes = journals.JournalStore.list_notes(
            scope=scope, machine=machine, campaign=campaign, shot=shot,
            date_from=date_from, date_to=date_to, author=author)
        return {'scope': scope or 'both',
                'count': len(notes),
                'notes': [note.asSearchResult() for note in notes]}

    def journal_stats(self):
        """The state of the two journals, their embeddings, and their
        indexes: the folder the personal and the shared are each under
        (a ``refusal`` when no folder is named / not a directory), the
        count of notes each holds, the state of the embeddings (is the
        endpoint named in the preferences, and if so, what model it
        names), and the one each journal's index holds — its file, its
        rows and vectors, its ``embed_sig`` and ``dim``, and its
        ``built_at`` (a ``refusal`` the same way when the shared folder
        is not named). The caller reads those to decide the method a
        run will rank with (index then keyword, embeddings then
        keyword), and one ``reindex_journals`` sets the two in step."""
        from imasviz.VizAgent import journals
        from imasviz.VizAgent import journals_index
        stats = journals.JournalStore.stats()
        try:
            stats['indexes'] = journals_index.stats()
        except Exception:
            stats['indexes'] = {}
        return stats

    def reindex_journals(self, scope=None):
        """The two (or the one) journals, in step with their indexes.

        The eager rebuild the read asks of when an index is empty, stale
        or guarded: it walks the notes the ``journals`` store holds,
        upserts each into the journal's store (re-embedding only what
        moved, under the endpoint the preferences name), and purges the
        rows the store holds that the journal no longer keeps. The answer
        is one line per journal it held (``upserted``/``kept``/``purged``/
        ``total``), a ``refusal`` the one it could not open (the shared
        folder not named), and the ``embedder_named`` flag — whether the
        run vectorized this pass or kept the text alone for the keyword
        (the embed the later run under a named endpoint will pay). A
        journal the writer emptied on one side is not purged by it (an
        empty source is not an ask to take the other writer's rows away);
        that one answers ``skipped_empty``.
        """
        from imasviz.VizAgent import journals_index
        embedder = self._noteEmbedder()
        out = journals_index.reindex(scope=scope, embedder=embedder)
        return {'scopes': out, 'embedder_named': embedder is not None}

    def _docsEmbedder(self):
        """The ``text -> vector`` the documents corpus answers, or
        ``None`` (the corpus served on the keyword alone). The one the
        preferences name (``AgentEmbedEndpoint`` / ``AgentEmbedModel``);
        left unnamed, the corpus is served on the keyword (a document's
        text is still kept in step with the store, and the one a later
        ``reindex_documents`` under a named endpoint pays to vector)."""
        from imasviz.VizAgent import rag_docs
        return rag_docs.docsEmbedder()

    def list_documents(self):
        """The documents the corpus reads: every ``.md``/``.txt``/``.pdf``
        the folder ``AgentDocsDir`` names holds (its name, its size, its
        date, and the ``rel`` the search answers by). A corpus run cannot
        read (no folder named, the folder not a directory) is a refusal by
        name, naming the one it could not read — the same shape the shared
        journal answers for its folder."""
        from imasviz.VizAgent import rag_docs
        return {'documents': rag_docs.listDocuments()}

    def read_document(self, rel):
        """The full text of one document of the corpus, by its ``rel`` (the
        one a search hits back by). Not in the corpus is a refusal by name,
        naming the ones it does read; a document it does not read is the
        same — the corpus does not cost a crash to a read it cannot answer."""
        from imasviz.VizAgent import rag_docs
        return {'rel': rel, 'text': rag_docs.readDocument(rel)}

    def reindex_documents(self):
        """The whole corpus, in step with the store: the one the user runs
        on adding a document to the corpus folder, or changing the endpoint
        (the two are then not the same space, and this sets them in step).
        It walks the documents the corpus reads, upserts each (re-embedding
        only what moved, under the endpoint the preferences name), and
        purges the rows the store holds that the corpus no longer holds (a
        document that left the folder). A corpus the run cannot read is a
        refusal by name (``refusal`` in the answer); a corpus that holds no
        document is kept as it was (``skipped_empty``, not emptied).
        The ``embedder_named`` flag says whether the run vectorized this
        pass or kept the text alone for the keyword."""
        from imasviz.VizAgent import rag_docs
        embedder = self._docsEmbedder()
        out = rag_docs.reindex(embedder=embedder)
        out['embedder_named'] = embedder is not None
        return out

    def search_documents(self, query, limit=8):
        """The corpus's rank: the one a ``search_documents`` asks of. The
        BM25 over the documents' chunks fused with the cosine of the query
        against the same (the ``rag_store``'s RRF), one hit per chunk (the
        document's ``rel``, the chunk's index, a snippet of its text). A
        corpus the run cannot read is a refusal by name; a search that
        hits no chunk is an ``empty`` the answer holds (not a crash, not a
        guess). The answer holds the ``method`` (``hybrid`` /
        ``embeddings`` / ``keyword`` / ``empty``) and, when a store's
        ``embed_sig`` is not the one the run is under, the ``guarded``
        flag with the ``guard_reason`` (vectors ignored, the keyword
        stands, and the reason names the embedder so a
        ``reindex_documents`` sets the two in step).
        """
        from imasviz.VizAgent import rag_docs
        embedder = self._docsEmbedder()
        return rag_docs.search(query, embedder=embedder, limit=limit)

    def documents_stats(self):
        """The state of the corpus: how many documents and chunks it
        holds, its ``embed_sig`` and ``dim``, and its ``built_at``. A
        corpus the run cannot read (no folder) answers a ``refusal`` the
        caller reads as the one the index could not open, not a zero it
        would read as empty. The caller reads those to decide the method a
        run will rank with (index then keyword, embeddings then keyword),
        and one ``reindex_documents`` sets the two in step."""
        from imasviz.VizAgent import rag_docs
        return rag_docs.stats()

    def add_note(self, scope, text, author=None, machine=None,
                 campaign=None, shot=None, date=None, title=None):
        """One new note in one journal.

        The author is required on every write: ``author`` named by the
        caller, or ``$USER`` when the caller left it out — a run with
        no ``$USER`` and no ``author`` is a named refusal, because a
        writer it cannot attribute to is one the journal does not hold.
        A note with no body is the same refusal, and the file is not
        written: the shape the journal does not hold is not one the
        write will cost.
        """
        from imasviz.VizAgent import journals
        answer = journals.JournalStore.add_note(
            scope, text, author=author, machine=machine, campaign=campaign,
            shot=shot, date=date, title=title)
        # The eager index on the write: the note is in the journal's store
        # the same turn it is on the disk, so the next search of it ranks
        # the body the writer just wrote (the ``add_note`` of the run is
        # the one the index answers, not one it recomputes on the read).
        # A store the run cannot keep in step (the shared folder not
        # named, the embedder refused) is logged and the write stands:
        # the note is on the disk the writers hold, and the read falls to
        # the keyword the journal ranks while the index is not in step.
        self._syncJournalWrite(scope, answer, kind='add')
        return answer

    def edit_note(self, scope, note_id, text=None, author=None, machine=None,
                  campaign=None, shot=None, date=None, title=None):
        """One note of one journal, changed in place: the note keeps the
        id the other writers read it under, and the fields the caller
        names take the place of the ones it held (a field left out
        keeps the one it held, an empty one clears it — except the
        author and the body, the two a note does not go without:
        an edit that empties either is the named refusal the add does
        not take, and the note on disk is not touched)."""
        from imasviz.VizAgent import journals
        answer = journals.JournalStore.edit_note(
            scope, note_id, text=text, author=author, machine=machine,
            campaign=campaign, shot=shot, date=date, title=title)
        # The eager index on the edit: the row keeps the id the edit kept,
        # and its text is the one the edit wrote (re-embedded when the body
        # moved, kept when it did not — the ``rag_store.upsert`` rule).
        self._syncJournalWrite(scope, answer, kind='edit')
        return answer

    def delete_note(self, scope, note_id):
        """One note of one journal, gone: the file and the row the index
        holds for it. Not in the journal is a named refusal, naming the
        ids it does hold, and the same rule the write is: a note the run
        deleted is one the next search does not rank, because its file
        is not there."""
        from imasviz.VizAgent import journals
        answer = journals.JournalStore.delete_note(scope, note_id)
        # The eager index on the delete: the row leaves the journal's store
        # the same turn the note's file does, so the next search does not
        # rank the line the writer took out (the note the run deleted is
        # one the index dropped, not one it recomputes).
        note_id = answer.get('id', note_id)
        try:
            from imasviz.VizAgent import journals_index
            journals_index.removeNote(scope, note_id)
        except Exception as e:
            import logging
            logging.getLogger('logPanel').info(
                'the %s journal could not drop its index row for %s: %s '
                '(the note itself is gone from the disk the writers hold)'
                % (scope, note_id, e))
        return answer

    def _promptContext(self):
        """What this session already knows, under the names a prompt's
        holes may carry: ``case``, ``uri``, ``shot``, ``run``,
        ``database``, ``figure``.

        This is what makes re-running a prompt cost no typing: the shot
        the user is looking at is the shot the prompt means, and it is
        read off the case the session has open —
        ``QVizIMASDataSource._readCaseFromUri`` is the one place a URI
        spells a case, so the number comes from the case, not from what a
        model recalls of the session. ``figure`` is the key of the one
        figure window the session holds, the same key the *Windows* menu
        and the other gestures take.

        Nothing is guessed: with two cases open, ``case``/``uri``/``shot``
        /``run``/``database`` are left unanswered — which one the prompt
        means is not said, so the user is asked for the value instead of
        getting the first view the walk reached. The reason is in
        ``note``, and the fill shows it.
        """
        out = {}
        note = []
        views = []
        try:
            views = list(self.api.DTVlist)
        except AttributeError:
            views = []
        if len(views) == 1:
            uri = views[0].dataSource.uri
            from imasviz.VizDataSource.QVizIMASDataSource import (
                _readCaseFromUri, caseLabel)
            database, shot, run = _readCaseFromUri(uri)
            out['uri'] = uri
            out['case'] = caseLabel(uri)
            for name, value in (('database', database), ('shot', shot),
                                ('run', run)):
                if value is not None:
                    out[name] = str(value)
        elif len(views) > 1:
            note.append('%d cases are open, so the prompt cannot be told '
                        'which one it means: name %s yourself.'
                        % (len(views), ', '.join(
                            '{%s}' % name for name in
                            ('case', 'uri', 'shot', 'run', 'database'))))
        else:
            note.append('no case is open, so the session answers no case '
                        'value: name the one the prompt means.')
        try:
            keys = [one['key'] for one in self.list_windows()
                    if one['kind'] != 'Agent']
        except Exception:
            keys = []
        if len(keys) == 1:
            out['figure'] = keys[0]
        elif keys:
            note.append('%d windows are open (%s), so the figure the '
                        'prompt means is not said: name {figure} yourself.'
                        % (len(keys), ', '.join(keys[:8])))
        else:
            note.append('no window is open, so the session answers no '
                        '{figure}.')
        if note:
            out['note'] = ' '.join(note)
        return out

    def list_prompts(self, scope=None, category=None, query=None,
                     limit=100):
        """The catalogue: the prompts the user can ask again, and what
        each one is.

        One entry per prompt — its id (what a gesture takes), its display
        name, its category, its one-line description, its holes and their
        defaults — category first then name, so the list reads as the
        catalogue the user wrote. ``category`` and ``query`` narrow it;
        ``query`` is read against the name, the description, the category
        and the id, because a reader remembers a word of the description,
        not the id. ``categories`` answers how many prompts each category
        holds — the filter the page and the panel build their chips from.
        ``context`` says what this session would answer for free.

        ``scope`` is the personal catalogue, the shared one
        (``SharedPromptsDir``), or both — the default. A shared catalogue
        with no folder named is not a refusal of the list: the personal
        prompts still answer, and the reason the shared half is missing is
        in ``catalogues_unavailable``, not left out.
        """
        from imasviz.VizAgent import prompts
        entries = prompts.PromptStore.list_prompts(scope=scope,
                                                   category=category,
                                                   query=query)
        out = {
            'prompts': [one.asLine() for one in entries[:int(limit)]],
            'total': len(entries),
            'categories': prompts.PromptStore.categories(scope=scope),
            'context': self._promptContext(),
        }
        unavailable = prompts.PromptStore.unavailable(scope)
        if unavailable:
            out['catalogues_unavailable'] = unavailable
        if len(entries) > int(limit):
            out['truncated'] = (
                '%d of %d prompts are answered: raise `limit` or narrow '
                'the ask.' % (int(limit), len(entries)))
        return out

    def prompt_detail(self, name, scope=None):
        """One prompt of the catalogue, whole: its body, its holes, and
        where each value would come from if it were asked right now.

        ``name`` is the id or the display name — a catalogue is read out
        loud ("relance Profils du plat-top"), and the answer names both.
        A name two prompts carry is refused naming their ids, never
        answered with the first one the walk reached.

        The ``values`` preview is not a guess and not a fill: it answers,
        per hole, the value the four sources would give (what the user
        named last time, what this session knows, what the file declares)
        and ``null`` for the holes that still need typing. Nothing is
        remembered by this call — asking what a prompt would answer is not
        typing an answer in.
        """
        from imasviz.VizAgent import prompts
        entry = prompts.PromptStore.find(name, scope=scope)
        context = self._promptContext()
        answer = entry.asDict()
        answer['values'] = prompts.resolveValues(entry, context=context,
                                                 remember=False)
        answer['context'] = context
        return answer

    def fill_prompt(self, name, values=None, scope=None):
        """The prompt as it will be asked, its holes filled — and nothing
        run.

        This is what a catalogue click costs: the page puts the text in
        its box or sends it as a turn, the panel puts it in its box, the
        client runs it. Filling is the gesture because running from here
        would stand inside the agent's own loop and ask it a second turn,
        which is not what a button asks.

        A hole is filled from the first source that answers it — what this
        call names, what was typed last time for that prompt, what this
        session knows, what the file declares — and the answer says which
        one it was, because a value the user did not type is a value they
        are entitled to see. A hole none of them answers is a refusal
        naming the holes that are still empty: a prompt is not sent with
        ``{shot}`` in it, and not sent with a guess in its place. The
        values this call names are kept for the next one (locally, never
        in the shared catalogue).
        """
        from imasviz.VizAgent import prompts
        entry = prompts.PromptStore.find(name, scope=scope)
        answers = prompts.resolveValues(entry, given=values,
                                        context=self._promptContext())
        filled = dict((name, one['value']) for name, one in answers.items()
                      if one['value'] is not None)
        text = prompts.fillTemplate(entry.body, filled)
        return {
            'id': entry.id, 'name': entry.name, 'scope': entry.scope,
            'category': entry.category, 'text': text, 'values': answers,
        }

    def save_prompt(self, name, text, category=None, description=None,
                    variables=None, scope='personal', prompt_id=None):
        """One prompt into the catalogue, under a name and a description.

        The prompt a turn just ran is the one worth filing: the user asks
        for it once, the wording works, and the next run should not have
        to type it again — which is what ``save_prompt`` is asked of on an
        explicit ask, never on a turn that merely drew something (the rule
        the shared journal's write answers by, for the same reason: it is
        a line other people read).

        ``variables`` left out is read off the text: every ``{hole}`` it
        opens, with no default. The hole is then asked for on every run,
        which is the safe reading of a prompt the user filed in a hurry.
        A hole declared and never opened in the text is refused by name.
        The shared catalogue is written to only when ``scope='shared'``
        and ``SharedPromptsDir`` names a folder — a write silently filed
        in the personal folder is a prompt its author believes shared.
        """
        from imasviz.VizAgent import prompts
        entry = prompts.PromptStore.add_prompt(
            text, name=name, category=category, description=description,
            variables=variables, scope=scope, prompt_id=prompt_id)
        return entry.asDict()

    def edit_prompt(self, name, text=None, category=None, description=None,
                    variables=None, scope=None):
        """One prompt of the catalogue, changed in place: it keeps the id
        the pages, the sessions and the remembered values read it under.

        A field left out keeps the one the prompt held; a field named
        takes the place of the one it held; an empty one clears it. The
        body is the one field an edit cannot empty, and the id is not a
        field an edit moves — a new prompt is ``save_prompt``.
        """
        from imasviz.VizAgent import prompts
        entry = prompts.PromptStore.find(name, scope=scope)
        changed = prompts.PromptStore.edit_prompt(
            entry.scope, entry.id, body=text, category=category,
            description=description, variables=variables)
        return changed.asDict()

    def delete_prompt(self, name, scope=None):
        """One prompt out of the catalogue, and the values remembered for
        it. Not there is a refusal naming the ids the catalogue holds."""
        from imasviz.VizAgent import prompts
        entry = prompts.PromptStore.find(name, scope=scope)
        return prompts.PromptStore.delete_prompt(entry.scope, entry.id)
