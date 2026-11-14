# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The client's prompt history: the one shared store, walked by the arrows.

The standard library's `readline` is **not built** in this node's Python
(measured: the module is the pure-Python fallback -- no `_rl` behind it, so no
arrows, no completion to ask of it), so the client keeps its own line editor
(`viz_cli.tui`) and walks the history it holds.

The history it holds is the one the whole application shares:
`QVizPromptHistory`, the list under `$HOME/.imasviz/agent_prompts` the in-app
panel writes and recalls. A prompt the client runs lands in that same list, and
a prompt the user typed in the panel -- or the web -- is the one the client's
arrows recall: one history, every prompt a turn of any surface asked for, and
`new session` cannot reach it.

The arrows read newest first (`tui` walks `entries` from its last to its
first), so this class holds the store oldest-first, as the shared store holds
it, and the walk maps on it without turning it around.

A plain-text history file a run kept under a different name (`--history`) is
folded into the shared list once at the open, so a history a client run left in
that file is not lost to the move.
"""

import os

from imasviz.VizAgent.QVizPromptHistory import QVizPromptHistory


class History:
    """The one prompt history the client's arrows walk.

    Thin over the application's shared store: `entries` holds what it keeps,
    oldest first (the arrows walk it from last to first), and `add` puts a
    prompt in it. `path` is where it lives, for the leave line the client
    prints.
    """

    def __init__(self, path=None):
        self.path = _sharedPath()
        if path:
            # A plain-text history file a run pointed the arrows at: fold its
            # prompts into the shared list once, so the move does not cost the
            # prompts that file held. Best-effort -- a file that is gone costs
            # only what it held; the client still opens on the shared list.
            _foldIntoStore(path)

    @property
    def entries(self):
        """The prompts the shared list holds, oldest first. A store that
        refuses to read answers an empty list: the arrows have nothing to walk
        yet, and the run still opens."""
        try:
            return QVizPromptHistory.load()
        except ValueError:
            return []

    def add(self, line):
        """One more prompt, in the shared list. The share of a line already
        held is what the store settles -- recalled to the newest, kept once."""
        line = (line or '').strip()
        if not line:
            return
        QVizPromptHistory.append(line)


def _sharedPath():
    """Where the shared list lives, for the leave line:
    `$HOME/.imasviz/agent_prompts`. Asked without the store's side effects --
    a path the client prints, not a read of the store itself."""
    home = os.environ.get('HOME') or os.getcwd()
    return os.path.join(home, '.imasviz', 'agent_prompts')


def _foldIntoStore(path):
    """The plain-text lines a legacy history file held, into the shared list.

    One line at a time, through the store, so the store's own rules -- the
    dedup, the newest first, the cap -- settle the fold. A file that is gone
    costs only what it held; the client opens on the shared list either way."""
    try:
        with open(path) as f:
            lines = [line.strip() for line in f if line.strip()]
    except OSError:
        return
    for line in lines:
        try:
            QVizPromptHistory.append(line)
        except ValueError:
            continue
