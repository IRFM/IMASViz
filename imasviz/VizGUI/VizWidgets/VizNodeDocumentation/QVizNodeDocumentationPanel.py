# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The dock that answers "what is this node?" when the tree is clicked.

It draws and nothing else: `QVizNodeFacts` decides what is worth saying, this
turns those rows into labels. The row set is rebuilt from scratch on every node,
which is why nothing of the previous node can survive -- the widget this replaces
hid its fields first and then died in the middle of reading, leaving the old
node's name and numbers in the hidden labels; measured, after a failed read it
still held `Node 'equilibrium.psi'`, `Array size '101'` and `Content '[-7.9 ...'`
while every field on screen was blank.

The entry point is `showNode`, deliberately not `update`: the old class defined
`update(self, item, dataTreeView)` on a QWidget, so the inherited no-argument
`update()` -- which Qt itself calls to schedule a repaint -- was gone. Measured,
`panel.update()` answered `TypeError: QVizNodeDocumentationWidget.update()
missing 2 required positional arguments: 'item' and 'dataTreeView'`.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from imasviz.VizUtils import GlobalColors, GlobalFonts
from .QVizNodeFacts import QVizNodeFacts

# What the panel says before the user has clicked anything.
NOTHING_SELECTED = 'no node selected yet'


class QVizNodeDocumentationPanel(QWidget):
    """Name, documentation and contents of the node the user selected."""

    def __init__(self, parent=None):
        super(QVizNodeDocumentationPanel, self).__init__(parent=parent)
        self.setObjectName("QVizNodeDocumentationPanel")
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setBrush(self.backgroundRole(), GlobalColors.LIGHT_CYAN)
        self.setPalette(palette)

        self._rows = []
        self._scroll = QScrollArea(self)
        self._scroll.setObjectName("QVizNodeDocumentationScroll")
        self._scroll.setWidgetResizable(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self._scroll)
        self._showRows([('Node: ', NOTHING_SELECTED)])

    def showNode(self, node):
        """Say what this node is and what the opened case holds in it."""
        self._showRows(QVizNodeFacts(node).rows())

    def displayedRows(self):
        """The rows on screen, as `'Label: value'` lines.

        The panel exists to be read, so a test -- or a user -- should be able to
        ask what it currently says without walking Qt widgets. The label carries
        its own colon and space, which is why the two halves are butted together.
        """
        return ['%s%s' % (title.text(), value.text())
                for title, value in self._rows]

    def _showRows(self, rows):
        """Replace every label on screen. Nothing of the previous node is kept."""
        content = QWidget()
        content.setObjectName("QVizNodeDocumentationContents")
        form = QFormLayout(content)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        drawn = []
        for label, text in rows:
            title = _makeLabel(label, GlobalFonts.TITLE_MEDIUM)
            value = _makeLabel(text, GlobalFonts.TEXT_MEDIUM)
            form.addRow(title, value)
            drawn.append((title, value))
        self._rows = drawn

        previous = self._scroll.takeWidget()
        self._scroll.setWidget(content)
        if previous is not None:
            previous.deleteLater()


def _makeLabel(text, font):
    """A label the user can read and select to copy."""
    label = QLabel()
    label.setText(text)
    label.setFont(font)
    label.setAlignment(Qt.AlignLeft)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return label
