# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The `/` commands of the viz_cli REPL, parsed and answered by name.

What a command answers is named when it cannot: an unknown command, a
missing name on `/session` -- each refusal is a `ValueError` carrying the
name the caller typed, which is the style the rest of the repository
applies (`refused by name, the reason named where the user reads it`).
"""

HELP = """viz_cli — IMASViz driven without its window: the agent, offscreen.

A line runs the agent (the LLM and the tools of this session); the
images it drew and its transcript are left in the turns directory,
named after the turn. Commands:

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


COMMANDS = ('shots', 'session', 'history', 'help', 'quit')


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
    elif cmd.name == 'shots':
        _shots(cmd, session)
    elif cmd.name == 'session':
        _session(cmd, session)
    elif cmd.name == 'history':
        _history(cmd, session)
    return True


# -------------------------------------------------------------------- /shots

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
