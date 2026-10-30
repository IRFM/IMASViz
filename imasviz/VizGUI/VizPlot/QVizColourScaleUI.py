# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Choosing the colours every picture of a window is drawn with.

One question, asked once: which map. The **level range** is deliberately not
here -- it has handles on the colour bar itself, and a dialogue that set the same
two numbers from two places is two answers to one question. What this window adds
over the library's own right-click menu on the bar is that it can be found (a
line in the menu the user already opens, not a 25-pixel strip) and that a name is
shown as the colours it stands for.

The names come from `mapNames()` -- what this node can draw with, measured at
**71** maps on `PyQtGraph/0.13.7-foss-2023b`. The library's own menu reaches
matplotlib's maps too, and those stay reachable there: this list is the set this
application promises to put back from a session file on a node that may not hold
matplotlib. A name picked from the other menu is still read back here when it
resolves, and refused by name when it does not.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QLineEdit, QListWidget,
                               QListWidgetItem, QVBoxLayout)

from imasviz.VizGUI.VizPlot.QVizColourScales import (DEFAULT_MAP, mapNamed,
                                                     mapNames, swatchPixmap)

ENTRY = 'Colour Scale...'


class QVizColourScaleUI(QDialog):
    """A list of the maps this node holds, each shown as the strip it paints."""

    def __init__(self, parent=None, current=DEFAULT_MAP, onChosen=None):
        """
        Arguments:
            current  (str)   : the map to start on, so the window answers the
                               question "which one is this?" and not only
                               "which one do you want?".
            onChosen (call)  : answered the name the user accepted. Nothing is
                               applied while a name is being looked at -- a
                               picture that changed colour on a click that was
                               only a look is a picture that has to be undone.
        """
        super().__init__(parent)
        self.setWindowTitle(ENTRY.rstrip('.'))
        self._onChosen = onChosen

        layout = QVBoxLayout(self)
        self.filter = QLineEdit(self)
        self.filter.setPlaceholderText('Filter the names')
        self.filter.textChanged.connect(self._filtered)
        layout.addWidget(self.filter)

        self.maps = QListWidget(self)
        self.maps.setUniformItemSizes(True)
        layout.addWidget(self.maps)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel,
                                   parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._names = mapNames()
        self._fill(())
        self._select(current)

    # -------------------------------------------------------------------- list
    def _fill(self, matching):
        """The rows, in `mapNames()` order, filtered by what has been typed."""
        self.maps.clear()
        for name in self._names:
            if matching and name not in matching:
                continue
            item = QListWidgetItem(name, self.maps)
            item.setIcon(self._iconFor(name))
            self.maps.addItem(item)

    def _iconFor(self, name):
        """A strip of the map, or a blank row for a name that cannot be drawn.

        A name in `mapNames()` is a file on disk, so this normally resolves. It
        degrades rather than losing the row: a map the list promises and the
        package cannot paint is a broken install, and it still has to be named
        for what it is called.
        """
        from PySide6.QtGui import QIcon

        try:
            return QIcon(swatchPixmap(mapNamed(name)))
        except ValueError:
            return QIcon()

    def _filtered(self, text):
        wanted = text.strip().lower()
        self._fill(tuple(name for name in self._names
                         if wanted in name.lower()) if wanted else ())

    def _select(self, name):
        rows = self.maps.findItems(name or '', Qt.MatchFlag.MatchExactly)
        if rows:
            self.maps.setCurrentItem(rows[0])

    # ------------------------------------------------------------------ answer
    def chosenName(self):
        """The name on the row the list is on, or None when there is none."""
        item = self.maps.currentItem()
        return None if item is None else item.text()

    def accept(self):
        """Only a name that draws is an answer.

        A filter that matches nothing leaves the list with no current row, and
        closing on that would silently put a map nobody chose on the window.
        """
        name = self.chosenName()
        if name is None:
            return
        super().accept()
        if self._onChosen is not None:
            self._onChosen(name)
