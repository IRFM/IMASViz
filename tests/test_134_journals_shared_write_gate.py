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

"""The write to the shared journal is asked for, not taken.

A write to the **shared** journal is a line the writers all read —
visible in the application, on the page, in the other writers'
sessions — and the loop runs it only when the user's own request names
the journal it will put a line in. A model-initiated write to the
shared journal on a request that names no shared journal is refused by
name: the gesture, the journal that would hold the line, and the one
word that unblocks it (the ask in the user's own words). The write the
model reaches for to the **personal** journal is the one it is owed on
a "note down what I said" — the gate stands aside there. The gesture
the **user** reaches for is never refused: the click is the ask.
The rule the loop's destructive gesture already wears — a close the
model runs on a request that does not name one — is the same shape:
the shared write runs only when the user asks, in their own words.

Two vocabularies, and this file sits on the seam. The notebooks answer
one tool, ``manage_note``, whose ``action`` says which write is meant;
the gate reads the GESTURE behind that action (``SHARED_JOURNAL_GESTURES``
names members), while the refusal and every ask here are spelled the way
the tool set offers them — a refusal naming ``add_note`` would send the
model to a name it is refused for asking, and a scripted call naming it
is refused as a tool no longer offered on its own.
"""

import pytest

from imasviz.VizAgent import agent as agent_module
from imasviz.VizAgent.agent import AgentLoop


class RecordingSharedCore:
    """The core one write reaches: the three shared-journal gestures,
    recorded, and nothing else. A refused write must not leave a call
    behind, so the test reads the record and sees the gate did what
    it named."""
    def __init__(self):
        self.calls = []

    def add_note(self, scope, text, author=None, machine=None, campaign=None,
                 shot=None, date=None, title=None):
        self.calls.append(('add_note', {'scope': scope, 'text': text}))
        return {'id': 'a-note-id', 'scope': scope, 'path': '/note.md',
                'overwritten': True}

    def edit_note(self, scope, note_id, text=None, author=None, machine=None,
                  campaign=None, shot=None, date=None, title=None):
        self.calls.append(('edit_note', {'scope': scope,
                                         'note_id': note_id, 'text': text}))
        return {'id': note_id, 'scope': scope, 'path': '/note.md',
                'edited': True}

    def delete_note(self, scope, note_id):
        self.calls.append(('delete_note', {'scope': scope,
                                           'note_id': note_id}))
        return {'id': note_id, 'deleted': True}


class FakeDispatcher:
    def call(self, function, timeout=300.0):
        return function()


@pytest.fixture
def loop():
    core = RecordingSharedCore()
    agent = AgentLoop(core=core, llm=object(), dispatcher=FakeDispatcher(),
                      main_window=None, api=None)
    return agent, core


def test_a_model_write_to_the_shared_journal_not_asked_is_refused(loop):
    """A ``model`` reaching for ``manage_note(action="add",
    scope='shared')`` on a request that names no shared journal is refused
    by name: the gate fires, the core is not called, and the refusal names
    the shared journal and the one word that unblocks it."""
    agent, core = loop
    with pytest.raises(ValueError) as exc:
        agent._dispatch('manage_note', {'action': 'add', 'scope': 'shared',
                                        'text': 'the plasma was unstable'},
                        requested_by='model',
                        user_prompt='note down that the plasma was unstable')
    refusal = str(exc.value)
    assert core.calls == [], \
        'a refused shared write must not reach the core: %r' % core.calls
    assert 'shared' in refusal, \
        'the refusal names the journal the write would land in: %r' % refusal
    assert 'manage_note(action="add")' in refusal, \
        'the refusal names the call it refused, in the spelling the tool ' \
        'set offers it, not the gesture behind it: %r' % refusal
    # The unblock is an ask in the user's own words, in either language.
    assert ('publier' in refusal or 'share' in refusal
            or 'partagé' in refusal), \
        'the refusal names the one word that unblocks it: %r' % refusal


def test_a_model_write_to_the_shared_journal_asked_runs(loop):
    """The same ``model`` call, on a request that names the shared
    journal in the user's own words, is the one the gate lets through:
    the unblock is a word, and the word is there. What the core is asked
    for is the gesture behind that action, under its own name."""
    agent, core = loop
    agent._dispatch('manage_note', {'action': 'add', 'scope': 'shared',
                                    'text': 'the plasma was unstable'},
                    requested_by='model',
                    user_prompt='publier cette note au journal partagé')
    assert core.calls, \
        'a shared write the user asked for in their own words runs: %r' \
        % core.calls
    assert core.calls[0][0] == 'add_note'
    assert core.calls[0][1]['scope'] == 'shared'


def test_a_user_write_to_the_shared_journal_never_refused(loop):
    """The gesture the ``user`` reaches for — the page's button,
    ``requested_by='user'`` — owes no word: the click is the ask. A
    shared write the model refuses is one the user's own hand runs, on
    the same words."""
    agent, core = loop
    # The one the loop's gate refuses as a model gesture, run as the
    # user's: the same core, the same arguments, and the refusal does
    # not stand in the way.
    agent._dispatch('manage_note', {'action': 'add', 'scope': 'shared',
                                    'text': 'the plasma was unstable'},
                    requested_by='user',
                    user_prompt='note down that the plasma was unstable')
    assert core.calls, \
        'a user write to the shared journal runs, the click is the ask: %r' \
        % core.calls
    assert core.calls[0][1]['scope'] == 'shared'


def test_a_model_write_to_the_personal_journal_not_refused(loop):
    """The gate is for the **shared** journal only: a ``model`` write to
    the **personal** journal on a request that names no shared journal
    is the one it is owed on a "note down what I said", and the gate
    stands aside there."""
    agent, core = loop
    agent._dispatch('manage_note', {'action': 'add', 'scope': 'personal',
                                    'text': 'the plasma was unstable'},
                    requested_by='model',
                    user_prompt='note down that the plasma was unstable')
    assert core.calls, \
        'a personal write the model reaches for is not a refusal: %r' \
        % core.calls
    assert core.calls[0][1]['scope'] == 'personal'


def test_the_delete_gate_reads_the_same_way(loop):
    """The gesture the gate names — the notebook's delete — reads the
    same as the add: a model ``manage_note(action="delete")`` on a
    request that names no shared journal is refused, and the one the
    user names in their own words runs."""
    agent, core = loop
    with pytest.raises(ValueError):
        agent._dispatch('manage_note', {'action': 'delete', 'scope': 'shared',
                                        'note_id': 'a-note-id'},
                        requested_by='model',
                        user_prompt='take that note out')
    assert core.calls == [], \
        'a refused shared delete must not reach the core: %r' % core.calls

    agent._dispatch('manage_note', {'action': 'delete', 'scope': 'shared',
                                    'note_id': 'a-note-id'},
                    requested_by='user')
    assert core.calls, 'a user delete to the shared journal runs: %r' \
        % core.calls


def test_the_edit_gate_reads_the_same_way(loop):
    """The third gesture the gate names — the notebook's edit — reads the
    same as the other two: a model ``manage_note(action="edit")`` on a
    request that names no shared journal is refused by name (the edit
    is a write to a place the writers all read, whatever it changes),
    and the one the user names in their own words runs."""
    agent, core = loop
    with pytest.raises(ValueError) as exc:
        agent._dispatch('manage_note', {'action': 'edit', 'scope': 'shared',
                                        'note_id': 'a-note-id',
                                        'text': 'it was unstable, not steady'},
                        requested_by='model',
                        user_prompt='fix that last line about the plasma')
    refusal = str(exc.value)
    assert core.calls == [], \
        'a refused shared edit must not reach the core: %r' % core.calls
    assert 'shared' in refusal, \
        'the refusal names the journal the edit would land in: %r' % refusal
    assert 'manage_note(action="edit")' in refusal, \
        'the refusal names the call it refused, in the spelling the tool ' \
        'set offers it: %r' % refusal

    agent._dispatch('manage_note', {'action': 'edit', 'scope': 'shared',
                                    'note_id': 'a-note-id',
                                    'text': 'it was unstable, not steady'},
                    requested_by='user')
    assert core.calls, 'a user edit to the shared journal runs: %r' \
        % core.calls
    assert core.calls[0][0] == 'edit_note'
    assert core.calls[0][1]['scope'] == 'shared'


def test_the_publish_words_are_the_unblock_in_either_language():
    """The one word that unblocks a refused shared write, in either
    language, is a member of the loop's own table — and a word the
    model recites (one the user did not give) is not. The two are
    asked of in ``_userAskedForAPublish``, the same shape as
    ``_userAskedForAClosure`` for the destructive gesture."""
    fn = agent_module._userAskedForAPublish
    # The user's own ask, in either language, unblocks the write.
    assert fn('publier cette note au journal partagé')
    assert fn('Share this to the shared journal')
    assert fn('écris cela au cahier de manip')
    # A request that names the plasma but not the journal does not.
    assert not fn('note down that the plasma was unstable')
    assert not fn('take that note out')
