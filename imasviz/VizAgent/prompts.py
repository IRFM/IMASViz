# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The prompt catalogue: the prompts a run asks again, with their variables.

``QVizPromptHistory`` keeps what a run *typed*, newest first, and nothing
else: it holds no category, no description, no variable, and a prompt one
run liked is not recallable by name by the next one. The catalogue is the
other thing — a prompt the user wrote once, named, described, categorised,
and re-runnable by typing only what changes in it.

A prompt is a file, the way a note is:
:file:`$HOME/.imasviz/prompts/<id>.md`, and the shared one under the
folder :file:`QVizPreferences.SharedPromptsDir` names (an AFS path, the
rule ``SharedJournalDir`` points at — an unnamed one is a refusal by
name). A short ``key: value`` front matter (``name``, ``category``,
``description``, ``variables``, ``author``), a blank line, then the body —
the prompt as it is asked, with its holes spelled ``{shot}``. The file is
the catalogue: a prompt added by hand in the folder is in the list on the
next read, and a prompt the list names is a file the user can read, edit
under another editor, and keep in their own version control.

The holes
--------

``{name}`` is a variable when ``name`` is a bare identifier
(``[a-z][a-z0-9_]*``) and nothing else: a brace that carries a space, a
quote or a dot is text the prompt says out loud (a JSON snippet in a
prompt stays a JSON snippet), so no escaping rule is needed and no
sentence is silently eaten.

The front matter declares them: ``variables: ids=core_profiles; shot=``
— ``key=value`` pairs separated by ``;``, the spelling an IMAS URI's
parameters already use. A declared name carries its default; an empty
default (``shot=``) or a bare name (``shot``) is a hole that has to be
answered before the prompt runs.

A value comes from one of four places, in this order, and the answer
names which one it was:

1. what the caller named for this run;
2. what the caller last typed for that prompt (the sidecar below);
3. what the session already knows (``case``, ``uri``, ``shot``, ``run``,
   ``database``, ``figure``) — the case open in front of the user, read
   off its URI, which is what makes a rerun cost no typing at all;
4. the default the file declares.

A hole none of the four answers is a refusal naming the holes that are
still empty: a prompt asked half-filled is not run on a guess.

The sidecar
-----------

The last values typed live in :file:`$HOME/.imasviz/prompt_values.json`,
one entry per prompt, keyed ``scope/id``. They are **local** even for a
prompt of the shared catalogue: the folder the team shares is not the
place one user's shot number goes to live, and a write there would make a
rerun mean different things to different people.
"""

import json
import os
import re

FRONT_MATTER_KEYS = ('name', 'category', 'description', 'variables',
                     'author')

# The id is the file name without its extension, under the same guard a
# note id holds (``journals._ID_RE``): the name a write spells is the
# name a read answers, and a name that escapes the folder is refused
# before the folder is looked at.
_ID_RE = re.compile(r'^[a-z0-9][a-z0-9_\-]{0,63}$')

# A hole is a bare identifier between braces. Anything else between
# braces is text the prompt says.
_VAR_RE = re.compile(r'\{([a-z][a-z0-9_]*)\}')
_VAR_NAME_RE = re.compile(r'^[a-z][a-z0-9_]*$')

# The variables the session answers by itself, so a prompt written with
# them costs no typing on a rerun. The core is the one that knows them
# (it is the one standing in front of the open cases); this is the list
# they are named by, spelled once.
CONTEXT_VARIABLES = ('case', 'uri', 'shot', 'run', 'database', 'figure')

# The sidecar: the last values typed, per prompt, under the user's own
# folder — never under the shared catalogue's.
VALUES_FILENAME = 'prompt_values.json'


# ------------------------------------------------------------- the declaration

def parseVariables(declaration):
    """The declared holes, ``{name: default}``, in the order the file spells.

    ``ids=core_profiles; shot=`` answers ``{'ids': 'core_profiles', 'shot':
    ''}``. A bare name is a hole with no default, and an empty declaration
    is no hole at all. A pair that reads on neither side of the ``=`` is a
    refusal naming it: a declaration with a hole nobody can name is the
    one the fill cannot answer, and finding it at the fill is finding it
    too late.
    """
    out = {}
    for term in (declaration or '').split(';'):
        term = term.strip()
        if not term:
            continue
        name, sep, value = term.partition('=')
        name = name.strip()
        value = value.strip() if sep else ''
        if not _VAR_NAME_RE.match(name):
            raise ValueError(
                '"%s" is not the declaration of a variable: a variable is '
                'a bare name (lowercase letters, digits and _, starting '
                'with a letter), with an optional =value as its default.'
                % term)
        out[name] = value
    return out


def renderVariables(variables):
    """The declaration of the holes, the way ``parseVariables`` reads it back."""
    return '; '.join('%s=%s' % (name, value)
                     for name, value in (variables or {}).items())


def templateVariables(body):
    """The holes the body asks of, in the order it asks them, no name twice."""
    seen = []
    for match in _VAR_RE.finditer(body or ''):
        if match.group(1) not in seen:
            seen.append(match.group(1))
    return seen


def fillTemplate(body, values):
    """The body with its holes filled.

    A hole ``values`` does not answer is a refusal naming the holes that
    are still empty — the prompt is not sent with ``{shot}`` in it and is
    not sent with a guess in its place. A brace that is not a bare
    identifier is left exactly where it is.
    """
    missing = [name for name in templateVariables(body)
               if values.get(name) in (None, '')]
    if missing:
        raise ValueError(
            'the prompt still names %d hole(s) nobody answered: %s — give '
            'their values, or take them out of the prompt.'
            % (len(missing), ', '.join('{%s}' % name for name in missing)))
    return _VAR_RE.sub(lambda m: str(values[m.group(1)]), body or '')


# ------------------------------------------------------------------ the file

def _parseFrontMatter(text):
    """The front matter of one prompt, or ``(None, text)`` when the file
    is not a prompt of this catalogue.

    The shape ``QVizPromptHistory`` and the journal answer: a ``key:
    value`` block, one field per line, a blank line, then the body. A
    field the block spells but the catalogue does not ask of is not a
    prompt — the file was written for something else, and reading it as
    one would put a stranger in the catalogue.
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
        if key not in FRONT_MATTER_KEYS:
            return None, text
        fields[key] = value.strip()
    body = '\n'.join(lines[index + 1:]).strip()
    if not body:
        # A prompt with nothing to ask is not a prompt: a catalogue line
        # that leads to an empty turn is the one the user clicks in vain.
        return None, text
    return fields, body


def _renderPrompt(name, category, description, variables, author, body):
    """One prompt to file: the fields the catalogue asks of, only the ones
    it names, then the body."""
    lines = []
    if name:
        lines.append('name: %s' % name)
    if category:
        lines.append('category: %s' % category)
    if description:
        lines.append('description: %s' % description)
    if variables:
        lines.append('variables: %s' % variables)
    if author:
        lines.append('author: %s' % author)
    lines.append('')
    lines.append(body)
    return '\n'.join(lines) + '\n'


class PromptEntry:
    """One prompt of the catalogue, and the asks made of it."""

    def __init__(self, id, scope, path, name, category, description,
                 variables, author, body, mtime=0, variables_refusal=None):
        self.id = id
        self.scope = scope
        self.path = path
        self.name = name or id
        self.category = category or ''
        self.description = description or ''
        self.variables = variables or {}
        self.author = author or ''
        self.body = body
        self.mtime = mtime
        self.variables_refusal = variables_refusal

    def key(self):
        """The one name a value is remembered under."""
        return '%s/%s' % (self.scope, self.id)

    def holes(self):
        """Every hole this prompt asks of: the declared ones, plus the ones
        the body opens and nobody declared. The second half is what a
        ``fill_prompt`` answers as a refusal when the session does not
        know the name either — a hole that is in neither the declaration
        nor the context is a typo the catalogue would otherwise run as
        text."""
        names = list(self.variables)
        for name in templateVariables(self.body):
            if name not in names:
                names.append(name)
        return names

    def asLine(self):
        """One line of the catalogue: what a reader chooses on."""
        line = {
            'id': self.id,
            'scope': self.scope,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'variables': dict(self.variables),
            'holes': self.holes(),
            'author': self.author or None,
            'path': self.path,
        }
        if self.variables_refusal:
            # A prompt whose declaration does not parse is still listed —
            # and the line says so, instead of answering no hole at all
            # for a file the user is in the middle of editing.
            line['variables_refusal'] = self.variables_refusal
        return line

    def asDict(self):
        """The whole prompt, the body included — what an edit form fills
        itself from."""
        line = self.asLine()
        line['text'] = self.body
        return line


# -------------------------------------------------------------------- store

class PromptStore:
    """The two catalogues and their prompts, on disk.

    ``scope='personal'`` is :file:`$HOME/.imasviz/prompts`, the one the
    user's own; ``scope='shared'`` is the folder
    :file:`SharedPromptsDir` names, the one a team shares, unreadable
    until it is named; ``scope=None`` (or ``both``) is the two asked at
    once — the list reads both, and an unnamed shared folder is a reason
    kept by ``unavailable`` and said in the answer, not a refusal of the
    list: the personal prompts still answer. The one write that names
    ``shared`` and gets nothing to write into is refused, because a write
    silently filed in the personal folder is a prompt its author believes
    shared.
    """

    @staticmethod
    def personalDirectory():
        home = os.environ.get('HOME')
        if not home:
            raise ValueError(
                'No HOME in the environment: the prompt catalogue has no '
                'folder to sit under.')
        folder = os.path.join(home, '.imasviz', 'prompts')
        os.makedirs(folder, exist_ok=True)
        return folder

    @staticmethod
    def sharedDirectory():
        from imasviz.VizUtils import QVizPreferences
        path = (QVizPreferences.SharedPromptsDir or '').strip()
        if not path:
            raise ValueError(
                'The shared prompt catalogue has no folder named: set '
                'SharedPromptsDir in ~/.imasviz/preferences to point it at '
                'a shared directory (AFS) the writers can reach. The '
                'personal one is under ~/.imasviz/prompts.')
        folder = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(folder):
            raise ValueError(
                'The shared prompt catalogue named "%s" is not a '
                'directory: create it, or name one that is.' % folder)
        return folder

    @classmethod
    def folderFor(cls, scope):
        if scope == 'personal':
            return cls.personalDirectory()
        if scope == 'shared':
            return cls.sharedDirectory()
        raise ValueError(
            '"scope=%r" is not a catalogue: its two are personal and '
            'shared.' % scope)

    @staticmethod
    def _scopes(scope):
        if scope in (None, 'both'):
            return ('personal', 'shared')
        if scope in ('personal', 'shared'):
            return (scope,)
        raise ValueError(
            '"scope=%r" is not a catalogue: its two are personal and '
            'shared (or both / left out for the two asked at once).'
            % scope)

    @staticmethod
    def _promptPath(folder, prompt_id):
        """The file of one prompt, under the guard a note id holds: a name
        that escapes the folder, and a shape the writer does not spell, are
        refused before the folder is looked at."""
        prompt_id = (prompt_id or '').strip()
        if not prompt_id:
            raise ValueError('a prompt id is a name, not the empty string.')
        if os.path.sep in prompt_id or '/' in prompt_id or '\\' in prompt_id \
                or prompt_id in ('.', '..') or prompt_id.startswith('.'):
            raise ValueError(
                '"%s" names a place, not a prompt: name one inside %s (a '
                'prompt is its file name, without the extension).'
                % (prompt_id, folder))
        if not _ID_RE.match(prompt_id):
            raise ValueError(
                '"%s" is not the id of a prompt: a prompt id is lowercase '
                'letters, digits, _ and -, at most 64 characters, leading '
                'with a letter or a digit and never with a -.' % prompt_id)
        path = os.path.join(folder, prompt_id + '.md')
        if os.path.dirname(os.path.realpath(path)) != os.path.realpath(folder):
            raise ValueError('"%s" would be read outside %s.'
                             % (prompt_id, folder))
        return path

    @staticmethod
    def _entryPath(folder, prompt_id):
        """The file of one prompt whose id was not spelled as this writer
        spells it.

        A prompt added by hand in the folder carries whatever name the
        hand gave it, and the catalogue reads it: the guard above refuses
        a *name that escapes the folder*, not a name this writer would not
        have written. So a read of a file already there goes through this,
        and a write still goes through ``_promptPath`` — the two are not
        the same ask, and holding one guard for both is how a catalogue
        entry the user wrote by hand becomes unreachable.
        """
        prompt_id = (prompt_id or '').strip()
        if not prompt_id or prompt_id in ('.', '..') \
                or os.path.sep in prompt_id or '/' in prompt_id \
                or '\\' in prompt_id or prompt_id.startswith('.'):
            raise ValueError(
                '"%s" names a place, not a prompt: name one inside %s (a '
                'prompt is its file name, without the extension).'
                % (prompt_id, folder))
        path = os.path.join(folder, prompt_id + '.md')
        if os.path.dirname(os.path.realpath(path)) != os.path.realpath(folder):
            raise ValueError('"%s" would be read outside %s.'
                             % (prompt_id, folder))
        return path

    # ------------------------------------------------------------------ read

    @classmethod
    def unavailable(cls, scope=None):
        """The catalogues the scope asks of that cannot be read, each with
        the reason it gives (``{'shared': '…'}`` while
        :file:`SharedPromptsDir` is unnamed).

        The list keeps reading the ones that answer: an unnamed shared
        folder costs its own catalogue, not the question the user asked.
        This is where the reason is kept so the answer can say it instead
        of answering a shorter list than the one that was asked for.
        """
        out = {}
        for sc in cls._scopes(scope):
            try:
                cls.folderFor(sc)
            except ValueError as e:
                out[sc] = str(e)
        return out

    @classmethod
    def list_prompts(cls, scope=None, category=None, query=None):
        """The prompts of the catalogue(s), category first then name.

        ``scope=None`` is the union of the two catalogues. ``category``
        narrows to the prompts that name it — compared case-insensitively,
        because a reader types a word, not a spelling. ``query`` narrows
        to the prompts whose name, description, category or id carries it.
        Empty is an answer, and an unnamed shared catalogue is skipped
        with its reason kept by ``unavailable``, not a refusal of the list.
        """
        entries = []
        for sc in cls._scopes(scope):
            try:
                folder = cls.folderFor(sc)
            except ValueError:
                continue
            for fileName in sorted(os.listdir(folder)):
                if not fileName.endswith('.md') or fileName.startswith('.'):
                    continue
                path = os.path.join(folder, fileName)
                if not os.path.isfile(path):
                    continue
                entry = cls._load(sc, fileName[:-3], path)
                if entry is not None:
                    entries.append(entry)
        if category:
            wanted = category.strip().lower()
            entries = [e for e in entries if e.category.lower() == wanted]
        if query:
            wanted = query.strip().lower()
            entries = [e for e in entries
                       if wanted in ' '.join((e.name, e.description,
                                              e.category, e.id)).lower()]
        entries.sort(key=lambda e: (0 if e.category else 1,
                                    e.category.lower(), e.name.lower()))
        return entries

    @staticmethod
    def _load(scope, prompt_id, path):
        """One prompt off its file, or ``None`` when the file is not a
        prompt of this catalogue (the front matter a stranger wrote, or a
        body with nothing to ask)."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
        except OSError:
            return None
        fields, body = _parseFrontMatter(text)
        if fields is None:
            return None
        refusal = None
        try:
            variables = parseVariables(fields.get('variables'))
        except ValueError as bad:
            # The prompt is kept and its declaration is named as broken:
            # the holes the body opens are still asked for, so a file the
            # user is mid-way through editing costs its own defaults and
            # not the catalogue around it.
            refusal = str(bad)
            variables = {}
        return PromptEntry(
            id=prompt_id, scope=scope, path=path,
            name=fields.get('name'), category=fields.get('category'),
            description=fields.get('description'), variables=variables,
            author=fields.get('author'), body=body,
            mtime=int(os.path.getmtime(path)),
            variables_refusal=refusal)

    @classmethod
    def read_prompt(cls, scope, prompt_id):
        """One prompt of one catalogue, by its id. Not there is a refusal
        naming the ids the catalogue does hold; a file that is not a
        prompt is refused for what it is."""
        folder = cls.folderFor(scope)
        path = cls._entryPath(folder, prompt_id)
        if not os.path.isfile(path):
            held = sorted(name[:-3] for name in os.listdir(folder)
                          if name.endswith('.md') and not name.startswith('.'))
            raise ValueError(
                'No prompt "%s" in the %s catalogue: it holds %s.'
                % (prompt_id, scope, ', '.join(held) or 'none at all'))
        entry = cls._load(scope, prompt_id, path)
        if entry is None:
            raise ValueError(
                '"%s" is in the %s catalogue but is not a prompt this '
                'shape answers: its front matter names a field the '
                'catalogue does not ask of, or it has nothing to ask.'
                % (prompt_id, scope))
        return entry

    @classmethod
    def find(cls, name, scope=None):
        """The one prompt a caller names — by its id or by its display name.

        A catalogue is read out loud ("relance Profils du plat-top"), and
        the id the file carries is what a gesture takes, so the two are
        resolved here, once. An id wins when the catalogue holds one by
        that name; then a display name matched case-insensitively. A name
        two prompts carry is a refusal naming both ids, never the first
        one the walk reached.
        """
        wanted = (name or '').strip()
        if not wanted:
            raise ValueError('a prompt is named by its id or its name, not '
                             'by nothing at all.')
        entries = cls.list_prompts(scope=scope)
        for entry in entries:
            if entry.id == wanted:
                return entry
        lowered = wanted.lower()
        same = [e for e in entries
                if e.name.lower() == lowered or e.id.lower() == lowered]
        if len(same) == 1:
            return same[0]
        if len(same) > 1:
            raise ValueError(
                '"%s" is the name of %d prompts: %s — name the one you '
                'mean by its id.'
                % (wanted, len(same),
                   ', '.join('%s (%s)' % (e.id, e.scope) for e in same)))
        held = ', '.join('%s (%s)' % (e.id, e.scope) for e in entries[:20])
        raise ValueError(
            'no prompt "%s" in %s. The catalogue holds: %s'
            % (wanted, 'the catalogues' if scope in (None, 'both')
               else 'the %s catalogue' % scope, held or 'no prompt at all'))

    @classmethod
    def categories(cls, scope=None):
        """The categories the catalogue holds, with how many prompts each
        answers — what the filter chips are built from. Uncategorised
        prompts are the ``''`` entry, said as such by the caller."""
        counts = {}
        for entry in cls.list_prompts(scope=scope):
            counts[entry.category] = counts.get(entry.category, 0) + 1
        return counts

    # ----------------------------------------------------------------- write

    @classmethod
    def add_prompt(cls, body, name=None, category=None, description=None,
                   variables=None, scope='personal', prompt_id=None,
                   author=None):
        """One new prompt in one catalogue, and the entry it wrote.

        The body is the one thing a prompt cannot go without: a catalogue
        line that leads to an empty turn is a click the user paid for
        nothing. The id is the slug of the name unless the caller names
        one, and a catalogue that already holds it is a refusal — a second
        prompt filed over the first is a prompt lost to a typo in a name.
        """
        if scope not in ('personal', 'shared'):
            raise ValueError(
                '"scope=%r" is not a catalogue: its two are personal and '
                'shared.' % scope)
        body = (body or '').strip()
        if not body:
            raise ValueError(
                'A prompt needs what it asks: the body named for it is '
                'empty, and a catalogue line that leads to an empty turn '
                'is not one this catalogue holds.')
        folder = cls.folderFor(scope)
        name = (name or '').strip()
        prompt_id = (prompt_id or '').strip() or _slug(name) or 'prompt'
        path = cls._promptPath(folder, prompt_id)
        if os.path.exists(path):
            raise ValueError(
                'The %s catalogue already holds a prompt "%s" (in %s): '
                'name this one differently, or edit the one it is — '
                'manage_prompt(action="edit") changes a prompt in place.'
                % (scope, prompt_id, path))
        declared = _declarationOf(variables, body)
        rendered = _renderPrompt(name, (category or '').strip(),
                                 (description or '').strip(), declared,
                                 (author or os.environ.get('USER')
                                  or '').strip(), body)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(rendered)
        return cls.read_prompt(scope, prompt_id)

    @classmethod
    def edit_prompt(cls, scope, prompt_id, body=None, name=None,
                    category=None, description=None, variables=None,
                    author=None):
        """One prompt, changed in place: the file keeps its name.

        The id is the name the catalogues, the sessions and the remembered
        values read a prompt under, and an edit does not move it. A field
        left out (``None``) keeps the one the prompt held; a field named
        replaces it; an empty string clears it. The body is the one field
        an edit cannot empty.
        """
        current = cls.read_prompt(scope, prompt_id)
        folder = cls.folderFor(scope)
        body_v = current.body if body is None else (body or '').strip()
        if not body_v:
            raise ValueError(
                'A prompt keeps what it asks: the edit named an empty body '
                'for "%s", and a catalogue line with nothing to ask is not '
                'one this catalogue holds.' % prompt_id)
        name_v = current.name if name is None else name.strip()
        category_v = current.category if category is None else category.strip()
        desc_v = (current.description if description is None
                  else description.strip())
        author_v = current.author if author is None else author.strip()
        # An edit that keeps the declaration still has to answer for it: an
        # edit that takes a hole out of the body would leave behind a
        # declaration the next fill asks for and never fills.
        declared = _declarationOf(current.variables if variables is None
                                  else variables, body_v)
        path = cls._entryPath(folder, prompt_id)
        rendered = _renderPrompt(name_v, category_v, desc_v, declared,
                                 author_v, body_v)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(rendered)
        return cls.read_prompt(scope, prompt_id)

    @classmethod
    def delete_prompt(cls, scope, prompt_id):
        """One prompt out of one catalogue. Not there is a refusal naming
        what the catalogue does hold, the same answer the read gives."""
        entry = cls.read_prompt(scope, prompt_id)
        os.remove(entry.path)
        forgetValues(entry.key())
        return {'deleted': entry.id, 'scope': scope, 'path': entry.path}


def _declarationOf(variables, body):
    """The ``variables:`` line a write spells.

    ``variables`` is the declaration as a dict, as a string the caller
    spells, or ``None`` — and then it is read off the body: every hole it
    opens that the body opens and nothing else. A prompt written from a
    panel that only names its holes gets a declaration the next read can
    answer, and a hole the body does not open is refused by name rather
    than filed as a declaration of nothing — asked of the same rule whatever
    shape the declaration came in, because a declared hole the body never
    opens is one ``holes()`` keeps asking for and ``fillTemplate`` never
    fills.
    """
    if isinstance(variables, str):
        declaration = variables.strip()
        declared = parseVariables(declaration)
    elif isinstance(variables, dict):
        declared = parseVariables(renderVariables(variables))
        declaration = renderVariables(declared)
    else:
        declared = dict.fromkeys(templateVariables(body), '')
        declaration = renderVariables(declared)
    opened = templateVariables(body)
    unknown = [name for name in declared if name not in opened]
    if unknown:
        raise ValueError(
            'the prompt asks none of %s: its body opens %s — a declared '
            'hole the body never opens is a hole nobody is ever asked '
            'for.'
            % (', '.join('{%s}' % name for name in unknown),
               ', '.join('{%s}' % name for name in opened) or 'no hole at '
                                                              'all'))
    return declaration


def _slug(text, limit=48):
    """The id the name leads with: lowercase alpha-num and dashes."""
    text = (text or '').strip().lower()
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    if len(text) > limit:
        text = text[:limit].rstrip('-')
    return text


# ----------------------------------------------------------- remembered values

def valuesPath():
    """The sidecar of the last values typed, under the user's own folder."""
    home = os.environ.get('HOME')
    if not home:
        raise ValueError(
            'No HOME in the environment: there is no folder to remember a '
            'prompt\'s last values in.')
    folder = os.path.join(home, '.imasviz')
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, VALUES_FILENAME)


def lastValues():
    """The values a run typed last time, ``{'personal/id': {name: value}}``.
    A file that is not one is refused by what it is, the way every other
    read in the repository is."""
    path = valuesPath()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise ValueError(
            '"%s" is not the remembered prompt values: %s.' % (path, e))
    if not isinstance(raw, dict) or not all(
            isinstance(one, dict) for one in raw.values()):
        raise ValueError(
            '"%s" is not the remembered prompt values: it is not one '
            'object of per-prompt objects of values.' % path)
    return raw


def rememberValues(promptKey, values):
    """The values this run typed for one prompt, kept for the next one.

    Only the values the caller named, and only in the user's own folder:
    a prompt of the shared catalogue gets its last values remembered
    locally, so a rerun of a team prompt costs the same typing for the
    person who typed it and none of it for anybody else.
    """
    kept = {str(name): str(value) for name, value in (values or {}).items()}
    if not kept:
        return {}
    stored = lastValues()
    stored[promptKey] = kept
    with open(valuesPath(), 'w', encoding='utf-8') as f:
        f.write(json.dumps(stored, ensure_ascii=False, indent=2,
                           sort_keys=True) + '\n')
    return kept


def forgetValues(promptKey):
    """The remembered values of one prompt, gone with it."""
    stored = lastValues()
    if promptKey not in stored:
        return {}
    del stored[promptKey]
    with open(valuesPath(), 'w', encoding='utf-8') as f:
        f.write(json.dumps(stored, ensure_ascii=False, indent=2,
                           sort_keys=True) + '\n')
    return stored


# ------------------------------------------------------------------ the fill

CALLED = 'you named it'
REMEMBERED = 'the last value you typed for this prompt'
SESSION = 'this session'
DEFAULT = 'the prompt\'s own default'


def resolveValues(entry, given=None, context=None, remember=True):
    """The values one fill answers, and where each one came from.

    ``{'name': {'value': …, 'source': …}}``, one entry per hole the prompt
    opens. The order is the one the module docstring spells: what this
    call names, then what the last call of that prompt typed, then what
    the session knows, then the default the file declares. A hole none of
    the four answers comes back with ``value`` ``None``, and ``fill``
    turns it into a refusal naming the holes — the caller sees both the
    hole and its answer in the same answer.

    ``context`` is the handful of names the session knows (the open case
    and its shot, the figure keys): the caller — the core — is the one
    standing in front of them, and the store never asks a window.
    """
    given = dict(given or {})
    context = dict(context or {})
    try:
        remembered = lastValues().get(entry.key(), {})
    except ValueError:
        # A sidecar that does not parse is a reason not to remember, not
        # a reason not to run the prompt the user chose. The refusal is
        # the caller's to say, and the fill goes on without it.
        remembered = {}
    answers = {}
    for name in entry.holes():
        if name in given and str(given[name]).strip() != '':
            answers[name] = {'value': str(given[name]).strip(),
                             'source': CALLED}
            continue
        old = str(remembered.get(name) or '').strip()
        if old:
            answers[name] = {'value': old, 'source': REMEMBERED}
            continue
        known = str(context.get(name) or '').strip()
        if known:
            answers[name] = {'value': known, 'source': SESSION}
            continue
        default = str(entry.variables.get(name) or '').strip()
        if default:
            answers[name] = {'value': default, 'source': DEFAULT}
            continue
        answers[name] = {'value': None, 'source': None}
    unknown = sorted(name for name in given
                     if name not in entry.holes()
                     and str(given[name]).strip() != '')
    if unknown:
        raise ValueError(
            'the prompt asks none of %s: it opens %s — a value named for a '
            'hole that is not there is a name the prompt never wrote.'
            % (', '.join(unknown),
               ', '.join('{%s}' % name for name in entry.holes())
               or 'no hole at all'))
    if remember:
        typed = {name: one['value'] for name, one in answers.items()
                 if one['source'] == CALLED}
        if typed:
            rememberValues(entry.key(), typed)
    return answers
