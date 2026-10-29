# Copyright holders : Commissariat à l’Energie Atomique and aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A session keeps what a hand styled, and only that.

``test_71`` pins the window: the *Configure Plot* line, the row that reaches its
own trace, the record of which traces were touched. ``test_66`` pins the file: a
``<Style>`` written is a ``<Style>`` read. What neither can pin is the promise the
two exist for -- colour a trace this morning, close the application, open the
session tomorrow, and the trace is still that colour.

Everything here goes through the gestures. The colour is set the way a user sets
it (open the window, pick a colour, accept), the session is written by
``QVizSaveSession`` from the api of the run, and it is put back by
``QVizRestoreSession`` on a **second** api that never saw the window -- the session
the user comes back to, since the first one is what closes with the window. Each
test gets an api of its own, because ``figureframes`` is what the save walks: a
run shared between tests would write the windows of its neighbours into every
file, and a test that says "this file holds no style" would be reading somebody
else's figure. The case itself is one record per process, so reopening the view
costs the tree walk and nothing else.

Two things the file must not do, and both are assertions here rather than
incidental:

* it must not write the traces nobody touched. Since T33 every trace carries a
  pen, so a session describing every pen would freeze the palette into the file: a
  case opened a month later would draw the colours of the day it was saved instead
  of the contrast those colours were chosen for. Measured on the reference case, an
  untouched two-trace figure writes **0** ``<Style>`` and one coloured trace writes
  **1**;
* a style must land on the quantity that was styled. A figure holds its traces in
  the order they were drawn, which is not an identity: a session that dressed a
  trace by its position in the window would redress another one as soon as the user
  plotted a quantity in front of it.

For the same reason a Table Plot View is pinned here and not only on stubs: its
panels are filled from a configuration file the command writes, so the node a panel
holds is not necessarily the node the gesture named -- and the style has to find
its panel anyway.
"""

import pytest
from PySide6.QtWidgets import QMdiArea

from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizConfigurations.QVizSessionFile import QVizSessionFile
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectNodes \
    import QVizSelectNodes
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsTable \
    import QVizPlotAsTable
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
    import QVizPlotOneNode
from imasviz.VizGUI.VizGUICommands.VizSession.QVizRestoreSession \
    import QVizRestoreSession
from imasviz.VizGUI.VizGUICommands.VizSession.QVizSaveSession \
    import QVizSaveSession
from imasviz.VizGUI.VizPlot.QVizCurveColors import penFor
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPanel import QVizPanel
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlot import QVizTablePlot
from imasviz.Viz_API import Viz_API

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip)
from support import ownership

IDS_NAME = 'magnetics'
OCCURRENCE = 0
FIRST = 'magnetics/flux_loop(0)/flux/data'
SECOND = 'magnetics/bpol_probe(0)/field/data'
THIRD = 'magnetics/flux_loop(1)/flux/data'
# A leaf the tree holds and the read answers nothing for along the plotted axis: it
# is in the file, it is in the case, and it draws no trace -- so its style has to be
# named as lost rather than dropped without a word.
NO_TRACE = 'magnetics/bpol_probe(0)/voltage/data'
# A path the tree does not hold at all: the other half of the same refusal.
NOT_IN_THE_CASE = 'magnetics/flux_loop(9999)/flux/data'

HAND = (255, 0, 0)
OTHER = (0, 0, 255)
pytestmark = [pytest.mark.case, pytest.mark.dd, pytest.mark.ui]


class Run:
    """The gestures of one IMASViz run, on one ``Viz_API``.

    The api is built on a ``QMdiArea``, as the application builds it on its central
    area: without one, ``addPlotWidgetToMDI`` keeps the subwindow it creates on
    itself and the earlier windows lose their Qt owner (``support/ownership.py``).
    """

    def __init__(self, mdi):
        self.mdi = mdi
        self.api = Viz_API(parent=mdi)

    def freshApi(self):
        """An api that never saw the windows being put back: another run."""
        return Viz_API(parent=self.mdi)

    def view(self):
        """The reference case, with `magnetics` loaded in it."""
        source = QVizDataSourceFactory().create(CASE_URI)
        source.dd_version = CASE_DATA_DICTIONARY_VERSION
        if self.api.isDataSourceAlreadyOpened(source):
            view = self.api.GetDTVFor(source.getKey())
        else:
            view = self.api.CreateDataTree(source).dataTreeView
            self.api.ShowDataTree(view)
        if not self.api.IDSDataAlreadyFetched(view, IDS_NAME, OCCURRENCE):
            QVizLoadOccurrence(dataTreeView=view, idsName=IDS_NAME,
                               occurrence=OCCURRENCE, asynch=False).execute()
        return view

    @staticmethod
    def node(view, path):
        for node in view.signalsList:
            if node.getPath() == path:
                return node
        raise AssertionError('"%s" is not a leaf of this tree' % path)

    def figure(self, view, *paths):
        """One curve figure holding those quantities, drawn as the menu draws it."""
        frame = None
        for path in paths:
            frame = QVizPlotOneNode(dataTreeView=view,
                                    treeNode=self.node(view, path),
                                    intoFigureKey=None if frame is None
                                    else frame.figureKey,
                                    alongTime=True).execute()
            assert type(frame) is QVizCurvePlot
        return frame

    def table(self, view, *paths):
        """A Table Plot View, one panel per quantity, drawn as the menu draws it."""
        selector = QVizSelectNodes(view)
        selector.unselectAll()
        for path in paths:
            selector.selectNode(self.node(view, path), view)
        frame = QVizPlotAsTable(view, plotAxis='TIME').execute()
        assert isinstance(frame, QVizTablePlot)
        return frame


@pytest.fixture
def run(qapp, tmp_path, monkeypatch):
    """One run of its own: a $HOME it may write into, one api, one central area.

    The run is kept for the whole session, as the application keeps its windows:
    a shown frame freed by the collector is a frame Qt still owes a paint event.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    monkeypatch.setenv('HOME', str(tmp_path))
    return ownership.keep(Run(QMdiArea()))


# --------------------------------------------------------------------- helpers

def rgbOf(curve):
    """The colour the curve is drawn with -- a pen the figure set, or a bare tuple."""
    pen = curve.opts['pen']
    return pen if isinstance(pen, tuple) else pen.color().getRgb()[:3]


def palette(index):
    return penFor(index).color().getRgb()[:3]


def colourATrace(window, which=0, rgb=HAND):
    """The styling window, opened and used the way a user uses it."""
    dialog = window.styling.show()
    row = dialog.curves[which]
    row.colorButton.setColor(rgb)
    row.colorButton.sigColorChanging.emit(row.colorButton)
    return dialog


def boldALabel(window, side='left'):
    """The same window, on the text tab: bold the label of one axis."""
    dialog = window.styling.show()
    editor = [row for row in dialog.axisEditors if row.key == side][0]
    editor.boldButton.toggle()
    return dialog


def saved(body):
    """The one figure of a written file, whatever window it describes."""
    return [figure for figure in body.figures if figure.key][0]


def styledIn(session):
    """Every `<Style>` of a written session, as [(path, trace, color)]."""
    return [(quantity.path, style.trace, style.attributes.get('color'))
            for figure in session.figures
            for quantity in figure.quantities
            for style in quantity.styles]


def quantitiesOf(saved, key):
    figure = [figure for figure in saved.figures if figure.key == key][0]
    return dict((quantity.path, quantity) for quantity in figure.quantities)


def colours(frame):
    """{path: colour} for every trace a curve figure draws."""
    return {treeNode.getPath(): rgbOf(curve)
            for treeNode, _, curve in frame.tracesForStyling()}


# ------------------------------------------------------------------- a figure

@pytest.mark.ui
def test_a_colour_a_hand_left_comes_back_with_the_session(run):
    view = run.view()
    frame = run.figure(view, FIRST, SECOND)
    colourATrace(frame, which=1).accept()
    assert rgbOf(frame.curves()[1]) == HAND
    path = QVizSaveSession(run.api, name='colour').execute()

    restored = run.freshApi()
    QVizRestoreSession(restored, path=path).execute()
    again = restored.figureframes[frame.figureKey]

    assert colours(again) == {FIRST: palette(0), SECOND: HAND}
    # A replay is a hand: closing that run again keeps what came back.
    writtenTwice = QVizSessionFile.read(
        QVizSaveSession(restored, name='colour2').execute())
    assert styledIn(writtenTwice) == [(SECOND, 0, '#ff0000')]


@pytest.mark.ui
def test_a_bold_label_of_the_figure_is_written_under_the_figure(run):
    view = run.view()
    frame = run.figure(view, FIRST)
    boldALabel(frame).accept()
    path = QVizSaveSession(run.api, name='label').execute()
    with open(path) as handle:
        body = handle.read()

    assert '<TextStyle side="left"' in body and 'bold="1"' in body
    assert '<Style ' not in body, 'a label is not a trace'

    restored = run.freshApi()
    QVizRestoreSession(restored, path=path).execute()
    again = restored.figureframes[frame.figureKey]
    assert again.styleText().getAxis('left').labelStyle['font-weight'] == 'bold'
    # The palette is not a hand either: a session that styles a label writes no pen.
    assert styledIn(QVizSessionFile.read(path)) == []


@pytest.mark.ui
def test_a_window_nobody_touched_writes_no_style_at_all(run):
    """The palette is not a hand, and the file must not mistake it for one.

    Measured: an untouched figure of two traces writes **0** ``<Style>``, and the
    session that puts it back colours both traces again from the palette -- so a
    palette changed between the two runs is a palette the session follows, which is
    the whole reason the values are read at save time and the record on the frame
    holds only *which* traces were touched.
    """
    view = run.view()
    frame = run.figure(view, FIRST, SECOND)
    path = QVizSaveSession(run.api, name='untouched').execute()
    with open(path) as handle:
        body = handle.read()

    assert '<Style' not in body and '<TextStyle' not in body

    restored = run.freshApi()
    QVizRestoreSession(restored, path=path).execute()
    again = restored.figureframes[frame.figureKey]
    assert colours(again) == {FIRST: palette(0), SECOND: palette(1)}


@pytest.mark.ui
def test_the_style_is_written_under_the_quantity_that_drew_the_trace(run):
    """`<Style>` under its `<Quantity>`, ranked among the traces of *that* quantity."""
    view = run.view()
    frame = run.figure(view, FIRST, SECOND)
    colourATrace(frame, which=1).accept()

    written = QVizSessionFile.read(
        QVizSaveSession(run.api, name='under_quantity').execute())
    byPath = quantitiesOf(written, frame.figureKey)

    assert byPath[FIRST].styles == ()
    assert [style.trace for style in byPath[SECOND].styles] == [0]
    assert byPath[SECOND].styles[0].attributes['color'] == '#ff0000'


@pytest.mark.ui
@pytest.mark.parametrize('lost', [NO_TRACE, NOT_IN_THE_CASE])
def test_a_style_naming_no_trace_to_dress_is_named(run, caplog, lost):
    """A colour that cannot come back is said, not quietly dropped.

    The two halves of the refusal are the two ways a file can outlive what it was
    written for: the quantity is no longer in the case at all, or it is in the tree
    and the read answers nothing for it along the plotted axis. Neither may put the
    colour on the trace next to it -- and the rest of the figure is put back.
    """
    view = run.view()
    frame = run.figure(view, FIRST, SECOND)
    colourATrace(frame, which=1).accept()
    path = QVizSaveSession(run.api, name='refused').execute()
    with open(path) as handle:
        body = handle.read()
    with open(path, 'w') as handle:
        handle.write(body.replace('path="%s"' % SECOND, 'path="%s"' % lost))

    with caplog.at_level('WARNING'):
        restored = run.freshApi()
        QVizRestoreSession(restored, path=path).execute()

    assert lost in caplog.text
    assert 'not put back' in caplog.text or 'draws' in caplog.text
    again = restored.figureframes[frame.figureKey]
    assert [rgbOf(curve) for curve in again.curves()] == [palette(0)]


# ---------------------------------------------------------------- a table

@pytest.mark.ui
def test_a_table_puts_the_colour_back_on_the_panel_that_was_styled(run):
    """One panel coloured, its neighbours left to the palette.

    The panels of a table are filled from a configuration file the command writes,
    so this is the window where the node a panel holds and the node the gesture
    named are two different objects -- and the style still has to find its panel.
    """
    view = run.view()
    frame = run.table(view, FIRST, SECOND, THIRD)
    assert len(frame.panels()) == 3
    colourATrace(frame.panels()[1], rgb=OTHER).accept()
    path = QVizSaveSession(run.api, name='panels').execute()

    written = QVizSessionFile.read(path)
    byPath = quantitiesOf(written, frame.figureKey)
    assert [path for path, quantity in byPath.items() if quantity.styles] \
        == [SECOND], 'a panel coloured its neighbours in the file'

    restored = run.freshApi()
    QVizRestoreSession(restored, path=path).execute()
    again = restored.figureframes[frame.figureKey]
    assert isinstance(again, QVizTablePlot)
    drawn = dict((panel.treeNode.getPath(), rgbOf(panel.curves()[0]))
                 for panel in again.panels() if isinstance(panel, QVizPanel))
    assert drawn == {FIRST: palette(0), SECOND: OTHER, THIRD: palette(0)}


@pytest.mark.ui
def test_a_panels_label_is_written_under_its_quantity_not_under_the_figure(run):
    """A `<TextStyle>` under a `<Figure>` is the figure's own title and axes.

    A table has one plot per panel, so its labels belong to the quantity of the
    panel that drew them; written at figure level they would style a label of the
    window, which is not what the user bolded.
    """
    view = run.view()
    frame = run.table(view, FIRST, SECOND)
    boldALabel(frame.panels()[0], side='bottom').accept()
    path = QVizSaveSession(run.api, name='panel_label').execute()

    written = QVizSessionFile.read(path)
    figure = [figure for figure in written.figures
              if figure.key == frame.figureKey][0]
    assert figure.text == ()
    sides = dict((quantity.path, [style.side for style in quantity.text])
                 for quantity in figure.quantities)
    assert sides == {FIRST: ['bottom'], SECOND: []}

    restored = run.freshApi()
    QVizRestoreSession(restored, path=path).execute()
    again = restored.figureframes[frame.figureKey]
    styles = dict((panel.treeNode.getPath(),
                   panel.pgPlotWidget.getAxis('bottom').labelStyle)
                  for panel in again.panels())
    assert styles[FIRST].get('font-weight') == 'bold'
    assert 'font-weight' not in styles[SECOND]
