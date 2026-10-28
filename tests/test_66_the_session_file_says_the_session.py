# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What a session file says, and what the application puts into it.

Nothing in IMASViz remembers a session today: closing the window drops the cases,
the occurrences that were loaded, the selection and every figure that was drawn.
The manual keeps two files for coming back -- a node selection (``.lsp``) and a
plot configuration (``.pcfg``) -- and neither says which windows were open
together, under which keys, with which occurrences loaded.

This file pins the format and the writer; ``test_67`` puts a session back on a
real case. What the format refuses, and how, is what makes it safe to keep a file
over a release: every refusal below names the file, because a session that
silently describes less than it says is worse than one that is not read at all --
the configuration reader measured before this format existed answered "no
quantities" for a file whose extension it did not recognise, without a word.

The stand-ins are the ones the plot tests already use: a leaf answering the axes
model and the tree questions, and a shot view answering the selection record. The
figures are not stand-ins -- they are the frames the commands build, registered
in the api's bookkeeping, because that bookkeeping is exactly what the session
writer reads, and a stand-in for it would test the writer against a state the
application never holds.
"""

import os
import xml.etree.ElementTree as ET

import pytest
from PySide6.QtWidgets import QMdiArea, QMenu, QWidget

from imasviz.VizGUI.VizConfigurations.QVizConfigurationFile import \
    QVizConfigurationFile
from imasviz.VizGUI.VizConfigurations.QVizSessionFile import (
    QVizSessionFile, QVizSessionCase, QVizSessionLoad, QVizSessionExpanded,
    QVizSessionSelection, QVizSessionFigure, QVizSessionQuantity,
    CURVE, IMAGE, TABLE, STACKED)
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectNodes import \
    QVizSelectNodes
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizMainMenuController \
    import QVizMainMenuController
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsTable import \
    QVizPlotAsTable
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsStacked import \
    QVizPlotAsStacked
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode import \
    QVizPlotOneNode
from imasviz.VizGUI.VizGUICommands.VizSession.QVizSaveSession import \
    QVizSaveSession
from imasviz.VizDataAccess.VizTimeSlices import ALL_SLICES, ONE_IN_TEN, \
    FIRST_SLICE, atIndex
from imasviz.Viz_API import Viz_API

from support.fakes import FakeAxesNode
from support import ownership

TIMES = [0., 1., 2., 3., 4.]
RHO = [0., 1., 2., 3.]
URI = 'imas:hdf5?case=1'


@pytest.fixture(autouse=True)
def configurationFolder(tmp_path, monkeypatch):
    """Keep the session inside the test, and out of the real ~/.imasviz."""
    monkeypatch.setenv('HOME', str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# The stand-ins: a leaf, a source, a shot view.

def _ids():
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = list(TIMES)
    ids.rho_tor = list(RHO)
    ids.time_slice = []
    for timeIndex in range(len(TIMES)):
        timeSlice = type(str('TimeSlice'), (), {})()
        timeSlice.time = TIMES[timeIndex]
        timeSlice.vector = [100. * timeIndex + 10. * i for i in range(len(RHO))]
        ids.time_slice.append(timeSlice)
    return ids


class Node(FakeAxesNode):
    """A leaf answering what the tree and the selection ask it."""

    def is0DAndDynamic(self):
        return self._dataType == 'FLT_0D'

    def is1DAndDynamic(self):
        return self._dataType == 'FLT_1D'

    def hasTimeAxis(self):
        return True

    def getPath(self):
        return self.getInfoDict().get('Path')

    def getOccurrence(self):
        return self.getInfoDict().get('occurrence')

    def parent(self):
        return None

    def setStyleWhenSelected(self):
        pass

    def setStyleWhenContainingData(self):
        pass


def leaf(name='vector', path='foo/time_slice(i)/vector', occurrence=0):
    return Node(_ids(), 'foo', 'foo.time_slice[itime]', 'FLT_1D', name=name,
                units='K', itimeIndex=0, coordinates=('rho_tor',),
                coordinateUnits={1: 'm'}, indices={'i': '1'},
                lengths={'i': str(len(TIMES))},
                infoDict={'Path': path, 'occurrence': occurrence, 'name': name})


class FakeBranch:
    """An IDS root or an occurrence node, answering whether it is unfolded."""

    def __init__(self, unfolded=False):
        self.unfolded = unfolded

    def isExpanded(self):
        return self.unfolded


class FakeSource:
    name = 'NATIVE'
    uri = URI
    dd_version = '3.35.0'

    def getKey(self):
        return 'URI:' + self.uri

    def dataKey(self, treeNode):
        return self.uri + '::' + treeNode.getPath()


class FakeView:
    """One shot view: the case it reads, the loads it shows, the selection it holds."""

    def __init__(self, uri=URI):
        self.uri = uri
        self.dataSource = FakeSource()
        self.selectedItem = None
        self.selectedSignalsDict = {}
        self.signalsList = []
        self.IDSRoots = {'foo': FakeBranch(unfolded=True),
                         'bar': FakeBranch()}
        self.ids_roots_occurrence = {'foo/0': FakeBranch(),
                                     'foo/1': FakeBranch(unfolded=True)}
        self.sliceSelections = {'foo/0': ALL_SLICES, 'foo/1': atIndex(7)}
        self.loaded = {'foo': [0, 1], 'bar': []}

    def loadedOccurrences(self, idsName):
        return self.loaded.get(idsName, [])

    def sliceSelectionFor(self, idsName, occurrence):
        return self.sliceSelections.get(idsName + '/' + str(occurrence),
                                        FIRST_SLICE)

    def parent(self):
        return None


def aSession(*views):
    """An api holding those views, as `CreateDataTree` would."""
    api = Viz_API()
    api.DTVlist = list(views)
    for view in views:
        view.imas_viz_api = api
    return api


# ---------------------------------------------------------------------------
# A session written by this release.

def aSessionFile():
    return QVizSessionFile(
        cases=[QVizSessionCase(
            uri=URI, dd_version='3.35.0', label='west 54924.0',
            loads=[QVizSessionLoad('equilibrium', 0, 'first'),
                   QVizSessionLoad('magnetics', 0, 'all'),
                   QVizSessionLoad('core_profiles', 1, 'index=7')],
            expanded=[QVizSessionExpanded('equilibrium', None),
                      QVizSessionExpanded('equilibrium', 0)],
            selection=[QVizSessionSelection('magnetics/flux_loop(3)/flux/data',
                                            0)]),
            QVizSessionCase(uri='imas:hdf5?case=2', dd_version=None,
                            label=None, loads=[], expanded=[], selection=[])],
        figures=[QVizSessionFigure('SlicesPlot1', CURVE,
                                   [QVizSessionQuantity(
                                       'magnetics/flux_loop(3)/flux/data', 0,
                                       URI, None, None),
                                    QVizSessionQuantity('magnetics/bpol(0)/x', 0,
                                                        'imas:hdf5?case=2',
                                                        None, None)],
                                   axis=None, tensor=False),
                 QVizSessionFigure('TablePlotView:1', TABLE,
                                   [QVizSessionQuantity('a/b', 0, URI, 0, 1),
                                    QVizSessionQuantity('c/d', 0, URI, 1, 1)],
                                   axis='TIME', tensor=False),
                 QVizSessionFigure('SlicesImage1', IMAGE,
                                   [QVizSessionQuantity('e/f', 0, URI, None,
                                                        None)],
                                   axis=None, tensor=True)])


@pytest.mark.ui
def test_a_session_comes_back_as_the_session_it_was_written():
    written = aSessionFile().write(QVizSessionFile.named('weekend'))
    read = QVizSessionFile.read(written)

    assert [(case.uri, case.dd_version, case.label) for case in read.cases] \
        == [(URI, '3.35.0', 'west 54924.0'), ('imas:hdf5?case=2', None, None)]
    assert read.cases[0].loads == [
        QVizSessionLoad('equilibrium', 0, 'first'),
        QVizSessionLoad('magnetics', 0, 'all'),
        QVizSessionLoad('core_profiles', 1, 'index=7')]
    assert read.cases[0].expanded == [QVizSessionExpanded('equilibrium', None),
                                      QVizSessionExpanded('equilibrium', 0)]
    assert read.cases[0].selection == [
        QVizSessionSelection('magnetics/flux_loop(3)/flux/data', 0)]
    assert [figure.key for figure in read.figures] \
        == ['SlicesPlot1', 'TablePlotView:1', 'SlicesImage1']
    assert [figure.kind for figure in read.figures] == [CURVE, TABLE, IMAGE]
    assert read.figures[1].axis == 'TIME'
    assert read.figures[2].tensor is True
    assert read.figures[0].tensor is False


@pytest.mark.ui
def test_a_figure_belongs_to_the_session_and_its_quantities_name_their_case():
    """A curve figure can hold quantities read from two shot views.

    That is what *Plot the selection in a figure* with *all databases* does, so a
    `<Figure>` nested inside a `<Case>` could not describe it.
    """
    written = aSessionFile().write(QVizSessionFile.named('two_shots'))
    root = ET.parse(written).getroot()

    assert [element.tag for element in root] \
        == ['Case', 'Case', 'Figure', 'Figure', 'Figure']
    assert [quantity.uri for quantity in aSessionFile().figures[0].quantities] \
        == [URI, 'imas:hdf5?case=2']


@pytest.mark.ui
def test_a_place_in_the_table_is_written_only_when_there_is_one():
    """`str(None)` used to be written for an absent place, and the reader then
    answered `invalid literal for int() with base 10: 'None'`."""
    path = aSessionFile().write(QVizSessionFile.named('places'))
    body = open(path).read()
    read = QVizSessionFile.read(path)

    assert 'row="0"' in body and 'column="1"' in body
    assert 'None' not in body
    assert [(q.row, q.column) for q in read.figures[0].quantities] \
        == [(None, None), (None, None)]
    assert [(q.row, q.column) for q in read.figures[1].quantities] \
        == [(0, 1), (1, 1)]


@pytest.mark.ui
def test_a_half_place_is_refused_and_says_which_half_is_missing():
    path = _write('half.vsess', """
    <IMASVizSession version="1">
      <Figure key="TablePlotView:1" kind="table">
        <Quantity path="a/b" occurrence="0" row="1"/>
      </Figure>
    </IMASVizSession>""")

    with pytest.raises(ValueError) as raised:
        QVizSessionFile.read(path)

    assert 'half a place' in str(raised.value) and 'column' in str(raised.value)
    assert path in str(raised.value)


# ---------------------------------------------------------------------------
# What the format refuses, and how it says it.

@pytest.mark.ui
def test_a_file_of_another_root_is_refused_naming_that_root():
    path = _write('other.vsess', '<PulseFile><shot>54924</shot></PulseFile>')

    with pytest.raises(ValueError) as raised:
        QVizSessionFile.read(path)

    assert '<PulseFile>' in str(raised.value) and '<IMASVizSession>' \
        in str(raised.value)


@pytest.mark.ui
def test_a_file_of_another_version_is_refused_naming_both_versions():
    """Guessing a format this module does not know is how a session comes back
    describing less than it says."""
    path = _write('future.vsess', '<IMASVizSession version="2"><Case uri="x"/>'
                                  '</IMASVizSession>')

    with pytest.raises(ValueError) as raised:
        QVizSessionFile.read(path)

    assert '"2"' in str(raised.value) and 'writes version 1' \
        in str(raised.value)


@pytest.mark.ui
def test_a_file_that_is_not_well_formed_xml_answers_with_a_reason():
    path = _write('broken.vsess', '<?xml version="1.0"?><IMASVizSession')

    with pytest.raises(ValueError) as raised:
        QVizSessionFile.read(path)

    assert 'well-formed' in str(raised.value)


@pytest.mark.ui
def test_a_missing_file_answers_with_a_reason():
    with pytest.raises(ValueError) as raised:
        QVizSessionFile.read('/no/such/session.vsess')

    assert 'Cannot read' in str(raised.value)


@pytest.mark.ui
def test_a_slice_choice_outside_the_four_names_the_words_that_are_accepted():
    path = _write('slices.vsess', """
    <IMASVizSession version="1">
      <Case uri="imas:hdf5?case=1">
        <Load ids="equilibrium" occurrence="0" slices="all time slices"/>
      </Case>
    </IMASVizSession>""")

    with pytest.raises(ValueError) as raised:
        QVizSessionFile.read(path)

    assert 'all / one_in_ten / first' in str(raised.value)


@pytest.mark.ui
def test_a_time_slice_index_is_read_as_a_number_and_not_as_a_word():
    path = _write('index.vsess', """
    <IMASVizSession version="1">
      <Case uri="imas:hdf5?case=1">
        <Load ids="equilibrium" occurrence="0" slices="index=7"/>
      </Case>
    </IMASVizSession>""")

    assert QVizSessionFile.read(path).cases[0].loads[0].slices == 'index=7'


@pytest.mark.ui
def test_a_slice_index_that_is_not_a_number_is_refused_with_what_the_file_said():
    path = _write('bad_index.vsess', """
    <IMASVizSession version="1">
      <Case uri="imas:hdf5?case=1">
        <Load ids="equilibrium" occurrence="0" slices="index=seven"/>
      </Case>
    </IMASVizSession>""")

    with pytest.raises(ValueError) as raised:
        QVizSessionFile.read(path)

    assert 'index=seven' in str(raised.value)


@pytest.mark.ui
def test_an_element_this_format_does_not_know_is_refused_by_name():
    """A misspelled `<Selections>` used to read as "no selection at all"."""
    path = _write('typo.vsess', """
    <IMASVizSession version="1">
      <Case uri="imas:hdf5?case=1">
        <Selections path="a/b" occurrence="0"/>
      </Case>
    </IMASVizSession>""")

    with pytest.raises(ValueError) as raised:
        QVizSessionFile.read(path)

    assert '<Selections>' in str(raised.value)


@pytest.mark.ui
def test_a_window_of_a_kind_this_application_does_not_draw_is_refused_by_name():
    path = _write('kind.vsess', """
    <IMASVizSession version="1">
      <Figure key="PlotView:1" kind="profiles">
        <Quantity path="a/b" occurrence="0"/>
      </Figure>
    </IMASVizSession>""")

    with pytest.raises(ValueError) as raised:
        QVizSessionFile.read(path)

    assert 'profiles' in str(raised.value)


@pytest.mark.ui
def test_a_element_missing_what_it_cannot_be_replayed_without_is_named():
    path = _write('keyless.vsess', """
    <IMASVizSession version="1">
      <Figure kind="curve">
        <Quantity path="a/b" occurrence="0"/>
      </Figure>
    </IMASVizSession>""")

    with pytest.raises(ValueError) as raised:
        QVizSessionFile.read(path)

    assert 'no key' in str(raised.value)


# ---------------------------------------------------------------------------
# The folder, shared with the configurations.

@pytest.mark.ui
def test_a_session_is_named_like_a_configuration_and_kept_in_the_same_folder():
    assert os.path.basename(QVizSessionFile.named('weekend')) == 'weekend.vsess'
    assert os.path.basename(QVizSessionFile.named('weekend.vsess')) \
        == 'weekend.vsess'
    assert os.path.dirname(QVizSessionFile.named('weekend')) \
        == QVizConfigurationFile.directory()


@pytest.mark.ui
def test_a_name_that_names_a_place_rather_than_a_session_is_refused():
    for typed in ('../outside', 'a/b', '', '.'):
        with pytest.raises(ValueError):
            QVizSessionFile.named(typed)

    assert QVizSessionFile.listing() == []


@pytest.mark.ui
def test_the_folder_lists_the_sessions_and_nothing_else():
    for name in ('one.vsess', 'two.pcfg', 'three.notvsess'):
        _write(name, '<IMASVizSession version="1"/>')

    assert QVizSessionFile.listing() == ['one.vsess']


# ---------------------------------------------------------------------------
# What the writer reads out of the application as it stands.

@pytest.mark.ui
def test_the_session_says_how_each_loaded_occurrence_was_asked_for():
    """The slice choice only ever reached the label of the occurrence node.

    Four words are written, and one of them carries the index: `index=7` is the
    fourth choice of the manual, and the two singleton choices are not
    distinguishable by anything but the object itself.
    """
    api = aSession(FakeView())

    figures = QVizSaveSession(api, path=_path('loads.vsess'))
    session = QVizSessionFile.read(figures.execute())

    assert session.cases[0].loads == [QVizSessionLoad('foo', 0, 'all'),
                                      QVizSessionLoad('foo', 1, 'index=7')]


@pytest.mark.ui
def test_an_occurrence_asked_for_the_default_comes_out_as_the_first_slice():
    view = FakeView()
    view.sliceSelections = {}
    api = aSession(view)

    session = QVizSessionFile.read(
        QVizSaveSession(api, path=_path('default.vsess')).execute())

    assert [load.slices for load in session.cases[0].loads] == ['first',
                                                                'first']


@pytest.mark.ui
def test_the_session_records_which_branches_were_open_and_tells_them_apart():
    """`<Expanded ids="foo"/>` is the IDS branch; with an occurrence, the node
    under it. Defaulting one to the other would unfold the wrong level."""
    api = aSession(FakeView())

    session = QVizSessionFile.read(
        QVizSaveSession(api, path=_path('unfolded.vsess')).execute())

    assert session.cases[0].expanded == [QVizSessionExpanded('foo', None),
                                         QVizSessionExpanded('foo', 1)]


@pytest.mark.ui
def test_the_selection_is_written_in_the_order_it_was_picked(qapp):
    view = FakeView()
    api = aSession(view)
    first, second = leaf('a', 'foo/a'), leaf('b', 'foo/b')
    view.signalsList = [first, second]
    QVizSelectNodes(view).selectNode(second)
    QVizSelectNodes(view).selectNode(first)

    session = QVizSessionFile.read(
        QVizSaveSession(api, path=_path('picked.vsess')).execute())

    assert [selection.path for selection in session.cases[0].selection] \
        == ['foo/b', 'foo/a']


@pytest.mark.ui
def test_a_saved_figure_keeps_the_key_the_api_handed_it(qapp):
    """A key is not a label: the Show/Hide and Delete menus address a window by
    it, so a file that renumbered its windows would stop describing the screen."""
    view = FakeView()
    api = aSession(view)
    view.signalsList = [leaf()]
    frame = QVizPlotOneNode(view, view.signalsList[0]).execute()
    assert frame is not None

    session = QVizSessionFile.read(
        QVizSaveSession(api, path=_path('keys.vsess')).execute())

    assert [figure.key for figure in session.figures] == ['SlicesPlot1']
    assert [quantity.path for quantity in session.figures[0].quantities] \
        == ['foo/time_slice(i)/vector']
    assert session.figures[0].kind == CURVE


@pytest.mark.ui
def test_a_table_writes_the_cell_each_panel_sits_in(qapp):
    """Read from the layout, the same reading a plot configuration uses."""
    view = FakeView()
    api = aSession(view)
    first = leaf('vector', 'foo/time_slice(i)/vector')
    second = leaf('theta_vector', 'foo/time_slice(i)/theta_vector')
    view.signalsList = [first, second]
    QVizSelectNodes(view).selectNode(first)
    QVizSelectNodes(view).selectNode(second)
    frame = QVizPlotAsTable(view, plotAxis='TIME').execute()
    assert frame is not None

    session = QVizSessionFile.read(
        QVizSaveSession(api, path=_path('cells.vsess')).execute())

    figure = session.figures[0]
    assert figure.kind == TABLE
    assert figure.axis == 'TIME'
    assert [(q.path, q.row, q.column) for q in figure.quantities] \
        == [(panel.treeNode.getPath(), row, column)
            for row, column, panel in frame.panelsInTable()]


@pytest.mark.ui
def test_a_window_drawn_by_a_plugin_is_left_out_and_named_by_its_key(qapp,
                                                                     caplog):
    """The Profiles window is drawn from a question the plugin asks; recording it
    would promise a window the restore has no gesture to replay."""
    view = FakeView()
    api = aSession(view)
    api.figureframes['PlotView:1'] = type(str('StubPluginWindow'), (), {})()

    session = QVizSessionFile.read(
        QVizSaveSession(api, path=_path('plugin.vsess')).execute())

    assert session.figures == []
    assert 'PlotView:1' in caplog.text


@pytest.mark.ui
def test_a_figure_key_already_held_by_a_live_window_is_refused_in_the_log(qapp,
                                                                          caplog):
    """Two frames under one key make one of them unreachable.

    The refusal is consigned to the log panel and costs no window, which is this
    command's contract for every refusal: a session that cannot put one of its
    windows back says so in the log of the case it belongs to, and puts the rest
    back.
    """
    view = FakeView()
    api = aSession(view)
    view.signalsList = [leaf()]
    QVizPlotOneNode(view, view.signalsList[0]).execute()

    assert QVizPlotOneNode(view, view.signalsList[0],
                           figureKey='SlicesPlot1').execute() is None

    assert 'SlicesPlot1' in caplog.text
    assert list(api.figureframes) == ['SlicesPlot1']


@pytest.mark.ui
def test_a_figure_key_the_api_hands_out_is_the_one_the_command_asks_for(qapp):
    view = FakeView()
    api = aSession(view)
    view.signalsList = [leaf()]

    frame = QVizPlotOneNode(view, view.signalsList[0],
                            figureKey='SlicesPlot7').execute()

    assert frame.figureKey == 'SlicesPlot7'
    assert list(api.figureframes) == ['SlicesPlot7']


@pytest.mark.ui
def test_the_stacked_command_takes_the_key_its_file_names(qapp):
    """The third plot command, the same promise.

    A Stacked Plot View is filled from the selection, so its key was the one the
    api handed out whatever the session asked for: a file naming
    `StackedPlotView:7` came back as `StackedPlotView:1`, and the key is the name
    the *Show/Hide* and *Delete* menus address that window by -- the two commands
    that read the session's own file.
    """
    view = FakeView()
    api = ownership.keep(aSession(view))
    first = leaf('vector', 'foo/time_slice(i)/vector')
    second = leaf('theta_vector', 'foo/time_slice(i)/theta_vector')
    view.signalsList = [first, second]
    QVizSelectNodes(view).selectNode(first)
    QVizSelectNodes(view).selectNode(second)

    frame = QVizPlotAsStacked(view, plotAxis='TIME',
                              figureKey='StackedPlotView:7').execute()

    assert frame is not None
    assert frame.figureKey == 'StackedPlotView:7'
    assert list(api.figureframes) == ['StackedPlotView:7']


# ---------------------------------------------------------------------------
# The two entries of the main menu.

class StubBrowser:
    def getActiveUsername(self):
        return ''


class StubMainWindow:
    """What the main menu controller asks of the window it belongs to."""

    def __init__(self, mdi):
        self.mdi = mdi
        self.IMASdbBrowserWidget = StubBrowser()

    def getMDI(self):
        return self.mdi


def menuLabels(menu):
    return [action.text() for action in menu.actions()]


def subMenusOf(menu):
    return [action.menu() for action in menu.actions() if action.menu()]


@pytest.mark.ui
def test_the_main_menu_offers_to_save_the_session(qapp):
    # The listener widget is held in a name, not passed as a temporary: the
    # QActions the controller builds are parented on it, and a temporary dies
    # when the call returns, taking the entries with it -- which is what the
    # application avoids by passing a widget that lives as long as the menu.
    listener = QWidget()
    view = QMenu()
    QVizMainMenuController(StubMainWindow(QMdiArea())).updateMenu(view,
                                                                  listener)

    assert 'Save session' in menuLabels(view)
    # Nothing has been saved yet: an empty list leaves no sub-menu on screen.
    assert [sub.title() for sub in subMenusOf(view)] == ['Show/Hide shot views',
                                                         'Delete']


@pytest.mark.ui
def test_the_main_menu_lists_the_sessions_the_folder_holds(qapp):
    aSessionFile().write(QVizSessionFile.named('weekend'))
    aSessionFile().write(QVizSessionFile.named('monday'))
    listener = QWidget()
    view = QMenu()
    QVizMainMenuController(StubMainWindow(QMdiArea())).updateMenu(view,
                                                                  listener)

    load = [sub for sub in subMenusOf(view) if sub.title() == 'Load session']
    assert len(load) == 1
    assert [action.text() for action in load[0].actions()] \
        == ['monday.vsess', 'weekend.vsess']


# ---------------------------------------------------------------------------

def _write(name, body):
    path = os.path.join(QVizConfigurationFile.directory(), name)
    with open(path, 'w') as handle:
        handle.write(body)
    return path


def _path(name):
    return os.path.join(QVizConfigurationFile.directory(), name)
