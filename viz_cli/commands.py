# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The `/` commands of the viz_cli REPL, parsed and answered by name.

What a command answers is named when it cannot answer: an unknown
command, an unknown `/llm` field, an unknown gesture after `/mcp`, a
non-http endpoint -- each refusal is a `ValueError` carrying the name
the caller typed and the names this client does hold, which is the
style the rest of the repository applies (`refused by name, the reason
named where the user reads it`).

Three of the fields `/llm` sets are the ones the GUI reads too --
`endpoint`, `model`, `key`: they are written in the **same**
preferences file the application builds from (`QVizPreferences.persist`,
the file `~/.imasviz/preferences`), so the two interfaces stay on the
same endpoint. The loop's own parameters (`max_turns`, `temperature`,
`max_tokens`) steer this client run only, and say so when they are set;
they have no line in that file, and inventing one would cost the GUI a
line it does not read.
"""

import json
import urllib.error
import urllib.request

from imasviz.VizAgent.QVizPromptHistory import QVizPromptHistory

COMMANDS = ('llm', 'mcp', 'ids', 'shots', 'session', 'history', 'tools',
            'note', 'help', 'quit')

LLM_FIELDS = ('endpoint', 'model', 'key', 'max_turns', 'temperature',
              'max_tokens')
LLM_FILE_FIELDS = {
    'endpoint': 'AgentLLMEndpoint',
    'model': 'AgentLLMModel',
    'key': 'AgentLLMApiKey',
}

HELP = """viz_cli — IMASViz driven without its window: the agent, offscreen.

A line runs the agent (the LLM and the {ntools} tools of this session);
the images it drew and its transcript are left in the turns directory,
named after the turn. Commands:

  /llm                       the parameters in force
  /llm endpoint URL          the model's endpoint, http://host:port/v1
  /llm model NAME            the model to send; 'auto' = the endpoint's
                             first /v1/models entry, read on first use
  /llm key TOKEN             sent as Authorization when non-empty
  /llm max_turns N           (this run only) the agent's turn limit
  /llm temperature X         (this run only) of every call it sends
  /llm max_tokens N          (this run only) of every call it sends
                             endpoint, model and key are persisted in the
                             preferences file the GUI reads; the others are not

  /mcp                       the services this session answers today:
                             the endpoint, its models, its tools
  /mcp NAME                  one tool: its words and its parameters
  /ids [URI]                 the IDS the open case actually holds, raw:
                             the names and their occurrences, read of the
                             case's entry (list_case_idss) with no LLM in
                             between. With no URI, the one open case
  /shots [DIR]               where the turns save their images
  /session                   the cases open in this session
  /session save NAME         the session the application writes
  /session restore NAME      put that session back
  /history                   the shared prompt history, newest first: the
                             prompts the panel, the web and the client's
                             arrows all recall
  /tools                     the transcript mode in force (hide, off,
                             verbose): the live view wears it, the file on
                             disk is still the full render
  /tools MODE                set it -- the panel, the web and the client
                             read the same one -- and persist it
  /note                      the two journals of this node: the folders,
                             the notes each answers, and whether an
                             embeddings endpoint is set
  /note search QUERY         the notes that fit the filters, ranked for
                             QUERY: --machine --campaign --shot
                             --date_from --date_to --author --scope
                             --limit
  /note list                 the notes that fit the filters, in date
                             order: the same flags as /note search
  /note read ID              the whole note by its ID (a search or a
                             list's answer names one)
  /note add SCOPE TEXT       a line in a journal: personal (the author's
                             own) or shared (the one the writers read),
                             with --author --machine --campaign --shot
                             --date --title
  /note delete ID            take a line out of a journal (the search or
                             the list answer names it)
  /help                      this text
  /quit                      leave; the arrows keep the prompts they
                             recall in ~/.imasviz/agent_prompts, with the
                             panel and the web

Ctrl+C during a turn stops it at the next turn boundary and still saves
what it drew.
""".format(ntools='<n>')


class Command:
    """One line the REPL has parsed: its name, and the words that follow."""
    def __init__(self, name, words):
        self.name = name
        self.words = words


def parse(line):
    """`/llm endpoint http://…` -> a `Command`; everything it cannot
    answer is refused by name, so a `/` line is never mistaken for a
    prompt and a prompt never mistaken for a `/banana`."""
    words = (line or '').split()
    if not words:
        raise ValueError(
            'an empty line no command answers: name one, /help lists them.')
    head = words[0]
    name = head[1:] if head.startswith('/') else head
    if name not in COMMANDS:
        raise ValueError(
            'unknown command /%s — the ones this client answers: %s.'
            % (name or '(empty)',
               ' '.join('/' + c for c in COMMANDS)))
    return Command(name, words[1:])


def help_text():
    """The `/help` answer, with the real count of the session's tools."""
    tools = _tools()
    return HELP.replace('<n>', str(len(tools)))


def _tools():
    """The tools the agent holds, by their schema -- the one source."""
    from imasviz.VizAgent.tools import TOOLS
    return TOOLS


def execute(cmd, session):
    """Run one command on one session. Returns `False` when the REPL
    leaves; every refusal is a `ValueError` the caller names out loud."""
    if cmd.name == 'help':
        print(help_text())
    elif cmd.name == 'quit':
        return False
    elif cmd.name == 'llm':
        _llm(cmd, session)
    elif cmd.name == 'mcp':
        _mcp(cmd, session)
    elif cmd.name == 'ids':
        _ids(cmd, session)
    elif cmd.name == 'shots':
        _shots(cmd, session)
    elif cmd.name == 'session':
        _session(cmd, session)
    elif cmd.name == 'history':
        _history(cmd, session)
    elif cmd.name == 'tools':
        _toolsMode(cmd, session)
    elif cmd.name == 'note':
        _note(cmd, session)
    return True


# --------------------------------------------------------------------- /llm

def _llm(cmd, session):
    if not cmd.words:
        _llmShow(session)
        return
    if len(cmd.words) != 2:
        raise ValueError(
            '/llm %s needs its value: /llm prints the ones in force, and '
            'its fields are %s.'
            % (cmd.words[0], ', '.join(LLM_FIELDS)))
    field, value = cmd.words
    if field == 'endpoint':
        if not value.startswith(('http://', 'https://')):
            raise ValueError(
                '%r is not an endpoint: name it as http://host:port/v1 '
                '(the one this client answers today: %s).'
                % (value, session.llm.endpoint))
        _setFileField(session, 'endpoint', value)
    elif field == 'model':
        _setFileField(session, 'model', '' if value == 'auto' else value)
        if value == 'auto':
            print('/llm — model = auto: the first entry of /v1/models is '
                  'the one sent on first use.', flush=True)
    elif field == 'key':
        _setFileField(session, 'key', value)
    elif field == 'max_turns':
        _setNumber(None, value, min=1)
        session.max_turns = int(value)
        print('/llm — max_turns = %s (this client run; not persisted).'
              % value, flush=True)
    elif field == 'temperature':
        try:
            number = float(value)
        except ValueError:
            raise ValueError('%r is not a temperature: name it as a number.'
                             % value)
        if not 0.0 <= number <= 2.0:
            raise ValueError(
                '%s is not a temperature: the endpoints here take 0 to 2.'
                % value)
        session.llm.temperature = number
        print('/llm — temperature = %s (this client run; not persisted).'
              % value, flush=True)
    elif field == 'max_tokens':
        _setNumber(None, value, min=1)
        session.llm.max_tokens = int(value)
        print('/llm — max_tokens = %s (this client run; not persisted).'
              % value, flush=True)
    else:
        raise ValueError(
            '/llm %s — this client does not answer that field. Its fields: '
            '%s.' % (field, ', '.join(LLM_FIELDS)))


def _setNumber(placeholder, value, min=1):
    try:
        number = int(value)
    except ValueError:
        raise ValueError('%r is not a number: name it as an integer.' % value)
    if number < min:
        raise ValueError(
            '%s is outside the range the loop takes: %d and up.'
            % (value, min))
    return number


def _setFileField(session, field, value):
    """One of the three fields the GUI reads too: set it in force and in
    the file, then rebuild the client of this session around it."""
    from imasviz.VizUtils import QVizPreferences
    key = LLM_FILE_FIELDS[field]
    old = getattr(QVizPreferences, key)
    if old == value:
        print('/llm — %s is already in force: %r' % (field, value),
              flush=True)
        return
    QVizPreferences.persist(**{key: value})
    setattr(QVizPreferences, key, value)
    session.llm.apply()
    print('/llm — %s = %s (in force now, and persisted in '
          '~/.imasviz/preferences, the file the GUI reads).'
          % (field, value), flush=True)


def _llmShow(session):
    print('LLM — what is in force for this session:')
    print('  endpoint   : %s' % session.llm.endpoint)
    print('  model      : %s'
          % (session.llm.model
             or '— the first entry of /v1/models, read on first use'))
    print('  key        : %s' % ('(empty: no Authorization header)'
                                 if not session.llm.key else 'set'))
    print('  max_turns  : %d   (this client run)' % session.max_turns)
    print('  temperature: %s (this client run)' % session.llm.temperature)
    print('  max_tokens : %d   (this client run)' % session.llm.max_tokens)


# ---------------------------------------------------------------------- /mcp

def _mcp(cmd, session):
    if not cmd.words:
        _mcpOverview(session)
    elif len(cmd.words) == 1:
        _mcpOne(session, cmd.words[0])
    else:
        raise ValueError(
            '/mcp takes at most one name: /mcp prints the list, and /mcp '
            'open_case one of it.')


def _mcpOverview(session):
    print('Services this session answers today:')
    print('  endpoint : %s' % session.llm.endpoint)
    try:
        names = _modelsList(session.llm.endpoint, session.llm.key,
                            timeout=5.0)
        print('  models   : %s' % ', '.join(names))
    except Exception as e:
        print('  models   : unanswered — %s' % e)
    tools = _tools()
    print('')
    print('  tools    : %d gestures of this session (run it with /mcp <name>).'
          % len(tools))
    for tool in tools:
        name = tool['function']['name']
        words = tool['function']['description'].strip()
        first = words.split('.')[0].rstrip()
        if len(first) > 72:
            first = first[:72] + '…'
        print('    %-16s %s' % (name, first))


def _mcpOne(session, name):
    tools = _tools()
    for tool in tools:
        if tool['function']['name'] == name:
            function = tool['function']
            print('%s' % name)
            print(function['description'].strip())
            parameters = function.get('parameters') or {}
            if parameters.get('properties'):
                print('  parameters:')
                for prop, spec in parameters['properties'].items():
                    kind = spec.get('type')
                    if isinstance(kind, list):
                        kind = ' | '.join(str(one) for one in kind)
                    required = prop in (parameters.get('required') or [])
                    print('    %-16s %s%s'
                          % (prop, kind, '   (required)' if required else ''))
            return
    raise ValueError(
        'no such tool /mcp %s — this session holds: %s.'
        % (name, ', '.join(t['function']['name'] for t in tools)))


def _modelsList(endpoint, key=None, timeout=5.0):
    """The endpoint's models, listed by name -- the `/v1/models` read the
    `LLMClient` uses for its `auto` model, asked for every entry instead
    of the first one. The refusal is named, as the `LLMClient` names it."""
    url = endpoint.rstrip('/') + '/models'
    request = urllib.request.Request(url, method='GET')
    if key:
        request.add_header('Authorization', 'Bearer ' + key)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            'the endpoint answered HTTP %d on /v1/models; the server '
            'may hold no model yet.' % e.code)
    except urllib.error.URLError as e:
        raise ConnectionError(
            'the endpoint %s does not answer within %.0f s (%s) — start '
            'it, or point the client at it with /llm endpoint.'
            % (endpoint, timeout, e.reason))
    except (TimeoutError, OSError) as e:
        raise ConnectionError(
            'the endpoint %s did not answer (%s) — start it, or point '
            'the client at it with /llm endpoint.' % (endpoint, e))
    names = [entry.get('id', '') for entry in data.get('data', [])
             if entry.get('id')]
    if not names:
        raise ValueError(
            'the endpoint %s holds no model at /v1/models — start the '
            'server with one (llama-server --model …).' % endpoint)
    return names


# ---------------------------------------------------------------------- /ids

def _ids(cmd, session):
    """The IDS the open case actually holds, printed raw -- no LLM in
    between. With a URI it is that case; with none, the one open case.
    The answer is what `list_case_idss` reads off the case's entry, so the
    names and the occurrence counts are the case's own, not a recalled list.
    """
    if len(cmd.words) > 1:
        raise ValueError('/ids takes one URI, not %d: /ids imas:hdf5?path=…'
                         % len(cmd.words))
    uri = cmd.words[0] if cmd.words else _singleOpenCase(session)
    held = session.core.list_case_idss(uri)
    if not held:
        print('the case holds no IDS with data: %s' % uri, flush=True)
        return
    print('IDS %d held by %s' % (len(held), uri), flush=True)
    for entry in held:
        occurrences = ', '.join(str(o) for o in entry['occurrences'])
        print('  %-28s %s' % (entry['name'], occurrences), flush=True)


def _singleOpenCase(session):
    """The one open case's URI, refused by name if there is not exactly one."""
    cases = session.core.list_cases()
    if not cases:
        raise ValueError(
            '/ids needs a case URI, and none is open: name one (a URI) or '
            'open a case first.')
    if len(cases) > 1:
        raise ValueError(
            '/ids needs one URI; this session holds %d cases: %s.'
            % (len(cases), ', '.join(case['uri'] for case in cases)))
    return cases[0]['uri']


# --------------------------------------------------------------------- /shots

def _shots(cmd, session):
    import os
    if not cmd.words:
        print('images of each turn are saved under: %s' % session.shots_dir)
        return
    if len(cmd.words) > 1:
        raise ValueError('one directory: /shots dir/to/save/them')
    directory = os.path.abspath(os.path.expanduser(cmd.words[0]))
    session.shots_dir = directory
    print('/shots — the turns now save their images under %s' % directory,
          flush=True)


# ------------------------------------------------------------------- /session

def _session(cmd, session):
    words = cmd.words
    if not words:
        cases = session.core.list_cases()
        if not cases:
            print('No case is open yet: a prompt that names a URI opens '
                  'one, and /mcp lists what it can ask of it.')
            return
        for case in cases:
            loaded = ', '.join(
                '%s %s' % (name, occurrences)
                for name, occurrences in sorted((case.get('loaded') or {}).items()))
            print('  %s  (data dictionary %s; loaded: %s)'
                  % (case['uri'], case.get('dd_version'),
                     loaded or 'nothing yet'))
        return
    if words[0] not in ('save', 'restore'):
        raise ValueError(
            '/session %s — this client answers /session save NAME and '
            '/session restore NAME (and /session alone lists the open '
            'cases).' % words[0])
    if len(words) != 2:
        raise ValueError(
            '/session %s needs a name: /session %s myname' % (words[0],
                                                              words[0]))
    if words[0] == 'save':
        answer = session.core.save_session(name=words[1])
        print('Session saved to %s' % answer['saved_to'], flush=True)
    else:
        answer = session.core.restore_session(name=words[1])
        opened = [c['uri'] for c in answer.get('cases', []) if c.get('opened')]
        print('Restored %d case(s): %s' % (len(opened),
                                           ', '.join(opened) or 'none'),
              flush=True)


# ------------------------------------------------------------------- /history

def _history(cmd, session):
    """The prompts in the shared history, newest first.

    The one list the panel, the web and the client's arrows all read: what
    a turn of any of the three asked for, and `new session` cannot reach it
    -- so the answer here is the list the user recalls, not just what this
    run typed. An empty list is an answer, as the panel's box is empty when
    no prompt has run yet."""
    try:
        prompts = QVizPromptHistory.mostRecentFirst()
    except ValueError as e:
        raise ValueError(
            'the shared prompt history could not be read: %s' % e)
    if not prompts:
        print('No prompt in the shared history yet: type one, or /help for '
              'the commands.')
        return
    print('Prompts in the shared history, newest first -- the one the panel '
          'and the web recall too: %d' % len(prompts))
    for number, prompt in enumerate(prompts, start=1):
        print('  %d. %s' % (number, prompt))


def _toolsMode(cmd, session):
    """The transcript mode a turn wears: `hide`, `off`, `verbose`.

    Set it and it is pinned on this client's loop (the very next turn wears
    it) and persisted to the preferences the panel and the web read too --
    one mode, the same three sides. It is the mode of the **live view**
    (the console here, the panel, the page); the on-disk `transcript.txt`
    is never it -- that stays the full render of the turn, so a reader can
    still audit what a `hide`-wearing run did. A value outside the three
    is refused by name, the way `/llm` refuses a bad field.
    """
    from imasviz.VizUtils import QVizPreferences

    modes = QVizPreferences.AGENT_TOOLS_MODES
    if not cmd.words:
        agent = getattr(session, 'agent', None)
        current = (getattr(agent, 'tools_mode', None) if agent is not None
                   else None)
        if current is None:
            current = QVizPreferences.AgentToolsMode
        print('Transcript mode: %s (the live view; the file on disk is '
              'still the full render) -- /tools %s to change it.'
              % (current, ' / '.join(modes)))
        return
    if len(cmd.words) != 1:
        raise ValueError(
            '/tools takes one word, its mode: %s -- /tools by itself '
            'prints the one in force.' % ' / '.join(modes))
    value = cmd.words[0]
    try:
        mode = QVizPreferences.toolsMode(value)
    except ValueError as e:
        raise ValueError(str(e))
    # Pin it on the loop in force so the very next turn wears it, and in the
    # file so the panel and the web read the same one back.
    session.agent.tools_mode = mode
    QVizPreferences.persist(AgentToolsMode=mode)
    print('/tools — %s (this client now, and the panel and the web read it '
          'back too; the file on disk is still the full render).' % mode,
          flush=True)


# ---------------------------------------------------------------------- /note

# The flags the note commands accept and the field each one maps to in
# the core. One table, both the parse and the refusal read off it, so
# a flag that is not one of them is refused by naming the ones this
# client holds instead of reaching for a value it does not keep.
_NOTE_FLAGS = (
    'machine', 'campaign', 'shot', 'date',
    'date_from', 'date_to', 'author', 'scope', 'title', 'limit',
)


def _parseFlagged(words):
    """`--shot 54924 --scope personal` -> ({shot: '54924', scope:
    'personal'}, []) -- the flags in order, the bare words left. A
    flag this client does not hold, or a `--flag` with no value, is
    refused by naming the ones it does.
    """
    flags, bare = {}, []
    while words:
        word = words.pop(0)
        if word.startswith('--'):
            if not words:
                raise ValueError(
                    '%s needs its value: --shot 54924, --scope '
                    'personal.' % word)
            key = word[2:]
            if key not in _NOTE_FLAGS:
                raise ValueError(
                    'unknown flag %s -- this client answers %s.'
                    % (word, ' '.join('--' + f for f in _NOTE_FLAGS)))
            flags[key] = words.pop(0)
        else:
            bare.append(word)
    return flags, bare


def _note(cmd, session):
    """The two journals on this node, driven off the core: the same
    six names the panel and the web reach, and the same refusals the
    core answers, read raw into the console -- no LLM in between, as
    `/ids` reads them.
    """
    words = cmd.words
    if not words:
        return _noteStats(session)
    sub = words[0]
    rest = words[1:]
    if sub == 'stats':
        return _noteStats(session)
    if sub == 'search':
        return _noteSearch(session, rest)
    if sub == 'list':
        return _noteList(session, rest)
    if sub in ('read', 'get'):
        return _noteRead(session, rest)
    if sub == 'add':
        return _noteAdd(session, rest)
    if sub in ('delete', 'remove'):
        return _noteDelete(session, rest)
    raise ValueError(
        '/note %s -- this client answers /note search, /note list, '
        '/note read, /note add, /note delete, /note stats, and /note '
        'alone (the stats overview).' % sub)


def _noteStats(session):
    answer = session.core.journal_stats()
    for scope in ('personal', 'shared'):
        entry = answer[scope]
        folder = entry.get('folder')
        count = entry.get('notes', 0)
        line = '  %-9s %d note(s)' % (scope, count)
        if folder:
            line += '  under %s' % folder
        refusal = entry.get('refusal')
        if refusal:
            line += '  — %s' % refusal
        print(line)
    emb = answer.get('embeddings') or {}
    if emb.get('endpoint_named'):
        print('  ranking   : embeddings on %s (model %s)'
              % (emb.get('endpoint') or '…', emb.get('model') or '…'))
    else:
        print('  ranking   : keywords — no embeddings endpoint is set yet; '
              'set one (AgentEmbedEndpoint + AgentEmbedModel in the '
              'preferences) and the search ranks by meaning.')
    return True


def _noteSearch(session, words):
    flags, bare = _parseFlagged(words)
    query = ' '.join(bare).strip()
    if not query:
        raise ValueError(
            '/note search needs a query: /note search "plasma unstable" '
            'is the words it ranks for.')
    answer = session.core.search_journals(query=query, **flags)
    if not answer['notes']:
        print('no note in %s fits: %s %s'
              % (answer['scope'], query, _flagWords(flags)))
        return True
    print('%d note(s) under %s, ranked for %s by %s'
          % (len(answer['notes']), answer['scope'], query,
             answer['method']))
    for note in answer['notes']:
        print('  %s' % _noteLine(note))
    return True


def _noteList(session, words):
    flags, bare = _parseFlagged(words)
    if bare:
        raise ValueError(
            '/note list takes flags, not bare words: %s.' % ' '.join(bare))
    answer = session.core.list_notes(**flags)
    if not answer['notes']:
        print('no note in %s fits %s'
              % (answer['scope'], _flagWords(flags) or 'the filters'))
        return True
    print('%d note(s) under %s' % (len(answer['notes']), answer['scope']))
    for note in answer['notes']:
        print('  %s' % _noteLine(note))
    return True


def _noteRead(session, words):
    flags, bare = _parseFlagged(words)
    bare = [word for word in bare if word]
    if not bare:
        raise ValueError(
            '/note read needs an ID: a /note search or /note list names '
            'the one.')
    if len(bare) > 1:
        raise ValueError('/note read takes one ID, got %d: %s.'
                         % (len(bare), ' '.join(bare)))
    note_id = bare[0]
    scope = flags.pop('scope', None) or 'personal'
    note = session.core.read_note(scope, note_id)
    print('  id      : %s' % note['id'])
    print('  scope   : %s' % note['scope'])
    print('  author  : %s' % (note.get('author') or '(none)'))
    for field in ('machine', 'campaign', 'shot', 'date', 'title'):
        if note.get(field):
            print('  %s  : %s' % (field, note[field]))
    print('-')
    print(note.get('text') or '(empty body)')
    return True


def _noteAdd(session, words):
    flags, bare = _parseFlagged(words)
    if len(bare) < 2:
        raise ValueError(
            '/note add SCOPE TEXT: name the journal to put a line in '
            '(personal or shared) and the body of the note.')
    scope, text = bare[0], ' '.join(bare[1:])
    if scope not in ('personal', 'shared'):
        raise ValueError(
            '/note add %s -- name the journal as personal or shared.'
            % scope)
    answer = session.core.add_note(scope, text, **flags)
    print('  %s -> %s (under %s)'
          % (answer['id'], answer['path'],
             _flagWords(flags) or 'no fields named'))
    return True


def _noteDelete(session, words):
    flags, bare = _parseFlagged(words)
    if not bare:
        raise ValueError(
            '/note delete needs an ID: a /note search or /note list '
            'names the one.')
    if len(bare) > 1:
        raise ValueError('/note delete takes one ID, got %d: %s.'
                         % (len(bare), ' '.join(bare)))
    note_id = bare[0]
    scope = flags.pop('scope', None) or 'personal'
    answer = session.core.delete_note(scope, note_id)
    print('  %s of %s is gone'
          % (answer['id'], scope))
    return True


def _noteLine(note):
    """One line for a note in a list: its ID, the fields that name it,
    and a line of its body -- the shape a search answer wears."""
    names = [str(note.get(field)) for field in
             ('machine', 'campaign', 'shot', 'date', 'title')
             if note.get(field)]
    prefix = ' '.join(names) or note['scope']
    snippet = (note.get('snippet') or note.get('text') or '').strip()
    if len(snippet) > 64:
        snippet = snippet[:64] + '…'
    return '%-40s  %-28s  %s' % (note['id'], prefix, snippet)


def _flagWords(flags):
    """The flags a caller named, in the --word value shape the help
    carries -- empty for no flags."""
    if not flags:
        return ''
    pairs = []
    for field in ('scope', 'machine', 'campaign', 'shot', 'date_from',
                  'date_to', 'author', 'title', 'limit'):
        if field in flags:
            word = {'date_from': 'date_from',
                    'date_to': 'date_to'}.get(field, field.lstrip('-'))
            pairs.append('--%s %s' % (field, flags[field]))
    return ' '.join(pairs)
