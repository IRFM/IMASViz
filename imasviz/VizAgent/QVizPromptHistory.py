# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The agent's prompt history: what the user has asked, kept where a
``new session`` cannot reach.

A ``new session`` (``Viz_API.closeAll``) takes the agent panel itself off
the screen and out of the bookkeeping -- the panel the *Windows* menu
names, the one a run types into. A prompt typed into it is thus gone with
the run, the way the case's selection and the windows go. This class is
where they are kept -- :file:`$HOME/.imasviz/agent_prompts` -- the same
folder the manual tells the user the configurations and the sessions live
in, and a panel rebuilt after the run reads them back in, which is the one
way the history crosses a ``new session`` without being asked.

The file holds one list: the prompts in the order they were typed, newest
last. A file that is not one is refused by what it is, the same way a
configuration whose root is neither shape is. The list the run does not
hold is dropped at a cap, so the folder does not grow with the run.
"""

import json
import os

FILENAME = 'agent_prompts'
# A run does not hold a list it never asked for; the run the file holds is
# bounded so a file named does not grow without limit.
MAX_HISTORY = 100


class QVizPromptHistory:
    """The prompts a run has typed, kept in the folder a run cannot reach
    with ``closeAll`` -- where a panel rebuilt after the run reads them
    back in, and a new run types the same prompts back out."""

    @staticmethod
    def directory():
        """The folder, created on the way in: a write lands a file there,
        and a file that goes in a folder has to go where the folder is --
        the same pattern the configurations and the sessions own."""
        home = os.environ.get('HOME')
        if not home:
            raise ValueError('HOME is not set: there is no folder to keep '
                             'the agent\'s prompts in.')
        folder = os.path.join(home, '.imasviz')
        if not os.path.isdir(folder):
            os.makedirs(folder)
        return folder

    @staticmethod
    def path():
        return os.path.join(QVizPromptHistory.directory(), FILENAME)

    @staticmethod
    def load():
        """The prompts the file holds, oldest first. An empty list is an
        answer: a run that has not yet typed one does not hold one, and an
        empty box is the history a fresh run reaches. A file that is not a
        list of prompts is refused by what it is, as every other read in
        the repository is a named refusal rather than a silent empty."""
        path = QVizPromptHistory.path()
        if not os.path.exists(path):
            return []
        try:
            with open(path) as f:
                entries = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise ValueError(
                '"%s" is not the agent\'s prompt history: %s.'
                % (path, e))
        if not isinstance(entries, list) or \
                not all(isinstance(entry, str) for entry in entries):
            raise ValueError(
                '"%s" is not the agent\'s prompt history: it is not a '
                'list of prompts.' % path)
        return list(entries)

    @staticmethod
    def append(prompt):
        """One more prompt, newest last. The prompt a run has typed is
        not dropped at the cap -- the run it is not held for is the
        oldest one the file names, not the one the run asks of the file."""
        text = (prompt or '').strip()
        if not text:
            raise ValueError('A prompt the history holds is a word, not an '
                             'empty box.')
        entries = QVizPromptHistory.load()
        if text in entries:
            # A prompt already in the history is not repeated: it is
            # recalled, not re-typed -- the run that asks it gets the
            # answer it asked for, and the one it recalls sits on top of
            # the ones it has had.
            entries.remove(text)
        entries.append(text)
        entries = entries[-MAX_HISTORY:]
        path = QVizPromptHistory.path()
        with open(path, 'w') as f:
            f.write(json.dumps(entries, ensure_ascii=False, indent=2) + '\n')
        return entries

    @staticmethod
    def mostRecentFirst(limit=None):
        """The prompts the box would list them in: newest first, up to a
        limit (the box does not hold a list it never asked for, but it
        does hold the one the run asked for)."""
        entries = QVizPromptHistory.load()[::-1]
        return entries if limit is None else entries[:limit]
