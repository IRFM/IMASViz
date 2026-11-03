# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import logging
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout,
                               QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QVBoxLayout, QWidget)

from imasviz.VizDataSource.QVizIMASDataSource import caseUri, hdf5PathUri
from imasviz.VizGUI.VizWidgets.QVizIMASdbBrowserWidget import (
    caseRootForUser, localCases)


class QVizCaseSelector(QWidget):
    """The URI-first selection of the start window.

    A flat list of the local cases, each row a readable label (backend,
    database, shot and run) whose data and tooltip are the URI the Access Layer
    opens the case with; the selection -- by double click or *Ouvrir* -- is
    handed to the caller through `uriOpened` **as a URI**. A free line takes
    any other URI (a UDA case, a remote case, or one the local walk does not
    reach), and *Dossier…* turns a chosen folder of ``*.h5`` into the ``path=``
    URI. The whole thing emits URIs and never the five derived parameters --
    that is the point of a URI-first selection: what the user chose is the
    string the case is opened with.
    """

    uriOpened = Signal(str)

    def __init__(self, parent=None):
        super(QVizCaseSelector, self).__init__(parent)

        layout = QVBoxLayout(self)

        self.listView = QListWidget(self)
        self.listView.setToolTip(
            'Les cas locaux trouvés. Un double-clic ouvre le cas choisi.')
        layout.addWidget(self.listView)

        self.freeText = QLineEdit(self)
        self.freeText.setPlaceholderText(
            'imas:hdf5?path=…   ou   imas:uda?user=…;database=…;shot=…;run=…')
        layout.addWidget(self.freeText)

        buttons = QHBoxLayout()
        self.openButton = QPushButton('Ouvrir', self)
        self.copyButton = QPushButton('Copier l\'URI', self)
        self.folderButton = QPushButton('Dossier…', self)
        for button in (self.openButton, self.copyButton, self.folderButton):
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.listView.itemDoubleClicked.connect(self.openRow)
        self.freeText.returnPressed.connect(self.openFree)
        self.openButton.clicked.connect(self.openCurrent)
        self.copyButton.clicked.connect(self.copyUri)
        self.folderButton.clicked.connect(self.pickFolder)

    # What the list holds, and what a row of it answers.

    def casesFor(self, username):
        """The local cases of `username`, flat and ordered; [] when none exists.

        A case that is a case on disk is a case here -- nothing is dropped -- and
        the order is the one `localCases` spells, which is the order the list is
        drawn in, so the row a user sees is the case the scanner found and not a
        copy of it.
        """
        root = caseRootForUser(username)
        if root is None:
            return []
        return localCases(root)

    def refresh(self, username):
        """Fill the list from `casesFor`. Returns the cases it laid in.

        Each row carries its URI both as data and as its tooltip, so a
        selection answers the URI without a second walk of the case, and a hover
        shows the user the very string that will be opened.
        """
        self.listView.clear()
        cases = self.casesFor(username)
        for case in cases:
            uri = self.uriOf(username, case)
            item = QListWidgetItem(self.labelOf(case), self.listView)
            item.setData(Qt.UserRole, uri)
            item.setToolTip(uri)
        return cases

    @staticmethod
    def labelOf(case):
        return '%s · %s · %s · %s' % (case['backend'], case['database'],
                                      case['shot'], case['run'])

    @staticmethod
    def uriOf(username, case):
        """The URI `case` is opened with: the path for HDF5, the parameter set
        for MDS+ -- the two spellings the Access Layer takes off this stack."""
        if case['backend'] == 'HDF5':
            return hdf5PathUri(case['path'])
        return caseUri(12, username, case['database'], case['shot'], case['run'],
                       '3', '')

    # The gestures.

    def selectedUri(self):
        """The URI of the selected row, or None when the list has no selection."""
        item = self.listView.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def openRow(self, item):
        """The row a double click landed on -- the gesture that opens a case."""
        uri = item.data(Qt.UserRole)
        if uri:
            self.uriOpened.emit(uri)

    def openFree(self):
        """The free line's text -- the gesture for a URI the local walk lacks.

        Refused, not sent empty: an empty line is an answer the user did not
        give, and opening one would spend a gesture on a case that was never
        named.
        """
        text = self.freeText.text().strip()
        if not text:
            logging.getLogger('logPanel').error(
                'Aucune URI à ouvrir : saisir une URI dans le champ libre.')
            return
        self.uriOpened.emit(text)

    def openCurrent(self):
        """*Ouvrir*: the selected row if there is one, else the free line.

        One button for the two presentations the start window shows it in --
        the list and the free line -- so the user never has to know which is
        which: whatever is in front of them and in focus is what opens.
        """
        uri = self.selectedUri()
        if uri:
            self.uriOpened.emit(uri)
            return
        self.openFree()

    def copyUri(self):
        """*Copier l'URI*: the selected row's URI, else the free line's text.

        The one affordance that makes a case portable -- copy it, paste it
        anywhere the Access Layer takes a URI. Nothing is copied when there is
        nothing to copy.
        """
        uri = self.selectedUri()
        if uri is None:
            uri = self.freeText.text().strip()
        if not uri:
            logging.getLogger('logPanel').error(
                'Aucune URI à copier : choisir un cas, ou saisir une URI.')
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(uri)

    def pickFolder(self):
        """*Dossier…*: choose a case folder, and open it as its ``path=`` URI.

        The HDF5 quick path: the user picks the directory that holds the case's
        ``*.h5`` files and the selector spells the URI instead of asking for the
        five parameters behind it. A cancelled choice leaves the free line alone.
        """
        folder = QFileDialog.getExistingDirectory(
            self, 'Dossier contenant les fichiers *.h5 du cas')
        if not folder:
            return
        self.freeText.setText(hdf5PathUri(folder))
