# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The `/` commands of the viz_cli REPL, parsed and answered by name.

What a command answers is named when it cannot: an unknown command, an
unknown `/llm` field, a missing name on `/session` -- each refusal is a
`ValueError` carrying the name the caller typed, which is the style the
rest of the repository applies (`refused by name, the reason named
where the user reads it`).

Three of the fields `/llm` sets are the ones the GUI reads too --
`endpoint`, `model`, `key`: they are written in the **same**
preferences file the application builds from (`QVizPreferences.persist`,
the file `~/.imasviz/preferences`), so the two interfaces stay on the
same endpoint. The loop's own parameters (`max_turns`, `temperature`,
`max_tokens`) steer this client run only, and say so when they are set;
they have no line in that file, and inventing one would cost the GUI a
line it does not read.
"""

LLM_FIELDS = ('endpoint', 'model', 'key', 'max_turns', 'temperature',
              'max_tokens')
LLM_FILE_FIELDS = {
    'endpoint': 'AgentLLMEndpoint',
    'model': 'AgentLLMModel',
    'key': 'AgentLLMApiKey',
}

HELP = """viz_cli — IMASViz driven without its window: the agent, offscreen.

A line runs the agent (the LLM and the tools of this session); the
images it drew and its transcript are left in the turns directory,
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

  /shots [DIR]               where the turns save their images
  /session                   the cases open in this session
  /session save NAME         the session the application writes
  /session restore NAME      put that session back
  /history                   the prompts of this client run
  /help                      this text
  /quit                      leave; the arrows keep your prompts in
                             ~/.imasviz/cli_history between runs

Ctrl+C during a turn stops it at the next turn boundary and still saves
what it drew.
"""


class Command:
    """One line the REPL has parsed: its name, and the words that follow."""
    def __init__(self, name, words):
        self.name = name
        self.words = words


COMMANDS = ('llm', 'shots', 'session', 'history', 'help', 'quit')


def parse(line):
    """`/shots dir` -> a `Command`; everything it cannot answer is
    refused by name, so a `/` line is never mistaken for a prompt and
    a prompt never mistaken for a `/banana`."""
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
    """The `/help` answer."""
    return HELP


def execute(cmd, session):
    """Run one command on one session. Returns `False` when the REPL
    leaves; every refusal is a `ValueError` the caller names out loud."""
    if cmd.name == 'help':
        print(help_text())
    elif cmd.name == 'quit':
        return False
    elif cmd.name == 'llm':
        _llm(cmd, session)
    elif cmd.name == 'shots':
        _shots(cmd, session)
    elif cmd.name == 'session':
        _session(cmd, session)
    elif cmd.name == 'history':
        _history(cmd, session)
    return True


# ---------------------------------------------------------------------- /llm

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


# ------------------------------------------------------------------ /session

def _session(cmd, session):
    words = cmd.words
    if not words:
        cases = session.core.list_cases()
        if not cases:
            print('No case is open yet: a prompt that names a URI opens '
                  'one.')
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


# ------------------------------------------------------------------ /history

def _history(cmd, session):
    if not session.prompts:
        print('No prompt in this client run yet: type one, or /help for '
              'the commands.')
        return
    print('Prompts of this client run:')
    for number, prompt in enumerate(session.prompts, start=1):
        print('  %d. %s' % (number, prompt))
