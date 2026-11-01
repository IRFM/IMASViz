# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Asking for a plugin of one's own, and writing it.

What the box says after it writes matters as much as the writing: the plugin is
already on the menu of the next right click -- nothing has to be registered, and
nothing has to be restarted. Saying so is the whole point, because the usual
doubt at that moment is "did it take?", and the way to answer it is the first
click the plugin answers back.

A refusal is said on the box, not in a modal popped from a slot: the reason is
about the words still sitting in the name field, and a dialog on top of them
means closing the answer to read the question.
"""

from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QTextEdit,
                               QVBoxLayout)

from imasviz.VizPlugins.QVizPluginSource import userPluginsFolder
from imasviz.VizPlugins.create_plugin import createPlugin

# The IDS names the box offers without being asked: the ones a run is most likely
# to write a plugin for. It is an editable combo box, so the list is a convenience
# and not a gate -- any name the case holds can be typed.
COMMON_IDSS = ['equilibrium', 'core_profiles', 'core_sources', 'magnetics',
               'wall', 'interferometer', 'polarimeter', 'spectrometer']


class QVizPluginCreatorDialog(QDialog):
    """Write a plugin of this user's own into their plugins folder."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('New IMASViz plugin')
        self.resize(520, 460)
        self.created = None
        self._buildUI()

    def _buildUI(self):
        layout = QVBoxLayout(self)

        folder = userPluginsFolder()
        layout.addWidget(QLabel('<b>A plugin of your own</b><br>'
                                'It is written into <code>%s</code> and offered '
                                'by the Plugins menu as soon as it is there -- '
                                'nothing is registered and IMASViz does not '
                                'restart.' % folder))

        layout.addWidget(QLabel('Plugin name (for instance <code>my '
                                'analysis</code>):'))
        self.nameInput = QLineEdit()
        self.nameInput.setPlaceholderText('my analysis')
        layout.addWidget(self.nameInput)

        layout.addWidget(QLabel('IDS it answers (any node of it opens the '
                                'menu):'))
        self.idsInput = QComboBox()
        self.idsInput.setEditable(True)
        self.idsInput.addItems(COMMON_IDSS)
        self.idsInput.setCurrentText('equilibrium')
        layout.addWidget(self.idsInput)

        layout.addWidget(QLabel('What the menu line says:'))
        self.titleInput = QLineEdit()
        self.titleInput.setPlaceholderText('Draw my thing...')
        layout.addWidget(self.titleInput)

        layout.addWidget(QLabel('What it is for (the first line of the file '
                                'IMASViz opens for you):'))
        self.descInput = QTextEdit()
        self.descInput.setPlaceholderText('One sentence: what this plugin is '
                                          'for.')
        self.descInput.setMaximumHeight(80)
        layout.addWidget(self.descInput)

        # What stopped the last attempt, if anything. A label on the box, because
        # the words to fix are the ones still in the fields underneath it.
        self.stateLabel = QLabel('')
        self.stateLabel.setWordWrap(True)
        layout.addWidget(self.stateLabel)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.cancelButton = QPushButton('Cancel')
        self.cancelButton.clicked.connect(self.reject)
        self.createButton = QPushButton('Create plugin')
        self.createButton.clicked.connect(self._create)
        buttons.addWidget(self.cancelButton)
        buttons.addWidget(self.createButton)
        layout.addLayout(buttons)

    def _create(self):
        try:
            self.created = createPlugin(
                self.nameInput.text(),
                targetIds=self.idsInput.currentText(),
                description=self.descInput.toPlainText(),
                menuTitle=self.titleInput.text())
        except ValueError as refusal:
            # The name field is where the fix is, so that is where the cursor
            # goes back.
            self.stateLabel.setText('<b>Not written:</b> %s' % refusal)
            self.nameInput.setFocus()
            self.nameInput.selectAll()
            return

        self.stateLabel.setText(
            '<b>%s</b> is written in <code>%s</code>.<br>'
            'Right-click a node of the <b>%s</b> IDS and pick '
            '&laquo;&nbsp;%s&nbsp;&raquo;: it draws a figure of its own. Then '
            'open it from <i>File &rarr; Plugins&hellip;</i> to change what it '
            'draws.' % (self.created.name, self.created.folder,
                        self.idsInput.currentText().strip(),
                        self.titleInput.text().strip()
                        or '%s...' % self.created.name))
        # The box stays open on purpose. Closing it on the spot would trade the
        # one thing the user needs to know -- where the file is and which gesture
        # answers it -- for a window that is gone, and the same button is then the
        # way into the editor of what was just written.
        self.createButton.setText('Edit it now')
        self.cancelButton.setText('Close')
        self.createButton.setEnabled(True)
        for field in (self.nameInput, self.idsInput, self.titleInput,
                      self.descInput):
            field.setEnabled(False)
