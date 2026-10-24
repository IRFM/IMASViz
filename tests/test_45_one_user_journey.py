# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""One user journey, end to end, on two real cases.

Every other test in this suite drives one gesture. That is how a defect hides in
the seams: measured while writing this file, a hand-built shot view (frame
constructed in the test, a bare ``Viz_API`` hung on it) passes each gesture
individually and still cannot draw the selection -- ``QVizPlotAsSlices`` takes
``all_DTV=True`` by default, so it asks the api for every opened view, finds an
empty ``DTVlist``, and answers ``ValueError: No signal selected.`` for a
selection of two that the view itself holds. Only the path the application takes
(``QVizOpenShotView`` -> ``Viz_API.CreateDataTree``, which appends the frame to
``DTVframeList`` and the view to ``DTVlist``) leaves the pieces wired the way a
click does. So the journey below opens its views that way and does not touch a
frame constructor.

What the steps answered on this machine before the file was written, in absolute
numbers (WEST 54924 run 0, data dictionary pinned at 3.35.0, harness dictionary
4.0.0):

* opening the case: 69 IDS roots, 0 signals -- the tree is a shadow until an
  occurrence is loaded;
* ``occurrencesOf('equilibrium')`` -> ``[0, 1, 2, 3]``, asked of the case, not of
  the data dictionary;
* loading occurrence 0 synchronously: 3368 signals, all 3368 of them leaves of
  ``equilibrium``, in 0.58 s for the walk;
* selecting three leaves leaves 3 entries; saving writes
  ``<name>.lsp`` under ``$HOME/.imasviz`` with one ``<Quantity path occurrence
  uri/>`` each;
* plotting those three draws **one** ``QVizCurvePlot`` (``SlicesPlot1``): the two
  scalars over time share it, and the third -- ``coordinate_system.r``, 2 axes to
  draw -- gets a picture frame that finds ``no values in the image`` and is
  dropped, so this case cannot exercise the picture branch;
* the same three plotted as a table: one ``QVizTablePlot`` (``TablePlotView:1``),
  which refuses that two-axis leaf with a message naming it;
* unselecting: 3 dropped, 0 left;
* WEST 55799 run 0 also answers ``[0, 1, 2, 3]`` for ``equilibrium``, and the
  ``.lsp`` written for 54924 selects 3 there: the file carries the uri it was
  written from and ``findNode`` matches ``getPath()`` plus the occurrence, which
  is the manual's "apply this selection to another database";
* 55799's ``hard_x_rays`` holds occurrence 0, 5687 signals and 38 leaves named
  ``hard_x_rays.channel[<n>].radiance.data``; selecting channel 0 and plotting
  gives one ``QVizImagePlot``, ``SlicesImage1``, ``isDrawing()`` True;
* removing the second view leaves 1 frame and 1 view.

The figures keep the keys the api handed out in the order the steps run, so the
file is one journey: its tests run in the order written, and each asserts on the
keys that appeared while it ran.
"""

import pytest

from imasviz.VizDataSource.QVizDBEntryRegistry import QVizDBEntryRegistry
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizConfigurations.QVizConfigurationFile import \
    SELECTION, QVizConfigurationFile
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSaveNodeSelection \
    import QVizSaveNodeSelection
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectFromConfiguration \
    import QVizSelectFromConfiguration
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectNodes \
    import QVizSelectNodes
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsSlices \
    import QVizPlotAsSlices
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsTable \
    import QVizPlotAsTable
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
    import QVizPlotOneNode
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlot import QVizTablePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.Viz_API import Viz_API

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      RANK3_CASE_DATA_DICTIONARY_VERSION, RANK3_CASE_URI,
                      case_uri_or_skip, rank3_case_uri_or_skip)

IDS_NAME = 'equilibrium'
CURVES = ('equilibrium.time',
          'equilibrium.time_slice[0].global_quantities.ip')
# Two axes to draw, so the command sends it to a picture frame -- and on this
# shot that frame finds nothing to picture.
UNPICTURED = 'equilibrium.time_slice[0].coordinate_system.r'
PICTURE_LEAF = 'hard_x_rays.channel[0].radiance.data'
PICTURE_PATH = 'hard_x_rays/channel(0)/radiance/data'

ROOTS = 69
EQUILIBRIUM_OCCURRENCES = [0, 1, 2, 3]
EQUILIBRIUM_LEAVES = 3368
PICTURE_IDS = 'hard_x_rays'
RADIANCE_SIGNALS = 5687

pytestmark = [pytest.mark.case, pytest.mark.ui, pytest.mark.dd]


class Journey:
    """The gestures of one application session, on one ``Viz_API``.

    ``openCase`` is the body of ``QVizOpenShotView.Open`` without the log panel:
    a source from the factory, the data dictionary the case was written with, and
    the api building the view so it registers the frame. The frames and the
    figures stay reachable through ``api.DTVframeList`` and ``api.figureframes``
    for the whole session, which is what keeps them alive in the application --
    and what keeps a shown frame from dying under a paint event here.
    """

    def __init__(self, api, home):
        self.api = api
        self.home = home

    def openCase(self, uri, ddVersion):
        source = QVizDataSourceFactory().create(uri)
        source.dd_version = ddVersion
        already = self.api.isDataSourceAlreadyOpened(source)
        view = (self.api.GetDTVFor(source.getKey()) if already
                else self.api.CreateDataTree(source).dataTreeView)
        self.api.ShowDataTree(view)
        return view, already

    def leaf(self, view, name):
        for node in view.signalsList:
            if node.getDataName() == name:
                return node
        raise AssertionError('"%s" is not a leaf of this tree (%d signals)'
                             % (name, len(view.signalsList)))

    def select(self, view, *names):
        """Select the named leaves from a clean slate, as clicks would."""
        QVizSelectNodes(view).unselectAll()
        select = QVizSelectNodes(view)
        answers = [select.selectNode(self.leaf(view, name), view)
                   for name in names]
        assert answers == [True] * len(names), answers

    def pathsInSelection(self, view):
        return sorted(entry['QTreeWidgetItem'].getPath()
                      for entry in view.selectedSignalsDict.values())

    def newFigures(self, before):
        return sorted(set(self.api.figureframes) - before)


@pytest.fixture(scope='module')
def journey(qapp, tmp_path_factory):
    """One session: a $HOME the journey may write into, and one api.

    The suite does not isolate ``$HOME``, so a saved selection would land in the
    real :file:`~/.imasviz`; the helpers read ``HOME`` when they are called, so
    setting it for the module is enough, and it is undone when the journey ends.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('journeyHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    try:
        yield Journey(Viz_API(), home)
    finally:
        patch.undo()


# --------------------------------------------------------------------------
# Opening the case
# --------------------------------------------------------------------------

def test_opening_a_case_hands_the_api_a_view_it_keeps_track_of(journey):
    view, opened = journey.openCase(CASE_URI, CASE_DATA_DICTIONARY_VERSION)

    assert opened is False
    assert journey.api.DTVlist == [view]
    assert len(journey.api.DTVframeList) == 1
    assert journey.api.DTVframeList[0].dataTreeView is view
    assert view.dataSource.uri == CASE_URI
    assert view.dataSource.dd_version == CASE_DATA_DICTIONARY_VERSION
    # The tree is a shadow until an occurrence is loaded: 55 roots, no leaf yet.
    assert len(view.IDSRoots) == ROOTS
    assert view.signalsList == []


def test_opening_the_same_case_again_gives_the_view_already_on_screen(journey):
    view, opened = journey.openCase(CASE_URI, CASE_DATA_DICTIONARY_VERSION)

    assert opened is True
    assert view is journey.api.DTVlist[0]
    assert len(journey.api.DTVframeList) == 1
    assert len(journey.api.DTVlist) == 1


def test_the_case_answers_which_occurrences_it_holds(journey):
    view = journey.api.DTVlist[0]

    assert view.occurrences.occurrencesOf(IDS_NAME) == EQUILIBRIUM_OCCURRENCES


def test_loading_an_occurrence_gives_the_shadow_tree_its_leaves(journey):
    view = journey.api.DTVlist[0]

    QVizLoadOccurrence(dataTreeView=view, idsName=IDS_NAME, occurrence=0,
                       asynch=False).execute()

    assert view.loadedOccurrences(IDS_NAME) == [0]
    assert view.loadsInProgress == set()
    assert view.dataSource.runningParsers == set()
    assert len(view.signalsList) == EQUILIBRIUM_LEAVES
    for name in CURVES + (UNPICTURED,):
        journey.leaf(view, name)


# --------------------------------------------------------------------------
# Selecting, saving, drawing
# --------------------------------------------------------------------------

def test_selecting_three_quantities_records_three(journey):
    view = journey.api.DTVlist[0]

    journey.select(view, *(CURVES + (UNPICTURED,)))

    assert len(view.selectedSignalsDict) == 3
    assert journey.pathsInSelection(view) == [
        'equilibrium/time',
        'equilibrium/time_slice(0)/coordinate_system/r',
        'equilibrium/time_slice(0)/global_quantities/ip']
    assert [entry['index'] for entry in view.selectedSignalsDict.values()] \
        == [0, 1, 2]


def test_saving_the_selection_writes_the_file_the_manual_describes(journey):
    view = journey.api.DTVlist[0]

    path = QVizSaveNodeSelection(view, name='journey').execute()

    assert path == str(journey.home / '.imasviz' / 'journey.lsp')
    configuration = QVizConfigurationFile.read(path)
    assert configuration.kind == SELECTION
    # Written in the order the three were clicked, not sorted: the file is a
    # recording of the gesture.
    assert [q.path for q in configuration.quantities] == [
        'equilibrium/time',
        'equilibrium/time_slice(0)/global_quantities/ip',
        'equilibrium/time_slice(0)/coordinate_system/r']
    assert sorted(q.path for q in configuration.quantities) \
        == journey.pathsInSelection(view)
    assert {q.occurrence for q in configuration.quantities} == {0}
    assert {q.uri for q in configuration.quantities} == {CASE_URI}


def test_plotting_the_selection_draws_one_curve_figure(journey, caplog):
    view = journey.api.DTVlist[0]
    before = set(journey.api.figureframes)

    frames = QVizPlotAsSlices(dataTreeView=view).execute()

    # The two scalars over time share one figure; the two-axis leaf gets a
    # picture frame of its own, which this shot leaves empty, so it is dropped
    # and named in the log of its view rather than left on screen as a blank.
    assert len(frames) == 1
    assert type(frames[0]) is QVizCurvePlot
    assert frames[0].isDrawing() is True
    assert journey.newFigures(before) == ['SlicesPlot1']
    assert QVizPlotAsSlices.IMAGE_FIGURE_TYPE not in journey.api.figureframes
    assert 'no values in the image' in caplog.text

    stored = journey.api.figToNodes['SlicesPlot1']
    assert sorted(node.getPath() for _, node in stored.values()) \
        == ['equilibrium/time', 'equilibrium/time_slice(0)/global_quantities/ip']


def test_the_same_selection_plotted_as_a_table_refuses_the_two_axis_leaf(journey,
                                                                         caplog):
    view = journey.api.DTVlist[0]
    before = set(journey.api.figureframes)

    frame = QVizPlotAsTable(dataTreeView=view).execute()

    assert type(frame) is QVizTablePlot
    assert journey.newFigures(before) == ['TablePlotView:1']
    assert 'coordinate_system.r' in caplog.text


def test_unselecting_empties_the_view(journey):
    view = journey.api.DTVlist[0]

    dropped = QVizSelectNodes(view).unselectAll()

    assert dropped == 3
    assert view.selectedSignalsDict == {}


# --------------------------------------------------------------------------
# The same journey in a second window, on another shot
# --------------------------------------------------------------------------

@pytest.fixture(scope='module')
def otherShot(journey):
    """A second window on another shot -- what the saved selection is for."""
    uri = rank3_case_uri_or_skip()
    if uri is None:
        pytest.skip('rank 3 case not reachable: %s' % RANK3_CASE_URI)
    view, opened = journey.openCase(uri, RANK3_CASE_DATA_DICTIONARY_VERSION)
    assert opened is False and len(journey.api.DTVlist) == 2
    return view


def test_the_selection_saved_from_one_shot_lands_in_another(journey, otherShot):
    path = str(journey.home / '.imasviz' / 'journey.lsp')
    saved = [q.path for q in QVizConfigurationFile.read(path).quantities]

    selected = QVizSelectFromConfiguration(otherShot, path).execute()

    # The file names the uri it was written from; the replay matches the paths
    # the target tree spells, which is how one shot's selection becomes another's.
    assert selected == 3
    assert journey.pathsInSelection(otherShot) == sorted(saved)
    # Applying a configuration loads the IDS it names when the view lacks it.
    assert otherShot.loadedOccurrences(IDS_NAME) == [0]


def test_a_replayed_quantity_is_plotted_from_the_second_view(journey, otherShot):
    before = set(journey.api.figureframes)
    node = otherShot.selectedSignalsDict[
        list(otherShot.selectedSignalsDict)[0]]['QTreeWidgetItem']

    figure = QVizPlotOneNode(dataTreeView=otherShot, treeNode=node).execute()

    assert type(figure) is QVizCurvePlot
    assert figure.isDrawing() is True
    assert journey.newFigures(before) == ['SlicesPlot2']


def test_the_picture_branch_needs_a_shot_that_holds_values(journey, otherShot):
    before = set(journey.api.figureframes)
    signals = len(otherShot.signalsList)

    # The user double clicks the IDS in the second window's tree: the picture
    # branch needs a shot that holds values, and 55799's hard_x_rays does.
    QVizLoadOccurrence(dataTreeView=otherShot, idsName=PICTURE_IDS,
                       occurrence=0, asynch=False).execute()
    assert len(otherShot.signalsList) - signals == RADIANCE_SIGNALS

    journey.select(otherShot, PICTURE_LEAF)
    frames = QVizPlotAsSlices(dataTreeView=otherShot).execute()

    assert len(frames) == 1
    assert type(frames[0]) is QVizImagePlot
    assert frames[0].isDrawing() is True
    assert journey.newFigures(before) == ['SlicesImage1']
    assert journey.api.figToNodes['SlicesImage1'][
        otherShot.dataSource.dataKey(
            journey.leaf(otherShot, PICTURE_LEAF))][1].getPath() == PICTURE_PATH


def test_closing_a_view_forgets_the_case_it_was_the_last_to_show(journey,
                                                                 otherShot):
    frame = [opened for opened in journey.api.DTVframeList
             if opened.dataTreeView is otherShot][0]
    kept = journey.api.DTVlist[0].dataSource
    keptBefore = QVizDBEntryRegistry.count(kept.uri, kept.MODE, kept.dd_version)

    journey.api.RemoveDTVFrame(frame)

    assert len(journey.api.DTVframeList) == 1
    assert journey.api.DTVlist == [journey.api.DTVlist[0]]
    # The view was the last one showing 55799 in this session, so its record is
    # gone: entry closed, IDS instances dropped. drop() removes the whole record,
    # which also forgets any reference another file of the suite held on that
    # same case -- the registry is one dict for the process.
    removed = otherShot.dataSource
    assert QVizDBEntryRegistry.count(removed.uri, removed.MODE,
                                     removed.dd_version) == 0
    assert QVizDBEntryRegistry.entry(removed.uri, removed.MODE,
                                     removed.dd_version) is None
    assert QVizDBEntryRegistry.ids_cache(removed.uri, removed.MODE,
                                         removed.dd_version) == {}
    # 54924 is still on screen, so closing this window leaves its record alone.
    # How many references it holds is not pinned: other files of the suite open
    # the same case in the same process, and in a full run this case arrived at
    # 12 of them -- measured here by pinning the number and reading what the
    # answer was.
    assert QVizDBEntryRegistry.count(kept.uri, kept.MODE, kept.dd_version) \
        == keptBefore
    assert keptBefore >= 1
