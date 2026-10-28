# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A session written from a real case, put back after the case was closed.

``test_66`` pins the format. This file pins the promise: close IMASViz, open it
again, ask for the session, and the windows are the ones that were there -- the
case, the occurrence that had been loaded and the way it was asked for, the
selection, the figures and the keys those windows answer to in the Show/Hide and
Delete menus.

Everything here goes through the gestures, never through a frame constructor: the
case is opened as ``QVizOpenShotView.Open`` opens it, the occurrence through
``QVizLoadOccurrence``, the quantities through ``QVizPlotOneNode`` and
``QVizPlotAsTable``, and the session back through ``QVizRestoreSession``. A frame
built by hand passes each gesture in isolation and then cannot draw a selection
(``test_45`` measures why), and a session put back through a constructor would
test something the application never does.

The restore reads the case through a **second** ``Viz_API``, because that is the
session the user comes back to: the first one is what is torn down when the
window closes. What that costs on the reference case (WEST 54924 run 0, pinned at
data dictionary 3.35.0), measured while writing this file:

* the walk of ``equilibrium`` occurrence 0, asked for the first slice only:
  **3368** signals, **0,10 s** and **+7,7 Mo** -- against **3,99 s** and
  **+122,8 Mo** when the same IDS is read whole. The tree is identical either
  way: 7203 elements, 7030 leaves;
* the IDS instances the reopened view holds are the lazy ones, so a session of
  three loaded IDS costs **+3,8 Mo** where reading them whole cost **+246,8 Mo**;
* an unreachable case costs that case's windows alone: the reason names the file
  and the URI, and the other cases of the file are still put back.
"""

import os

import pytest
from PySide6.QtWidgets import QMdiArea

from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizConfigurations.QVizSessionFile import (
    QVizSessionFile, QVizSessionLoad, QVizSessionSelection)
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence import \
    QVizLoadOccurrence
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectNodes import \
    QVizSelectNodes
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsTable import \
    QVizPlotAsTable
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode import \
    QVizPlotOneNode
from imasviz.VizGUI.VizGUICommands.VizSession.QVizRestoreSession import \
    QVizRestoreSession
from imasviz.VizGUI.VizGUICommands.VizSession.QVizSaveSession import \
    QVizSaveSession
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlot import QVizTablePlot
from imasviz.Viz_API import Viz_API

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip)

IDS_NAME = 'equilibrium'
CURVES = ('equilibrium.time',
          'equilibrium.time_slice[0].global_quantities.ip')
CURVE_PATHS = ['equilibrium/time',
               'equilibrium/time_slice(0)/global_quantities/ip']

EQUILIBRIUM_SIGNALS = 3368
# How many elements the dynamic array of this occurrence holds, while the walk of
# a session keeps the one slice its file names.
EQUILIBRIUM_SLICES = 49

pytestmark = [pytest.mark.case, pytest.mark.ui, pytest.mark.dd]


class Session:
    """The gestures of one IMASViz run, on one ``Viz_API``.

    ``openCase`` is the body of ``QVizOpenShotView.Open``: a source from the
    factory and the api building the view, so the frame is registered and the
    figures the commands draw have a session to be drawn into. The frames stay
    reachable through ``api.figureframes`` for the whole run, which is what keeps
    them alive -- in the application and here.

    The api is built on a ``QMdiArea``, as the application builds it on its
    central area. Without one, ``addPlotWidgetToMDI`` has nowhere to hand the
    subwindow it creates: it keeps the last one on itself and the earlier
    windows lose their Qt owner, which is measured here as a restored figure
    whose C++ object is gone before anyone looks at its axis.
    """

    def __init__(self, mdi, home):
        self.mdi = mdi
        self.home = home
        self.api = Viz_API(parent=mdi)
        self.others = []

    def freshApi(self):
        """An api that never saw the windows being put back: another run."""
        api = Viz_API(parent=self.mdi)
        self.others.append(api)
        return api

    def openCase(self, uri, ddVersion=None):
        source = QVizDataSourceFactory().create(uri)
        if ddVersion:
            source.dd_version = ddVersion
        already = self.api.isDataSourceAlreadyOpened(source)
        view = (self.api.GetDTVFor(source.getKey()) if already
                else self.api.CreateDataTree(source).dataTreeView)
        self.api.ShowDataTree(view)
        return view

    def leaf(self, view, name):
        for node in view.signalsList:
            if node.getDataName() == name:
                return node
        raise AssertionError('"%s" is not a leaf of this tree (%d signals)'
                             % (name, len(view.signalsList)))

    def select(self, view, *names):
        QVizSelectNodes(view).unselectAll()
        selector = QVizSelectNodes(view)
        for name in names:
            selector.selectNode(self.leaf(view, name), view)

    def pathsInSelection(self, view):
        return [entry['QTreeWidgetItem'].getPath()
                for entry in view.selectedSignalsDict.values()]

    def sessionPath(self):
        return QVizSessionFile.named('journey')


@pytest.fixture(scope='module')
def session(qapp, tmp_path_factory):
    """One run: a $HOME it may write into, and one api on a central area."""
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('sessionHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    # The area is held by the Session the fixture keeps: an owner dropped with a
    # helper takes its subwindows with it, and the crash shows up in a test
    # several away from the one that dropped it.
    run = Session(QMdiArea(), home)
    try:
        yield run
    finally:
        run.mdi = None
        run.others = []
        patch.undo()


# --------------------------------------------------------------------------
# Writing the session of a run that drew two windows.

def test_a_run_that_loaded_and_drew_is_a_session_that_fits_in_one_file(session):
    view = session.openCase(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    QVizLoadOccurrence(dataTreeView=view, idsName=IDS_NAME, occurrence=0,
                       asynch=False).execute()
    assert len(view.signalsList) == EQUILIBRIUM_SIGNALS

    session.select(view, *CURVES)
    curve = QVizPlotOneNode(view, session.leaf(view, CURVES[0])).execute()
    QVizPlotOneNode(view, session.leaf(view, CURVES[1]),
                    intoFigureKey=curve.figureKey).execute()
    table = QVizPlotAsTable(view, plotAxis='TIME').execute()
    assert isinstance(curve, QVizCurvePlot) and isinstance(table, QVizTablePlot)
    # What the window was drawn along, kept to compare the restored one with it.
    session.curveLabel = curve.pgPlotWidget.getAxis('bottom').labelText
    session.curvePoints = curve.curveCount()

    path = QVizSaveSession(session.api, name='journey').execute()
    saved = QVizSessionFile.read(path)

    assert [case.uri for case in saved.cases] == [CASE_URI]
    assert saved.cases[0].dd_version == CASE_DATA_DICTIONARY_VERSION
    assert saved.cases[0].loads == [QVizSessionLoad(IDS_NAME, 0, 'first')]
    assert [figure.key for figure in saved.figures] \
        == ['SlicesPlot1', 'TablePlotView:1']
    assert [figure.kind for figure in saved.figures] == ['curve', 'table']
    assert [quantity.path for quantity in saved.figures[0].quantities] \
        == CURVE_PATHS
    assert [selection.path for selection in saved.cases[0].selection] \
        == CURVE_PATHS


def test_the_session_says_which_time_slices_the_view_was_showing(session):
    """The choice only ever reached the label of the occurrence node before."""
    saved = QVizSessionFile.read(session.sessionPath())

    assert [load.slices for load in saved.cases[0].loads] == ['first']
    view = session.api.GetDTVFor(QVizDataSourceFactory().create(
        CASE_URI).getKey())
    assert view.sliceSelectionFor(IDS_NAME, 0).viewLabel() \
        == 'displaying first time slice'


# --------------------------------------------------------------------------
# Putting it back, in a session that never saw those windows.

def test_putting_the_session_back_reopens_the_case_and_the_windows(session,
                                                                   caplog):
    """The point of the file: the same windows, under the same keys."""
    # The run is over: its shot view goes the way closing its window takes it,
    # and the case record goes with it (`forget_case`).
    for frame in list(session.api.GetDTVFrames()):
        session.api.RemoveDTVFrame(frame)

    reopened = session.reopened = session.freshApi()
    views = QVizRestoreSession(reopened, name='journey').execute()

    assert list(views) == [CASE_URI]
    view = views[CASE_URI]
    assert len(view.signalsList) == EQUILIBRIUM_SIGNALS
    assert view.loadedOccurrences(IDS_NAME) == [0]
    assert sorted(session.pathsInSelection(view)) == sorted(CURVE_PATHS)

    figures = reopened.figureframes
    assert sorted(figures) == ['SlicesPlot1', 'TablePlotView:1']
    assert isinstance(figures['SlicesPlot1'], QVizCurvePlot)
    assert isinstance(figures['TablePlotView:1'], QVizTablePlot)
    assert figures['SlicesPlot1'].curveCount() == 2


def test_the_windows_that_come_back_are_drawn_from_the_data(session):
    """A restored window is a frame of the application, not a picture of one."""
    figures = session.reopened.figureframes

    curve = figures['SlicesPlot1']
    assert curve.isDrawing()
    # The abscissa is settled by the first quantity drawn into a curve figure, so
    # replaying that quantity settles the same one: what is compared here is the
    # window the file describes against the window it was written from.
    assert curve.pgPlotWidget.getAxis('bottom').labelText == session.curveLabel
    assert curve.curveCount() == session.curvePoints == 2
    table = figures['TablePlotView:1']
    assert table.panelCount() == 2
    assert table.getPlotAxis() == 'TIME'


def test_the_idss_a_restored_view_holds_are_read_lazy(session):
    """The walk of a session is lazy, and that is what makes it cheap.

    Measured on this case: 0,10 s and +7,7 Mo for the walk of `equilibrium`
    occurrence 0, against 3,99 s and +122,8 Mo read whole, the tree identical
    either way (7203 elements, 7030 leaves). A handle stays readable only while
    the case is held open, which is what the view does for as long as it lives.
    """
    view = session.reopened.DTVlist[0]
    ids = view.loadedIds(IDS_NAME)

    assert ids is not None
    assert getattr(ids, '_lazy', False) is True
    # Nothing was read for this: the handle answers for the whole array only when
    # it is asked -- 49 slices for this occurrence -- while the walk of the view
    # kept the one the session file named.
    assert len(ids.time_slice) == EQUILIBRIUM_SLICES
    assert {node.getPath().split('/')[1] for node in view.signalsList
            if node.getPath().startswith('equilibrium/time_slice')} \
        == {'time_slice(0)'}


# --------------------------------------------------------------------------
# What a session does when part of it cannot come back.

def test_a_case_that_cannot_be_reached_costs_its_own_windows_and_says_why(session,
                                                                          caplog):
    """A session usually holds more than one shot."""
    path = os.path.join(str(session.home), '.imasviz', 'unreachable.vsess')
    with open(path, 'w') as handle:
        handle.write(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<IMASVizSession version="1">\n'
            '  <Case uri="imas:hdf5?path=/no/such/case/0" dd_version="3.35.0"/>'
            '  <Figure key="SlicesPlot1" kind="curve">\n'
            '    <Quantity path="equilibrium/time" occurrence="0" '
            'uri="imas:hdf5?path=/no/such/case/0"/>\n'
            '  </Figure>\n'
            '</IMASVizSession>\n')

    views = QVizRestoreSession(session.freshApi(), path=path).execute()

    assert views == {'imas:hdf5?path=/no/such/case/0': None}
    assert '/no/such/case/0' in caplog.text
    assert 'unreachable.vsess' in caplog.text


def test_a_quantity_the_reopened_tree_does_not_hold_is_named_and_the_rest_comes_back(
        session, caplog):
    """A session written against another data dictionary can name a node that
    is not there; that quantity is named, the rest of its window is drawn."""
    saved = QVizSessionFile.read(session.sessionPath())
    saved.cases[0].selection.append(
        QVizSessionSelection('equilibrium/time_slice(0)/gone/quantity', 0))
    path = saved.write(os.path.join(str(session.home), '.imasviz',
                                    'missing.vsess'))

    views = QVizRestoreSession(session.freshApi(), path=path).execute()
    view = views[CASE_URI]

    assert 'equilibrium/time_slice(0)/gone/quantity' in caplog.text
    assert sorted(session.pathsInSelection(view)) == sorted(CURVE_PATHS)
