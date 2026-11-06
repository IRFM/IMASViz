# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The client's prompt history: one file, the arrows to walk it.

The standard library's `readline` is **not built** in this node's
Python (measured: the module is the pure-Python fallback -- no `_rl`
behind it, so no arrows, no history file, no completion to ask of it),
so the client keeps its own. One file under `$HOME/.imasviz`, as the
preferences: read when the client opens, appended as lines are added,
and walked by `tui` with the up and down arrows.

The file is plain text, one prompt per line: readable in an editor,
deletable by hand, and the same shape the shells' own histories are.
Two consecutive additions of the same line cost one entry, which is
the rule the shells apply and the one that keeps the arrows from
pointing at the same line twice.
"""

import os


class History:
    """The one file and its entries, oldest first as the file holds them."""
    def __init__(self, path):
        self.path = path
        self.entries = []
        folder = os.path.dirname(path)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    self.entries = [line.rstrip('\n') for line in f
                                    if line.strip()]
            except OSError:
                pass

    def add(self, line):
        line = (line or '').strip()
        if not line:
            return
        if self.entries and self.entries[-1] == line:
            return
        self.entries.append(line)
        with open(self.path, 'a') as f:
            f.write(line + '\n')
