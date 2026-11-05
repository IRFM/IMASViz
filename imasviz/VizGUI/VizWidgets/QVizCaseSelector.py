# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import logging
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,
                               QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QPushButton,
                               QVBoxLayout, QWidget)

from imasviz.VizDataSource.QVizIMASDataSource import caseUri, hdf5PathUri
from imasviz.VizGUI.VizWidgets.QVizIMASdbBrowserWidget import (
    caseRootForUser, localCases)
from imasviz.VizUtils import QVizPreferences


class QVizCaseSelector(QWidget):
    """The URI-first selection of the start window.

    A flat list of the local cases, each row a shape the user chose at the
    *Affichage* box -- the URI the Access Layer opens the case with (the
    default), or the backend, database, shot and run behind it -- whose data
    and tooltip are always that URI; the selection -- by double click or
    *Ouvrir* -- is handed to the caller through `uriOpened` **as a URI**. A free
    line takes
    any other URI (a UDA case, a remote case, or one the local walk does not
    reach), and *Dossier…* turns a chosen folder of ``*.h5`` into the ``path=``
    URI. The whole thing emits URIs and never the five derived parameters --
    that is the point of a URI-first selection: what the user chose is the
    string the case is opened with.
    """

    uriOpened = Signal(str)

    # What the *Trier par* box offers, in the order the box lays them out.
    # Each of the four is one of QVizPreferences.SORT_KEYS, spelled by the name
    # the preferences file takes (lower, identifier-safe); the display is the
    # French name the UI has settled on, so a user sees "Tir" rather than "shot"
    # -- but the box, when asked through `currentData`, answers the file name.
    SORT_ITEMS = (
        ('uri', 'URI'),
        ('database', 'Base'),
        ('backend', 'Backend'),
        ('shot', 'Tir'),
        ('run', 'Run'),
    )

    # What the *Affichage* box offers: the two shapes a row may wear. ``uri``
    # (the default) is the URI the case is opened with; ``parsed`` is the
    # backend, database, shot and run the scanner read out of it. The box is at
    # the shape the preferences hold, and a hand on it re-lays the list and
    # remembers the shape for the next session.
    VIEW_ITEMS = (
        ('uri', 'URI'),
        ('parsed', 'Cas'),
    )

    def __init__(self, parent=None):
        super(QVizCaseSelector, self).__init__(parent)

        layout = QVBoxLayout(self)

        # The controls of the list: the shape of the rows, the sort key, its
        # direction, and the two protocol boxes. The state is read from the
        # preferences file the last time the user touched any of them, so a
        # session that has not chosen anything sees the list as it has always
        # been (the URI, database, ascending, both protocols on) -- the
        # defaults the preferences reader gives when the file is absent, and the
        # state the file writes when the user first chooses a different one.
        # They are laid on **two lines**: the panel is the eighth of the
        # window, and a single row of all eight controls does not fit in
        # that width -- the boxes squeezed until they overlapped, which is
        # what a row that asks for more width than the panel has does. A row
        # per question group stays inside the width, and each group keeps its
        # label with its controls.
        shapeRow = QHBoxLayout()
        self.viewShapeLabel = QLabel('Affichage', self)
        shapeRow.addWidget(self.viewShapeLabel)
        self.viewBox = QComboBox(self)
        for key, label in self.VIEW_ITEMS:
            self.viewBox.addItem(label, key)
        self.viewBox.setToolTip(
            'La forme des lignes : la URI d\'ouverture, ou le backend, la base, '
            'le tir et le run. La donnée et l\'infobulle restent toujours la URI.')
        shapeRow.addWidget(self.viewBox)
        shapeRow.addSpacing(12)
        self.sortKeyLabel = QLabel('Trier par', self)
        shapeRow.addWidget(self.sortKeyLabel)
        self.sortKeyBox = QComboBox(self)
        for key, label in self.SORT_ITEMS:
            self.sortKeyBox.addItem(label, key)
        # The box must be put in the row: before this, its addWidget had gone
        # missing, and the box floated at (0,0) over the controls to its left
        # -- the overlap a user saw as "one list spilling over another". A
        # box with a parent and no layout is never laid out, and the geometry
        # test at the panel width is what pins it back in the row.
        shapeRow.addWidget(self.sortKeyBox)
        self.sortDirButton = QPushButton('↓', self)
        self.sortDirButton.setCheckable(True)
        self.sortDirButton.setChecked(False)          # False = asc (montant)
        self.sortDirButton.setToolTip(
            'Le sens du tri. Non cliqué, montant (12 avant 999); cliqué, '
            'descendant (999 avant 12).')
        shapeRow.addWidget(self.sortDirButton)
        shapeRow.addStretch(1)
        layout.addLayout(shapeRow)
        protocolRow = QHBoxLayout()
        self.filterLabel = QLabel('Afficher', self)
        protocolRow.addWidget(self.filterLabel)
        self.filterHDF5 = QCheckBox('HDF5', self)
        self.filterHDF5.setChecked(True)
        self.filterMDS = QCheckBox('MDS+', self)
        self.filterMDS.setChecked(True)
        protocolRow.addWidget(self.filterHDF5)
        protocolRow.addWidget(self.filterMDS)
        protocolRow.addStretch(1)
        layout.addLayout(protocolRow)
        # The controls of the list, all of them: the labels and the boxes they
        # name. `presentAs` hides the whole group at once when the panel is not
        # showing the list it acts on -- a free URI line needs none of sort,
        # shape or protocol -- and the group is kept whole so the list mode can
        # put it back in one answer.
        self._listControls = (
            self.viewShapeLabel, self.viewBox,
            self.sortKeyLabel, self.sortKeyBox, self.sortDirButton,
            self.filterLabel, self.filterHDF5, self.filterMDS)

        self.listView = QListWidget(self)
        self.listView.setToolTip(
            'Les cas locaux trouvés. Un double-clic ouvre le cas choisi. '
            'Le tri et le filtre s\'appliquent sur cette liste.')
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
        # The controls: a touched shape, sort key or direction, or a touched
        # protocol box, answers for itself -- re-shape the rows the list shows,
        # and remember the choice in the preferences file so the next run does
        # not ask. During _syncControls, the signals are blocked, so the
        # initial read of the preferences does not fire a change.
        self.viewBox.currentIndexChanged.connect(self._onViewTouched)
        self.sortKeyBox.currentIndexChanged.connect(self._onSortTouched)
        self.sortDirButton.toggled.connect(self._onSortTouched)
        self.filterHDF5.toggled.connect(self._onFilterHDF5Touched)
        self.filterMDS.toggled.connect(self._onFilterMDSTouched)

        # The state a refresh starts with: the list is empty until refresh is
        # called, and the sync of the controls is what sets them from the
        # preferences -- so a test that only builds the widget and inspects the
        # controls still sees the state a fresh installation would answer.
        self.username = None
        self._allCases = []
        self._shapedCases = []
        self._syncControls()

    def presentAs(self, mode):
        """Show the list or the free line, never the two at the same time.

        The list mode shows the list and its whole controls row, and hides
        the free line. The free mode shows the free line -- and keeps the
        buttons, since a URI can still be opened, copied or turned in from a
        folder -- and hides the list and every control of it: a free URI is
        subject to none of the shape, the sort or the protocol, so the row
        would sit there doing nothing, and hiding it is the mode's answer to
        that, not a state the user left behind. A word that names neither is
        refused by the word, so a caller that misspells its mode does not
        quietly get a half-present panel.
        """
        if mode not in ('list', 'free'):
            raise ValueError(
                '%r is not a presentation of the case panel: name "list", '
                'or "free"' % (mode,))
        listMode = (mode == 'list')
        self.listView.setVisible(listMode)
        self.freeText.setVisible(not listMode)
        for control in self._listControls:
            control.setVisible(listMode)
        # The buttons act on whichever of the two is visible, so they stay
        # with the panel in both presentations.
        self.openButton.setVisible(True)
        self.copyButton.setVisible(True)
        self.folderButton.setVisible(True)

    # The controls: what they say, what they refuse, and what they persist.

    def _syncControls(self):
        """Read the controls from QVizPreferences, without touching the file.

        The signals are blocked on the way out: a read is not a change, and a
        test that builds the widget and looks at its controls before any
        refresh should see the preferences state, not the moment of the first
        read.
        """
        for control in (self.viewBox, self.sortKeyBox, self.sortDirButton,
                        self.filterHDF5, self.filterMDS):
            control.blockSignals(True)
        self._setBoxTo(self.viewBox, QVizPreferences.Uri_list_view)
        self._setBoxTo(self.sortKeyBox, QVizPreferences.Uri_list_sort_key)
        self.sortDirButton.setChecked(
            QVizPreferences.Uri_list_sort_direction == 'desc')
        self.filterHDF5.setChecked(bool(QVizPreferences.Uri_list_filter_HDF5))
        self.filterMDS.setChecked(
            bool(QVizPreferences.Uri_list_filter_MDSplus))
        for control in (self.viewBox, self.sortKeyBox, self.sortDirButton,
                        self.filterHDF5, self.filterMDS):
            control.blockSignals(False)

    @staticmethod
    def _setBoxTo(box, value):
        """Put `box` on the item whose data is `value`, or on 0 if none is.

        The box's currentData carries the file name, its currentText the French
        label, and the two are in the same place. A value the box does not carry
        -- a preference the class answers but the box never offers -- falls
        through to the first entry, so a sync that reads a word the box refused
        never throws and never points at nothing.
        """
        for i in range(box.count()):
            if box.itemData(i) == value:
                box.setCurrentIndex(i)
                return
        box.setCurrentIndex(0)

    def _onViewTouched(self, *args):
        """A shape was chosen at the *Affichage* box: re-lay the rows and
        remember the shape for the next session.

        ``currentIndexChanged`` fires when a *sync* reads the file into the box
        too, but ``_syncControls`` blocks the box's signals on the way out, so
        this handler only runs for a hand -- the same way `_onSortTouched` and
        the two filter handlers run. Nothing is opened here: the rows keep the
        case in their data and are only re-shown in the shape asked.
        """
        QVizPreferences.Uri_list_view = self.viewBox.currentData()
        self._applyControls()
        QVizPreferences.persist(Uri_list_view=QVizPreferences.Uri_list_view)

    def _onSortTouched(self, *args):
        """A sort key or its direction changed: re-order the list and remember
        both, so the next session does not ask again.

        ``currentIndexChanged`` fires when a *sync* reads the file into the
        box, so it would have to refuse a signal it has not actually changed
        (the box is at the state the file spells). It does not, because
        ``_syncControls`` blocks the box's signals on the way out -- and this
        handler only runs for a hand.
        """
        QVizPreferences.Uri_list_sort_key = self.sortKeyBox.currentData()
        QVizPreferences.Uri_list_sort_direction = (
            'desc' if self.sortDirButton.isChecked() else 'asc')
        self._applyControls()
        QVizPreferences.persist(
            Uri_list_sort_key=QVizPreferences.Uri_list_sort_key,
            Uri_list_sort_direction=QVizPreferences.Uri_list_sort_direction)

    def _onFilterHDF5Touched(self, checked):
        self._filterTouched(self.filterHDF5, self.filterMDS, 'HDF5')

    def _onFilterMDSTouched(self, checked):
        self._filterTouched(self.filterMDS, self.filterHDF5, 'MDS+')

    def _filterTouched(self, sender, other, name):
        """A protocol box was touched: if both would be off, refuse and keep
        the one the user just tried to turn off.

        The list is *which kind of case to open*, and an empty list is a place
        to look that shows nothing -- so the two boxes have one rule between
        them: at least one stays checked, and the one the user just turned off
        is the one that stays. The user is told by what the box tried to become
        and what it kept.
        """
        if not sender.isChecked() and not other.isChecked():
            sender.blockSignals(True)
            sender.setChecked(True)
            sender.blockSignals(False)
            logging.getLogger('logPanel').warning(
                'Le protocole %s restait masqué : au moins un doit rester '
                'affiché, et c\'est lui qui reste coché.' % name)
            return
        self._applyControls()
        QVizPreferences.Uri_list_filter_HDF5 = int(
            self.filterHDF5.isChecked())
        QVizPreferences.Uri_list_filter_MDSplus = int(
            self.filterMDS.isChecked())
        QVizPreferences.persist(
            Uri_list_filter_HDF5=QVizPreferences.Uri_list_filter_HDF5,
            Uri_list_filter_MDSplus=QVizPreferences.Uri_list_filter_MDSplus)

    def _visibleBackends(self):
        backends = set()
        if self.filterHDF5.isChecked():
            backends.add('HDF5')
        if self.filterMDS.isChecked():
            backends.add('MDS+')
        return backends

    @staticmethod
    def _numericOrWord(value):
        """The ordering of a shot or a run: a number when it is one, a word
        when it is not, in a list that stays comparable either way.

        The tuple ``(0, number)`` comes before ``(1, word)`` in sort order,
        which is not the order the case folders spell -- a case stored under a
        name sorts after the ones with numbers, which is what a user would not
        expect from a *run* number. The number is the number's order, 12
        before 999, not 999 before 54924, and the word is the word.
        """
        s = str(value)
        if s.isdigit():
            return (0, int(s))
        return (1, s)

    def _sortFunction(self, key):
        """The ordering key for `key`: a function from a case to a comparable.

        ``shot`` and ``run`` are read as numbers where they read as numbers --
        the number's order, not the word's -- and ``uri`` sorts by the URI
        string the case opens on, so the two spellings keep their order (HDF5
        before MDS+, path before parameters within each). ``database`` and
        ``backend`` sort by their strings, and the fallback is an order the
        list answers but that nothing else asks for.
        """
        username = self.username
        numWord = QVizCaseSelector._numericOrWord
        if key == 'uri':
            return lambda c: QVizCaseSelector.uriOf(username, c)
        if key == 'database':
            return lambda c: c['database']
        if key == 'backend':
            return lambda c: c['backend']
        if key == 'shot':
            return lambda c: numWord(c['shot'])
        if key == 'run':
            return lambda c: numWord(c['run'])
        # A key the box did not offer is a state nothing else can reach; the
        # fallback is a word in the case's database, which is the same as the
        # 'database' key and is what the list answers.
        return lambda c: (c['database'], c['backend'],
                          numWord(c['shot']), numWord(c['run']))

    def _applyControls(self):
        """Re-filter and re-sort the rows the list shows; lay them.

        The state a change is read against is the current state of the
        controls -- the user's hand, not the state a sync laid out at start-up
        -- so a change that is a hand re-shapes the list, and a test that only
        builds the widget and looks at its controls sees the state the user
        last chose (as read into the file, and as laid back in).
        """
        visible = self._visibleBackends()
        filtered = [c for c in self._allCases if c['backend'] in visible]
        key = QVizPreferences.Uri_list_sort_key
        reverse = QVizPreferences.Uri_list_sort_direction == 'desc'
        key_func = self._sortFunction(key)
        filtered.sort(key=key_func, reverse=reverse)
        self._shapedCases = filtered
        # The shape the rows wear is read here, not at the box, so any handler
        # that re-lays the list -- a sort, a filter, a shape -- lays the same
        # shape the user last chose at the box, and the box never drifts from
        # what it shows.
        view = QVizPreferences.Uri_list_view
        self.listView.clear()
        for case in filtered:
            uri = QVizCaseSelector.uriOf(self.username, case)
            label = uri if view == 'uri' else QVizCaseSelector.labelOf(case)
            item = QListWidgetItem(label, self.listView)
            item.setData(Qt.UserRole, uri)
            item.setToolTip(uri)
        return filtered

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
        """Fill the list from `casesFor`, through the user's last chosen sort
        and protocol filter. Returns the cases it laid in -- the ones the list
        shows, so a test that reads them through the same entry reads what the
        user sees.

        Each row carries its URI both as data and as its tooltip, so a
        selection answers the URI without a second walk of the case, and a
        hover shows the user the very string that will be opened. The state a
        first read answers is the user's last chosen one (as read into
        ``QVizPreferences`` from ``~/.imasviz/preferences``, or the defaults
        the reader gives when the file is absent), and a test that wants a
        different starting state asks the preferences reader directly rather
        than the widget.
        """
        self.username = username
        self._allCases = self.casesFor(username)
        self._syncControls()
        self._applyControls()
        return self._shapedCases

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
