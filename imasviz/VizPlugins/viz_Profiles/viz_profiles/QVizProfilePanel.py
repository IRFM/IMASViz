# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The window the Profiles plugin opens: what this IDS holds, and a click to draw it.

This panel names quantities; it does not draw them. Every drawing gesture here ends
in a command of the application (`QVizPlotAsTable`, `QVizPlotOneNode`), so a window
this plugin opens is a Table Plot View, a curve figure or an image window like the
one the tree's own right click produces: it is in `api.figureframes` under a
`FigureTypes` key, so a line of the *Windows* menu and one of its *Delete*
sub-menu reach it, a ``.vsess`` session puts
it back, *Configure Plot* dresses its traces and the export dialogue offers its
formats. The panel carries none of that itself, which is why it carries no plot
widget either.

One thing the panels of a table do **not** get from that hand-off, and it is said
here because the offer counts the fields: the bars of an error field live in
`QVizCurveErrors`, which only a figure of curves owns (`test_58` pins it). A Table
Plot View panel therefore answers *Configure Plot* and no error-bar line, which is
why the 536 error fields `equilibrium` occurrence 0 earns are named as a refusal on
the panel rather than drawn as panels, and why a tab offers *Draw the selected
quantities* beside the page: one chosen alone opens the curve the bar belongs to.

What the old panel did instead was build its own grid (`QVizTablePlotView`), read
through `Viz_API.getAll_0D_1D_Nodes` and draw two rows per quantity. Two
consequences of that read are why it is gone, and both are measured:

* `getChildren_` keeps only a child that `isDynamicData()`. An IDS written at
  `homogeneous_time = 1` -- `magnetics`, `wall`, most of the dictionary -- has no
  dynamic array, so **nothing** in it satisfied the criteria. The plugin could not
  be offered for those IDSs because it had nothing to show them with;
* the pages were laid out by two separate spellings of `tab * 100 + panels so far`
  (`VizProfiles.py:169` and `:234`), which stop agreeing as soon as more than one
  tab is added at once -- showing one quantity twice and skipping its neighbour.
  Ten years of the reference case could not show it: 41 quantities, one page, one
  tab per click.

The abscissa question is asked once, in a combo, and answered by the strategy the
command honours: `TIME` walks the dynamic array, and `OWN_AXIS` leaves the choice
to the read -- which is what `New (default axis)` means in the tree's own menu.
There is no third entry, because a Table Plot View cannot be told to run every
panel along one named coordinate: its panels are independent by design, and a
combo promising what the command cannot do is a refusal the user has to discover
by clicking. What each strategy can carry is said on the tab, with the quantities
it leaves out named -- a quantity of two axes of its own is a picture, and
*Draw the selected quantities*, with one chosen, opens it as one.

The time cursors at the bottom drive the windows this panel opened rather than
holding an index of their own. A panel of a Table Plot View carries a slider per
axis its read pins (measured: `('AOS', 'equilibrium', 'time_slice')` on a panel of
`profiles_1d` drawn along the default axis), so moving one of these cursors asks
those panels to move theirs, which re-reads them through their own controls. Two
facts decided that shape: an index kept twice is an index that drifts, and the
panels' rows are what the read already asks. The band only offers a base that at
least one open window pins -- a panel running along the clock has no row for it, so
a cursor there would command nothing, and a slider whose number the numbers did not
come from is worse than no slider.

Nothing in this window opens a modal dialog. The old one asked which occurrence to
plot through a `QInputDialog` that a probe left alone for **240 s**, and asked how
many tabs to add through a second one, built with no parent. A question that
cannot be answered is a refusal in the log panel of the case, and a choice is a
control.
"""

import logging
import weakref

import shiboken6
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QListWidget,
                               QMainWindow, QPushButton, QTabWidget, QVBoxLayout,
                               QWidget)

from imasviz.VizDataAccess.QVizCurveAbscissa import TIME, axisPhrase
from imasviz.VizDataAccess.QVizSlices import QVizSlice
from imasviz.VizGUI.VizConfigurations.QVizConfigurationFile import \
    QVizConfigurationFile, QVizQuantity, PLOT
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence import \
    QVizLoadOccurrence
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsTable import \
    QVizPlotAsTable
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode import \
    QVizPlotOneNode
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizSliceControls import \
    QVizSliceControls
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizProfileOffer import \
    OWN_AXIS, PAGE, QVizProfileOffer
from imasviz.VizUtils import FigureTypes
from imasviz.Viz_API import QVizClosableWindow


class QVizProfilePage(QWidget):
    """One tab: the quantities of one array of structures, a page at a time.

    The list holds the page, not the group: a group of `equilibrium` can hold 50
    quantities and `core_profiles` several hundred, and the window the button
    opens holds at most `PAGE` panels. Showing a list longer than what a click can
    draw is how the old panel came to have tabs nobody could reach.
    """

    def __init__(self, panel, group):
        # The panel owns this widget through the tab bar; the way back is held
        # weakly, because a Qt widget freed by the cyclic collector while Qt still
        # owes it a paint event is how this package loses a process -- see the
        # rule in QVizCurveErrors' place in the curve frames.
        super().__init__(None)
        self._panel = weakref.ref(panel)
        self.group = group
        self.page = 0

        layout = QVBoxLayout(self)
        self.summary = QLabel(self)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.quantities = QListWidget(self)
        # One or several rows, chosen with the clicks the list already knows: a
        # selection the user can make is a selection the button honours, and a
        # single choice and a selection of five answer two different windows --
        # a curve figure and a table -- which the button below says.
        self.quantities.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(self.quantities, 1)

        buttons = QHBoxLayout()
        self.drawButton = QPushButton('Draw this page', self)
        self.drawButton.clicked.connect(self.drawPage)
        self.nextButton = QPushButton('Add the next page', self)
        self.nextButton.clicked.connect(self.addNextPage)
        self.oneButton = QPushButton('Draw the selected quantities', self)
        self.oneButton.clicked.connect(self.drawSelected)
        buttons.addWidget(self.drawButton)
        buttons.addWidget(self.nextButton)
        buttons.addWidget(self.oneButton)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.refresh()

    def panel(self):
        return self._panel()

    # ------------------------------------------------------------- the page
    def abscissa(self):
        """What this tab's pages are read along, as the group answers it.

        Asked of the panel every time, because the abscissa is a choice the user
        can change while this tab is open -- and the list, the count and the
        window must all answer for the same choice.
        """
        return self.panel().abscissa()

    def pages(self):
        return self.group.pages(self.abscissa())

    def refresh(self):
        pages = self.pages()
        if not pages:
            self.page = 0
        elif self.page >= len(pages):
            self.page = len(pages) - 1
        self.quantities.clear()
        current = pages[self.page] if pages else []
        for leaf in current:
            self.quantities.addItem(self.labelFor(leaf))
        self.summary.setText(self.summaryText(len(pages), current))
        self.drawButton.setEnabled(bool(current))
        self.nextButton.setEnabled(self.page + 1 < len(pages))

    def labelFor(self, leaf):
        """What one row of the list says about a quantity.

        The parametrized path, IDS root taken out: it is the spelling the tree
        carries, the one the legend of the window will carry, and it is the only
        thing that tells `boundary/x_point.r` from `constraints/x_point.r` when
        two tabs hold quantities of one name.
        """
        path = leaf.getParametrizedDataPath() or leaf.getPath() or leaf.getName()
        root = leaf.getIDSName() + '.'
        return path[len(root):] if path.startswith(root) else path

    def summaryText(self, pageCount, page):
        """How many quantities, which page, and what this abscissa cannot carry.

        The left-out count is spelled with the names, because a tab that shows 47
        of 50 rows and says nothing reads as a bug in the panel. A quantity of two
        axes of its own has no panel to sit in -- it is a picture -- and
        *Draw this quantity* opens it as one.
        """
        panel = self.panel()
        left = self.group.leftOut(self.abscissa())
        parts = ['%d quantities along %s, page %d of %d (%d on this page, %d per '
                 'page)' % (len(self.group.following(self.abscissa())),
                            panel.abscissaWords(), self.page + 1,
                            max(pageCount, 1), len(page), PAGE)]
        if left:
            parts.append('%d cannot be read along %s and are not on the pages: %s '
                         '-- they have two axes of their own, so *Draw the '
                         'selected quantities*, with that one alone chosen, '
                         'opens them as pictures.'
                         % (len(left), panel.abscissaWords(),
                            panel.namesOf(left)))
        elements = self.group.elementCount()
        if elements > 1:
            parts.append('the tree holds %d elements of these quantities: a page '
                         'draws the one the tree stands on, and each panel moves '
                         'its own index with the slider under it.' % elements)
        return '\n'.join(parts)

    # ------------------------------------------------------------- the click
    def drawPage(self):
        pages = self.pages()
        if self.page >= len(pages):
            return
        return self.panel().drawQuantities(self.group, pages[self.page])

    def addNextPage(self):
        """Put the page after this one in a window of its own, and follow it.

        A second window and not a second half of the first, because the layout of
        a Table Plot View asks its width once for the whole table: panels added to
        a window that is already full would be laid on a grid of one width and
        then relayed on another.
        """
        pages = self.pages()
        if self.page + 1 >= len(pages):
            return None
        self.page += 1
        self.refresh()
        return self.drawPage()

    def drawSelected(self):
        """The quantities the list stands on, in the order the list reads them.

        None selected is a refusal named; one is the tree's own gesture, so a
        quantity the list holds answers the figure its own axes call for --
        which is how the button opens a picture rather than a panel for a
        quantity of two axes the pages happen to carry; several are a Table Plot
        View of exactly those, in the order they stand in the list -- not the
        page, because a page of a hundred is what the other button draws, and a
        selection of five is what this one answers.
        """
        pages = self.pages()
        if self.page >= len(pages):
            return None
        page = pages[self.page]
        leaves = [page[row] for row in self.selectedRows()
                  if row < len(page)]
        if not leaves:
            logging.getLogger(self.panel().logOf()).info(
                'No quantity is selected in the "%s" tab: select one or more, '
                'or draw the whole page.' % self.group.title())
            return None
        if len(leaves) == 1:
            return self.panel().drawQuantity(leaves[0])
        return self.panel().drawQuantities(self.group, leaves)

    def selectedRows(self):
        """The selected rows of the list, in the order the list holds them.

        The list is the page, so its item order is the answer: a row the list
        no longer holds cannot be drawn, and a row held is the one the user's
        clicks stood on -- never the current row, which one of several carries.
        """
        return sorted(self.quantities.row(item)
                      for item in self.quantities.selectedItems())


class QVizProfilePanel(QVizClosableWindow, QMainWindow):
    """What one IDS occurrence holds that can be drawn, and the clicks to draw it."""

    def __init__(self, vizAPI, dataTreeView, idsName, occurrence,
                 figureKey=None):
        """
        Arguments:
            idsName, occurrence : what the plugin was offered on and what the case
                answered. Both are changeable here, because both are facts about
                the case the panel can ask the view about.
            figureKey      (str) : the key this window is registered under when
                something already named one -- a session file. Left free, the api
                hands out the next one.
        """
        super().__init__()
        self.api = vizAPI
        self.view = dataTreeView
        self.idsName = idsName
        self.occurrence = occurrence
        self.figureKey = vizAPI.FigureKeyFor(FigureTypes.PROFILESPLOTTYPE,
                                             figureKey)
        # The windows this panel opened, so the cursors have something to move.
        # Keyed, never held: a window the user deleted is out of `figureframes`
        # and asking it for its panels would be drawing a curve on a corpse.
        self._windows = []
        self._offer = None
        self._groups = []
        # The time bases this IDS answers, as slices. The band on screen holds the
        # subset of these that a window this panel opened actually pins -- see
        # `refreshCursors`.
        self._cursors = []

        body = QWidget(self)
        layout = QVBoxLayout(body)

        controls = QHBoxLayout()
        controls.addWidget(QLabel('Occurrence:', self))
        self.occurrenceBox = QComboBox(self)
        self.occurrenceBox.currentIndexChanged.connect(self.onOccurrenceChosen)
        controls.addWidget(self.occurrenceBox)
        controls.addWidget(QLabel('Plot along:', self))
        self.abscissaBox = QComboBox(self)
        self.abscissaBox.currentIndexChanged.connect(self.onAbscissaChosen)
        controls.addWidget(self.abscissaBox)
        controls.addWidget(QLabel('Plots per row:', self))
        self.columnsBox = QComboBox(self)
        # Left to the page size is what the window has always answered, and it
        # stays the default -- a page of two panels laid in three columns would
        # be a surprise nobody asked for.
        self.columnsBox.addItem('auto (from the page size)', None)
        for count in range(1, 13):
            self.columnsBox.addItem(str(count), count)
        controls.addWidget(self.columnsBox)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.explains = QLabel(self)
        self.explains.setWordWrap(True)
        layout.addWidget(self.explains)

        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs, 1)

        self.cursors = QVizSliceControls(self, foldable=True)
        self.cursors.changed.connect(self.moveCursors)
        layout.addWidget(self.cursors)

        self.setCentralWidget(body)
        self.setWindowTitle('%s IDS: what can be plotted [%s]'
                            % (idsName, self.figureKey))
        self.resize(820, 620)

        key = dataTreeView.dataSource.dataKey2(self.figureKey)
        vizAPI.AddNodeToFigure(self.figureKey, key,
                               (dataTreeView.dataSource.uri, None))
        vizAPI.figureframes[self.figureKey] = self

        self.ensureLoaded()
        self.rebuild()

    def windowApi(self):
        """The api this window is registered in -- the one that holds the rule.

        This panel is a top-level window: it is registered in `figureframes`
        like any figure, but no `QMdiSubWindow` sees its close box, so the rule
        has to be asked of the window itself. Answering it is what makes the
        close box cost the same as the *Delete* line of the *Windows* menu,
        whichever of the two the user clicks.
        """
        return self.api

    @staticmethod
    def findOpen(vizAPI, view, idsName):
        """A panel already opened for that IDS of this case, or None.

        The entry is offered per IDS root, and the case answers that IDS with one
        set of quantities: a second window for the same IDS would ask the same
        questions twice and hold two occurrence choices for one answer. It is
        looked for in the api's figures -- the panel registers itself there --
        and matched on the IDS it was built for and the case it belongs to. A
        frame a Qt ``deleteLater`` has not run yet keeps its Python wrapper, so
        the one already gone is skipped rather than raised by the hand that
        closes it.
        """
        for frame in list(vizAPI.figureframes.values()):
            if not isinstance(frame, QVizProfilePanel):
                continue
            if frame.idsName != idsName:
                continue
            if frame.view is None or frame.view.dataSource.uri != \
                    view.dataSource.uri:
                continue
            if shiboken6.isValid(frame):
                return frame
        return None

    # ------------------------------------------------------------------ state
    def groups(self):
        """The tabs this panel holds, in the order they were laid on the bar."""
        return list(self._groups)

    def ensureLoaded(self):
        """Have the view hold the tree of this IDS at this occurrence.

        The plugin's entry asks the api to load it, and that load is an
        asynchronous walk. The tabs are built on the tree that walk produces, so a
        panel that starts before it is over is a blank window with no reason: the
        session restore already loads synchronously for the same reason. Measured
        cost on the reference case: **0,6 s** for `equilibrium`.
        """
        key = '%s/%s' % (self.idsName, self.occurrence)
        if key not in getattr(self.view, 'ids_roots_occurrence', {}):
            QVizLoadOccurrence(self.view, self.idsName, self.occurrence,
                               asynch=False).execute()

    def logOf(self):
        """The log panel of the case this panel belongs to.

        A generic logger writes to a file nobody reads; the log of the shot view is
        the one the application shows.
        """
        return self.view.uri

    def occurrences(self):
        """Which occurrences this case holds, as the view answers it.

        The view's answer and not a count off the data dictionary: on this
        IMAS-Python the dictionary's `getMaxOccurrences` does not exist, and the
        question the old plugin asked with it is what a probe sat in a modal
        dialog for.
        """
        try:
            return list(self.view.occurrences.occurrencesOf(self.idsName))
        except Exception as e:
            logging.getLogger(self.view.uri).error(
                'The occurrences of the %s IDS could not be asked of this case: '
                '%s: %s' % (self.idsName, type(e).__name__, e))
            return [self.occurrence]

    def offer(self):
        return self._offer

    def abscissa(self):
        """The strategy the combo stands for: TIME, or the read's own choice."""
        chosen = self.abscissaBox.currentData()
        return TIME if chosen == TIME else OWN_AXIS

    def abscissaWords(self):
        chosen = self.abscissaBox.currentData()
        return self.abscissaBox.currentText() if chosen else 'no axis'

    def columns(self):
        """How many panels a row holds in a window this panel opens, or None.

        `None` is the width the window has always answered from how many panels
        it holds; a number is the one the user left on the combo. Asked when a
        page is drawn, so the choice on the combo is the one the next window
        wears -- the windows already opened keep the width they were drawn with.
        """
        return self.columnsBox.currentData()

    def namesOf(self, leaves):
        """The quantities a refusal names, bounded so the line stays readable."""
        shown = [leaf.getName() for leaf in leaves[:6]]
        more = len(leaves) - len(shown)
        return ', '.join(shown) + (' (+%d more)' % more if more > 0 else '')

    # --------------------------------------------------------------- rebuild
    def rebuild(self):
        """Ask the view what this occurrence holds, and put the tabs back.

        Called when the panel opens and whenever the occurrence or the abscissa
        changes: the offer is a walk of the view's own nodes, so the tabs are what
        the tree holds, including what the user set on a node.
        """
        self.tabs.clear()
        self._groups = []
        self.cursors.setSlices([])
        self.fillOccurrenceBox()
        try:
            self._offer = QVizProfileOffer(self.view, self.idsName,
                                           self.occurrence)
            groups = self._offer.timeGroups() + self._offer.staticGroups()
        except ValueError as e:
            # The load is a command's job and this one refused to do it, or the
            # walk found no tree. Either way the window says which.
            self.explains.setText(str(e))
            return

        refusal = self._offer.refusal() if not groups else None
        if refusal:
            self.explains.setText(refusal)
            return
        self._groups = groups
        # Both combos before the tabs: a page asks the abscissa combo which
        # quantities its page holds, so the choice has to be on screen by the time
        # the first row is written.
        self.fillAbscissaBox()
        for group in groups:
            page = QVizProfilePage(self, group)
            self.tabs.addTab(page, group.title())
        self.explains.setText(self.summaryText())
        self._cursors = [QVizSlice(axis, length=axis.length,
                                   index=axis.index if axis.index is not None
                                   else 0)
                         for axis in self._offer.timeBases()]
        self.refreshCursors()

    def refreshCursors(self):
        """Offer a cursor only for a time base an open window actually pins.

        A panel that runs its curve along the clock has no slider for it -- the
        array *is* its abscissa -- so a cursor there would move nothing. Measured
        on the reference case: the 0D quantities of `time_slice/boundary` are drawn
        as histories under both strategies and answer no row, while `profiles_1d`
        read along `psi` answers a `time_slice` row per panel. Showing a slider
        that commands nothing is worse than showing none, because the next reader
        believes the index on screen is what the numbers came from.
        """
        pinned = set()
        for figureKey in self._windows:
            panelsOf = getattr(self.api.figureframes.get(figureKey), 'panels',
                               None)
            if panelsOf is None:
                continue
            for panel in panelsOf():
                pinned.update(panel.sliceControls.keys())
        self.cursors.setSlices([one for one in self._cursors
                                if one.key in pinned])

    def summaryText(self):
        """What the whole IDS answers, in the unit the tabs count in.

        The error fields are named as a count and refused, not hidden: they are
        536 of the 727 quantities `equilibrium` occurrence 0 answers, and the
        application draws them as bars on the curve they belong to. If the tensor
        filter is on, the tabs can only hold what survived it, and the sentence
        says so rather than inventing a number for what was pruned away.
        """
        parts = ['%s occurrence %d: %d tabs, %d quantities.'
                 % (self.idsName, self.occurrence, len(self._groups),
                    self._offer.quantityCount())]
        errors = self._offer.errorFields()
        if errors:
            parts.append('%d error fields are not plotted here: they are drawn as '
                         'bars on the curve they belong to.' % errors)
        if self._offer.tensorFilterIsOn():
            parts.append('The preference *Show only tensors rank >= 1* is on, so '
                         'these tabs hold what survived it.')
        return ' '.join(parts)

    def fillOccurrenceBox(self):
        """The occurrences of this IDS the case holds, the current one first.

        Rebuilt rather than kept: the same view can be asked for another
        occurrence while this panel is open, and the answer belongs to the case.
        """
        known = self.occurrences()
        if self.occurrence not in known:
            known.insert(0, self.occurrence)
        self.occurrenceBox.blockSignals(True)
        self.occurrenceBox.clear()
        for occurrence in known:
            self.occurrenceBox.addItem(str(occurrence), occurrence)
        self.occurrenceBox.setCurrentIndex(known.index(self.occurrence))
        self.occurrenceBox.blockSignals(False)

    def fillAbscissaBox(self):
        """The two readings the commands this panel calls can honour.

        `TIME` walks the dynamic array; anything else leaves the read to answer
        per quantity, which is the `New (default axis)` entry of the tree's own
        menu. The label of the second says what the first quantity of the offer
        would be read against, because "default" is otherwise a word with no
        picture attached.
        """
        known = self._offer.abscissae() if self._offer else []
        choices = []
        if TIME in known:
            choices.append((TIME, 'time (the clock of the IDS)'))
        other = [abscissa for abscissa in known if abscissa != TIME]
        if other:
            choices.append((OWN_AXIS, 'its own axis (e.g. %s)'
                                       % axisPhrase(other[0])))
        if not choices:
            choices = [(OWN_AXIS, 'whatever axis it has')]
        current = self.abscissaBox.currentData()
        self.abscissaBox.blockSignals(True)
        self.abscissaBox.clear()
        for data, words in choices:
            self.abscissaBox.addItem(words, data)
        position = next((index for index, (data, _) in enumerate(choices)
                         if data == current), 0)
        self.abscissaBox.setCurrentIndex(position)
        self.abscissaBox.blockSignals(False)

    # -------------------------------------------------------------- gestures
    def onOccurrenceChosen(self):
        occurrence = self.abscissaBoxOk(self.occurrenceBox.currentData())
        if occurrence is None or occurrence == self.occurrence:
            return
        self.occurrence = occurrence
        self.ensureLoaded()
        self.fillOccurrenceBox()
        self.fillAbscissaBox()
        self.rebuild()

    @staticmethod
    def abscissaBoxOk(value):
        return None if value is None else int(value)

    def onAbscissaChosen(self):
        for index in range(self.tabs.count()):
            self.tabs.widget(index).refresh()

    def moveCursors(self):
        """Move the panels of the windows this panel opened to where a cursor stands.

        `setIndex` on a panel's own controls emits that panel's `changed`, which is
        what re-reads it -- so the index lives in one place, the row the panel
        already answers with. A panel whose read draws this axis has no row for it
        and is left alone; asking it to move would be asking for an index of an
        axis its curve runs along.
        """
        for key, index in self.cursors.indices().items():
            for figureKey in list(self._windows):
                frame = self.api.figureframes.get(figureKey)
                panelsOf = getattr(frame, 'panels', None)
                if panelsOf is None:
                    continue
                for panel in panelsOf():
                    panel.sliceControls.setIndex(key, index)

    def drawQuantities(self, group, leaves):
        """One Table Plot View for a page of quantities. Returns the frame, or None.

        The quantities are named to the command through a configuration -- the same
        shape a ``.pcfg`` file holds -- because that is the seam the command
        already offers, and a page drawn this way can be saved and re-applied. The
        name given to it names this panel, so a path the tree no longer holds is
        refused with a sentence about where it came from.
        """
        configuration = QVizConfigurationFile(
            kind=PLOT,
            quantities=[QVizQuantity(leaf.getPath(), self.occurrence, None, None,
                                     self.view.dataSource.uri)
                        for leaf in leaves],
            abscissa=TIME if self.abscissa() == TIME else None,
            path='the %s IDS panel of occurrence %d' % (self.idsName,
                                                        self.occurrence))
        try:
            command = QVizPlotAsTable(self.view,
                                      plotAxis='TIME' if self.abscissa() == TIME
                                      else 'DEFAULT',
                                      configuration=configuration,
                                      columns=self.columns())
            frame = command.execute()
        except ValueError as e:
            logging.getLogger(self.view.uri).error(str(e))
            return None
        if frame is None:
            return None
        self.api.addPlotWidgetToMDI(frame)
        self._windows.append(frame.figureKey)
        self.refreshCursors()
        return frame

    def drawQuantity(self, leaf):
        """One quantity in the frame its axes call for. Returns the frame, or None.

        This is the tree's own *Plot this node* gesture, so a quantity of two axes
        leaves the panel and becomes a picture -- which is what the tab's count of
        left-out quantities promises.
        """
        command = QVizPlotOneNode(self.view, leaf,
                                  alongTime=True if self.abscissa() == TIME
                                  else False)
        frame = command.execute()
        if frame is None:
            # The reason is in the log panel of this shot view already.
            return None
        if command.builtFigure:
            self.api.addPlotWidgetToMDI(frame)
        frame.show()
        return frame
