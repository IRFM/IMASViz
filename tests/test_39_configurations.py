# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A configuration: what it holds, and what applying it puts back on the screen.

The manual promises two kinds of file under :file:`$HOME/.imasviz` -- a node
selection and a plot configuration -- and says a plot configuration holds
"which quantities" and "the place of each panel in the table", while the style
is not applied and is named in the log. Measured against the two writers and
the two readers this replaces, none of that held:

* the Table Plot View's *Save Plot Configuration* button wrote **no file at
  all**. It read 23 keys out of ``PlotDataItem.opts`` by name and this
  pyqtgraph (0.13.7) does not have them: ``KeyError: 'name'``, and with that
  key supplied by hand ``AttributeError: 'tuple' object has no attribute
  'brush'`` -- on a window of two panels and on one holding a curve of 1642
  points.
* a window whose first panel carried no ``signalData`` was written anyway: the
  loop stopped there, leaving a file of **363 bytes** with **0** quantities in
  it and no word saying so.
* the reader kept **two attributes per panel** -- path and occurrence. The row
  and column the same writer had put in the file were read by nobody: measured,
  a file naming (0, 0) and (1, 1) laid its panels at (0, 0) and (0, 1), while
  the manual promises the place back.
* the abscissa the window was drawn with was not in the file: a window drawn
  along ``time`` came back along ``rho_tor`` and ``theta_poloidal``, first
  abscissa values ``[0, 1, 2, 3]`` instead of the time base.
* the reader asked the file **name**: the same XML named ``probe.xyz`` answered
  "no quantities" without a word, ``endswith('lsp')`` -- no dot -- took
  ``probe.notlsp`` for a node selection, and a truncated file raised
  ``ParseError: no element found: line 1, column 35`` out of the slot asked to
  apply it.
* the name typed in the dialog was trusted: ``probe.lsp`` wrote ``probe..lsp``
  (three characters removed from a four character extension) and ``../outside``
  wrote **outside** the configuration folder.
* ``Viz_API.SelectSignals``, the scripted entry the manual shows with a plain
  list of paths, raised ``TypeError: list indices must be integers or slices,
  not str`` on the documented form; given the dictionary form it rewrote the
  caller's own list (``['foo.time_slice[i].vector']`` came back as
  ``['foo/time_slice(i)/vector']``), and three paths with two occurrences raised
  ``IndexError`` instead of the reason its own code states two lines later.

What replaces them is one module defining the file, two commands writing it and
one applying it. The two shapes the old writers produced are still read, so the
files already on users' disks keep working -- their styling is counted and
named, as the manual says.
"""

import os

import numpy as np
import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMdiArea, QWidget

from imasviz.VizGUI.VizConfigurations.QVizApplyConfigurations import \
    QVizApplyConfigurations
from imasviz.VizGUI.VizConfigurations.QVizConfigurationFile import \
    QVizConfigurationFile, QVizQuantity, PLOT, SELECTION
from imasviz.VizGUI.VizConfigurations.QVizSavePlotConfiguration import \
    QVizSavePlotConfiguration
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSaveNodeSelection \
    import QVizSaveNodeSelection
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectFromConfiguration \
    import QVizSelectFromConfiguration
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectNodes \
    import QVizSelectNodes
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlot import QVizTablePlot
from imasviz.VizUtils import QVizGlobalOperations
from imasviz.Viz_API import Viz_API

from support.fakes import FakeAxesNode

RHO = [0., 1., 2., 3.]
THETA = [0., .25, .5, .75]
TIMES = [0., 1., 2., 3., 4.]
URI = 'imas:hdf5?case=1'


@pytest.fixture(autouse=True)
def configurationFolder(tmp_path, monkeypatch):
    """Keep every configuration inside the test, and out of the real ~/.imasviz.

    The suite does not isolate $HOME: a test that saved a configuration through
    the application would otherwise write into the folder the user works with.
    The helpers read HOME when they are called, so setting it here is enough.
    """
    monkeypatch.setenv('HOME', str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# The quantities, on stand-ins that answer the way a tree node does.

def _ids():
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = list(TIMES)
    ids.rho_tor = list(RHO)
    ids.theta_poloidal = list(THETA)
    ids.time_slice = []
    for timeIndex in range(len(TIMES)):
        timeSlice = type(str('TimeSlice'), (), {})()
        timeSlice.time = TIMES[timeIndex]
        timeSlice.vector = [100. * timeIndex + 10. * i for i in range(len(RHO))]
        timeSlice.theta_vector = [1. * timeIndex + .1 * i
                                  for i in range(len(THETA))]
        ids.time_slice.append(timeSlice)
    return ids


class Node(FakeAxesNode):
    """A leaf held by an array of structures, answering for a window and a tree.

    The plot side needs the axes model (test_36 spells the same stub); the
    selection side needs what ``QVizSelectNodes`` asks a node: the path and the
    occurrence the tree spells, the style it recolours, and the parent chain it
    walks to find the view.
    """

    def __init__(self, *args, **kwargs):
        FakeAxesNode.__init__(self, *args, **kwargs)
        self.colour = 'other'

    def is0DAndDynamic(self):
        return self._dataType == 'FLT_0D'

    def is1DAndDynamic(self):
        return self._dataType == 'FLT_1D'

    def hasTimeAxis(self):
        return True

    def isPlotToPerformAlongTimeAxis(self, plotWidget=None):
        if plotWidget is None:
            return self.hasTimeAxis()
        axis = plotWidget.getPlotAxis()
        if axis == 'TIME':
            return self.hasTimeAxis()
        if axis in ('DEFAULT', 'COORDINATE1'):
            if self.is0DAndDynamic():
                return True
            if self.is1DAndDynamic():
                return False
        return None

    def getPath(self):
        return self.getInfoDict().get('Path')

    def getOccurrence(self):
        return self.getInfoDict().get('occurrence')

    def parent(self):
        return None

    def setStyleWhenSelected(self):
        self.colour = 'selected'

    def setStyleWhenContainingData(self):
        self.colour = 'other'


def node(dataType, name, coordinates, units='K'):
    return Node(_ids(), 'foo', 'foo.time_slice[itime]', dataType, name=name,
                units=units, itimeIndex=0, coordinates=coordinates,
                coordinateUnits={number: 'm'
                                 for number in range(1, len(coordinates) + 1)},
                indices={'i': '1'}, lengths={'i': str(len(TIMES))},
                infoDict={'Path': 'foo/time_slice(i)/' + name,
                          'occurrence': 0,
                          'name': name})


def _vector():
    return node('FLT_1D', 'vector', ('rho_tor',))


def _theta():
    return node('FLT_1D', 'theta_vector', ('theta_poloidal',), units='rad')


class FakeSource(QObject):
    name = 'NATIVE'
    uri = URI

    def dataKey(self, treeNode):
        return treeNode.getParametrizedDataPath()


def aView(parent):
    """One shot view: the selection record, the signal list, and the api."""

    class FakeView(QObject):
        def __init__(self):
            super().__init__()
            self.uri = URI
            self.parent = parent
            self.dataSource = FakeSource()
            self.selectedItem = None
            self.selectedSignalsDict = {}
            self.signalsList = []
            self.ids_roots_occurrence = {'foo/0': None}

    view = FakeView()
    view.mdi = QMdiArea()
    view.imas_viz_api = Viz_API(parent=view.mdi)
    view.imas_viz_api.DTVlist = [view]
    return view


@pytest.fixture
def view(qapp):
    # The frame owns the shot view the configuration window is built on, and the
    # view has to keep the frame: a parent held only as a local dies at the end
    # of the fixture and Qt takes its children with it.
    frame = QWidget()
    frame.setWindowTitle('54924 - west - imas:hdf5?case=1')
    frame.dataTreeView = view = aView(frame)
    view.frame = frame
    return view


def select(view, *nodes):
    view.signalsList = list(nodes)
    view.selectedSignalsDict = {n.getParametrizedDataPath():
                                {'index': index,
                                 'QTreeWidgetItem': n,
                                 'uri': URI}
                                for index, n in enumerate(nodes)}
    return view


def fillTree(view, *nodes):
    """The tree as it stands when a configuration is applied to it.

    A configuration names paths and the view has to hold the nodes they name;
    nothing is selected here, which is the point -- applying a configuration is
    what selects them.
    """
    view.signalsList = list(nodes)
    return view


def listedNames(listWidget):
    return [listWidget.item(row).text() for row in range(listWidget.count())]


def pathsInSelection(view):
    return [entry['QTreeWidgetItem'].getPath()
            for entry in view.selectedSignalsDict.values()]


def fill(view, *nodes):
    """Draw the selection into a Table Plot View, as the menu entry does."""
    select(view, *nodes)
    QVizSignalHandling(view).onPlotToTablePlotView(all_DTV=False,
                                                   plotAxis='TIME')
    return tables(view)[0]


def tables(view):
    return [frame for frame in view.imas_viz_api.figureframes.values()
            if isinstance(frame, QVizTablePlot)]


def panelData(frame, index=0):
    x, y = frame.panels()[index].curves()[0].getData()
    return np.asarray(x), np.asarray(y)


# ---------------------------------------------------------------------------
# The file itself.

@pytest.mark.ui
def test_a_saved_configuration_gives_back_its_quantities_their_place_and_its_abscissa():
    """What the manual says a configuration holds, and nothing else."""
    configuration = QVizConfigurationFile(
        kind=PLOT,
        quantities=[QVizQuantity('foo/time_slice(i)/vector', 0, 0, 0, URI),
                    QVizQuantity('foo/time_slice(i)/theta_vector', 1, 1, 1, URI)],
        abscissa='TIME')
    path = configuration.write(QVizConfigurationFile.named('saved', PLOT))

    read = QVizConfigurationFile.read(path)

    assert read.kind == PLOT
    assert read.abscissa == 'TIME'
    assert [(q.path, q.occurrence, q.row, q.column) for q in read.quantities] \
        == [('foo/time_slice(i)/vector', 0, 0, 0),
            ('foo/time_slice(i)/theta_vector', 1, 1, 1)]
    assert read.styledPanels == 0


@pytest.mark.ui
def test_an_older_plot_configuration_is_still_read_and_its_styling_counted():
    """Files already on users' disks: read for their quantities, styling named.

    The old writer spelled the place twice -- a ``key="(row, column)"`` and
    ``row``/``column`` attributes -- and put the path under ``sourceInfo``.
    """
    path = _write('old.pcfg', """
    <PlotConfiguration>
      <GraphicsWindow>
        <PlotItem key="(0, 1)" row="0" column="1" title="a panel">
          <PlotDataItem>
            <sourceInfo path="foo.time_slice[i].vector" occurrence="0"
                        uri="imas:hdf5?case=1"/>
            <opts connect="True" antialias="True"/>
          </PlotDataItem>
        </PlotItem>
        <PlotItem key="(1, 0)" row="1" column="0" title="another panel">
          <PlotDataItem>
            <sourceInfo path="foo.time_slice[i].theta_vector" occurrence="0"
                        uri="imas:hdf5?case=1"/>
            <opts connect="True" antialias="True"/>
          </PlotDataItem>
        </PlotItem>
      </GraphicsWindow>
    </PlotConfiguration>""")

    read = QVizConfigurationFile.read(path)

    assert read.kind == PLOT
    assert read.styledPanels == 2
    assert [(q.path, q.row, q.column) for q in read.quantities] \
        == [('foo.time_slice[i].vector', 0, 1),
            ('foo.time_slice[i].theta_vector', 1, 0)]
    assert read.treePaths() == ['foo/time_slice(i)/vector',
                                'foo/time_slice(i)/theta_vector']


@pytest.mark.ui
def test_an_older_node_selection_is_still_read_with_its_occurrences_as_numbers():
    """The old reader handed the occurrences back as strings; the format does not."""
    path = _write('old.lsp', """
    <SignalSelection comment="generated by IMASVIZ">
      <ListOfSignalPaths>
        <IDSPath key="0" path="foo.time_slice[i].vector" occurrence="0"
                 uri="imas:hdf5?case=1"/>
        <IDSPath key="1" path="foo.time_slice[i].theta_vector" occurrence="2"
                 uri="imas:hdf5?case=1"/>
      </ListOfSignalPaths>
    </SignalSelection>""")

    read = QVizConfigurationFile.read(path)

    assert read.kind == SELECTION
    assert [(q.path, q.occurrence) for q in read.quantities] \
        == [('foo.time_slice[i].vector', 0),
            ('foo.time_slice[i].theta_vector', 2)]
    assert all(isinstance(q.occurrence, int) for q in read.quantities)


@pytest.mark.ui
def test_a_file_is_known_by_what_it_holds_and_not_by_the_extension_it_wears():
    """Measured: the same XML named probe.xyz answered no quantities at all."""
    body = ('<SignalSelection><ListOfSignalPaths><IDSPath key="0" '
            'path="foo/rho_tor" occurrence="0"/></ListOfSignalPaths>'
            '</SignalSelection>')
    read = QVizConfigurationFile.read(_write('probe.xyz', body))

    assert read.kind == SELECTION
    assert len(read.quantities) == 1


@pytest.mark.ui
def test_a_file_holding_something_else_is_refused_naming_its_root_element():
    path = _write('other.pcfg', '<PulseFile><shot>54924</shot></PulseFile>')

    with pytest.raises(ValueError) as raised:
        QVizConfigurationFile.read(path)

    assert '<PulseFile>' in str(raised.value)


@pytest.mark.ui
def test_a_file_that_is_not_well_formed_xml_answers_with_a_reason():
    """Measured: a truncated file raised ParseError out of the applying slot."""
    path = _write('broken.pcfg', '<?xml version="1.0"?><PlotConfig')

    with pytest.raises(ValueError) as raised:
        QVizConfigurationFile.read(path)

    assert 'well-formed' in str(raised.value)


@pytest.mark.ui
def test_a_missing_file_answers_with_a_reason():
    with pytest.raises(ValueError) as raised:
        QVizConfigurationFile.read('/no/such/file.pcfg')

    assert 'Cannot read' in str(raised.value)


@pytest.mark.ui
def test_the_folder_lists_each_kind_by_its_own_extension():
    """Measured: endswith('lsp'), no dot, took probe.notlsp for a selection."""
    for name in ('one.pcfg', 'two.lsp', 'three.notlsp', 'four.xpcfg'):
        _write(name, '<IMASVizConfiguration kind="selection"/>')

    assert QVizConfigurationFile.listing(SELECTION) == ['two.lsp']
    assert QVizConfigurationFile.listing(PLOT) == ['one.pcfg']


@pytest.mark.ui
def test_a_name_typed_with_its_extension_on_it_is_written_once():
    """Measured: typing probe.lsp wrote probe..lsp."""
    assert os.path.basename(QVizConfigurationFile.named('probe.lsp',
                                                        SELECTION)) \
        == 'probe.lsp'
    assert os.path.basename(QVizConfigurationFile.named('probe', SELECTION)) \
        == 'probe.lsp'


@pytest.mark.ui
def test_a_name_that_names_a_place_rather_than_a_configuration_is_refused():
    """Measured: typing ../outside wrote outside the configuration folder."""
    for typed in ('../outside', 'a/b', '', '.', '   '):
        with pytest.raises(ValueError):
            QVizConfigurationFile.named(typed, SELECTION)

    assert os.listdir(QVizConfigurationFile.directory()) == []


@pytest.mark.ui
def test_the_folder_the_manual_names_is_the_one_that_is_used():
    folder = QVizConfigurationFile.directory()

    assert folder.endswith('.imasviz')
    assert os.path.realpath(folder) == os.path.realpath(
        os.path.join(os.environ['HOME'], '.imasviz'))


# ---------------------------------------------------------------------------
# Saving the window the button belongs to.

@pytest.mark.ui
def test_the_save_button_writes_a_file_naming_every_panel_the_window_shows(view,
                                                                           monkeypatch):
    """Measured: the button raised KeyError and left no file on disk."""
    frame = fill(view, _vector(), _theta())
    monkeypatch.setattr(QVizGlobalOperations, 'askWithCancel',
                        lambda **kwargs: ('saved', True))

    frame.saveButton.click()

    listed = QVizConfigurationFile.listing(PLOT)
    assert listed == ['saved.pcfg']
    read = QVizConfigurationFile.read(
        os.path.join(QVizConfigurationFile.directory(), listed[0]))
    assert [q.path for q in read.quantities] == ['foo/time_slice(i)/vector',
                                                 'foo/time_slice(i)/theta_vector']
    assert read.abscissa == 'TIME'


@pytest.mark.ui
def test_the_place_written_for_a_panel_is_the_place_it_sits_in(view):
    frame = fill(view, _vector(), _theta())

    quantities = QVizSavePlotConfiguration(view, frame,
                                           name='placed').quantities()

    written = [(q.row, q.column) for q in quantities]
    assert written == [(row, column) for row, column, _ in
                       frame.panelsInTable()]


@pytest.mark.ui
def test_a_window_whose_panels_carry_nothing_is_written_whole(view):
    """Measured: a panel without signalData stopped the loop at 0 quantities."""
    frame = fill(view, _vector(), _theta())
    for panel in frame.panels():
        panel.signalData = None

    path = QVizSavePlotConfiguration(view, frame, name='empty').execute()

    assert len(QVizConfigurationFile.read(path).quantities) == 2


@pytest.mark.ui
def test_a_bad_name_is_said_in_the_log_rather_than_left_as_a_traceback(view,
                                                                       caplog,
                                                                       monkeypatch):
    frame = fill(view, _vector())
    monkeypatch.setattr(QVizGlobalOperations, 'askWithCancel',
                        lambda **kwargs: ('../outside', True))

    frame.saveButton.click()

    assert QVizConfigurationFile.listing(PLOT) == []
    assert 'not a configuration name' in caplog.text


# ---------------------------------------------------------------------------
# Applying a configuration: the place, and the abscissa.

def _plotConfiguration(name, entries, abscissa=None):
    """A '.pcfg' in the shape this release writes."""
    configuration = QVizConfigurationFile(
        kind=PLOT, abscissa=abscissa,
        quantities=[QVizQuantity(path, 0, row, column, URI)
                    for path, row, column in entries])
    return configuration.write(QVizConfigurationFile.named(name, PLOT))


@pytest.mark.ui
def test_a_configuration_naming_where_its_panels_sat_lays_them_there(view):
    """Measured: a file naming (0, 0) and (1, 1) laid its panels at (0, 0), (0, 1)."""
    fillTree(view, _vector(), _theta())
    path = _plotConfiguration('places', [('foo/time_slice(i)/vector', 0, 0),
                                         ('foo/time_slice(i)/theta_vector', 1, 1)])

    QVizSignalHandling(view).onPlotToTablePlotView(all_DTV=False,
                                                   configFile=path)

    frame = tables(view)[0]
    assert [(row, column) for row, column, _ in frame.panelsInTable()] \
        == [(0, 0), (1, 1)]


@pytest.mark.ui
def test_a_window_saved_along_time_comes_back_along_time(view):
    """Measured: it came back along rho_tor, first values [0, 1, 2, 3]."""
    fillTree(view, _vector())
    path = _plotConfiguration('along', [('foo/time_slice(i)/vector', 0, 0)],
                              abscissa='TIME')

    QVizSignalHandling(view).onPlotToTablePlotView(all_DTV=False,
                                                   configFile=path)

    frame = tables(view)[0]
    assert frame.getPlotAxis() == 'TIME'
    x, y = panelData(frame)
    np.testing.assert_allclose(x, TIMES)
    np.testing.assert_allclose(y, [100. * t for t in TIMES])


@pytest.mark.ui
def test_the_abscissa_the_caller_named_wins_over_the_file(view):
    fillTree(view, _vector())
    path = _plotConfiguration('along', [('foo/time_slice(i)/vector', 0, 0)],
                              abscissa='TIME')

    QVizSignalHandling(view).onPlotToTablePlotView(all_DTV=False,
                                                   plotAxis='DEFAULT',
                                                   configFile=path)

    frame = tables(view)[0]
    assert frame.getPlotAxis() == 'DEFAULT'
    x, _ = panelData(frame)
    np.testing.assert_allclose(x, RHO)


@pytest.mark.ui
def test_a_configuration_written_now_says_nothing_about_styling(view, caplog):
    """The refusal is for the files that hold styling, not for every file."""
    fillTree(view, _vector())
    path = _plotConfiguration('plain', [('foo/time_slice(i)/vector', 0, 0)])

    QVizSignalHandling(view).onPlotToTablePlotView(all_DTV=False,
                                                   configFile=path)

    assert tables(view)[0].panelCount() == 1
    assert 'not applied' not in caplog.text


# ---------------------------------------------------------------------------
# A node selection: written once, applied anywhere.

@pytest.mark.ui
def test_saving_a_selection_writes_its_nodes_in_the_order_they_were_picked(view):
    first, second = _vector(), _theta()
    select(view, first, second)

    path = QVizSaveNodeSelection(view, name='selection').execute()

    assert [q.path for q in QVizConfigurationFile.read(path).quantities] \
        == [first.getPath(), second.getPath()]
    assert QVizConfigurationFile.listing(SELECTION) == ['selection.lsp']


@pytest.mark.ui
def test_a_selection_of_nothing_is_said_rather_than_written_as_an_empty_file(view):
    select(view)

    with pytest.raises(ValueError) as raised:
        QVizSaveNodeSelection(view, name='nothing').execute()

    assert 'no node is selected' in str(raised.value)
    assert QVizConfigurationFile.listing(SELECTION) == []


@pytest.mark.ui
def test_a_saved_selection_selects_the_same_nodes_in_another_view(view):
    """The manual's promise: one database's selection, another database's tree."""
    select(view, _theta(), _vector())
    path = QVizSaveNodeSelection(view, name='across').execute()

    other = aView(view.frame)
    other.signalsList = list(view.signalsList)
    selected = QVizSelectFromConfiguration(other, path).execute()

    assert selected == 2
    assert pathsInSelection(other) == ['foo/time_slice(i)/theta_vector',
                                       'foo/time_slice(i)/vector']
    assert [entry['QTreeWidgetItem'].getPath()
            for entry in other.selectedSignalsDict.values()] \
        == pathsInSelection(view)


@pytest.mark.ui
def test_a_quantity_the_tree_does_not_hold_is_named_and_the_rest_is_kept(view,
                                                                         caplog):
    select(view, _theta())
    path = QVizSaveNodeSelection(view, name='partial').execute()

    other = aView(view.frame)
    other.signalsList = [_vector()]
    assert QVizSelectFromConfiguration(other, path).execute() == 0
    assert 'foo/time_slice(i)/theta_vector' in caplog.text
    assert 'not in this tree' in caplog.text


# ---------------------------------------------------------------------------
# The scripted entry the manual shows with a plain list of paths.

@pytest.mark.ui
def test_the_api_selects_a_list_of_paths_as_the_manual_spells_it(view):
    """Measured: this raised TypeError: list indices must be integers, not str."""
    view.signalsList = [_vector(), _theta()]
    api = Viz_API(parent=view.mdi)

    api.SelectSignals(view.frame, ['foo/time_slice(i)/vector',
                                   'foo/time_slice(i)/theta_vector'])

    assert sorted(pathsInSelection(view)) \
        == ['foo/time_slice(i)/theta_vector', 'foo/time_slice(i)/vector']


@pytest.mark.ui
def test_the_api_leaves_the_list_it_was_handed_alone(view):
    """Measured: the old command rewrote the caller's own list in place."""
    view.signalsList = [_vector()]
    paths = ['foo.time_slice[i].vector']
    api = Viz_API(parent=view.mdi)

    api.SelectSignals(view.frame, {'paths': paths, 'occurrences': [0]})

    assert paths == ['foo.time_slice[i].vector']
    assert pathsInSelection(view) == ['foo/time_slice(i)/vector']


@pytest.mark.ui
def test_three_paths_and_two_occurrences_answer_with_the_reason(view):
    """Measured: IndexError: list index out of range, two lines above a ValueError."""
    api = Viz_API(parent=view.mdi)

    with pytest.raises(ValueError) as raised:
        api.SelectSignals(view.frame,
                          {'paths': ['foo/a', 'foo/b', 'foo/c'],
                           'occurrences': [0, 1]})

    assert 'number of specified occurrences' in str(raised.value)


# ---------------------------------------------------------------------------
# The window that lists them.

@pytest.mark.ui
def test_the_window_lists_the_folder_every_time_it_is_shown(view):
    """Measured: the list was refreshed by reaching through three attributes."""
    window = QVizApplyConfigurations(view)
    assert window.tabs.widget(1).listWidget.count() == 0

    _plotConfiguration('late', [('foo/time_slice(i)/vector', 0, 0)],
                       abscissa='TIME')
    window.show()

    assert listedNames(window.tabs.widget(0).listWidget) == ['late.pcfg']


@pytest.mark.ui
def test_applying_a_node_selection_selects_it_in_the_view_it_belongs_to(view):
    select(view, _theta(), _vector())
    QVizSaveNodeSelection(view, name='mine').execute()
    # The tree keeps its nodes when the selection is cleared: applying the
    # configuration has to find them again by path.
    view.selectedSignalsDict = {}

    window = QVizApplyConfigurations(view)
    window.tabs.widget(1).listWidget.setCurrentRow(0)
    window.apply(SELECTION)

    assert pathsInSelection(view) == ['foo/time_slice(i)/theta_vector',
                                      'foo/time_slice(i)/vector']
    assert QVizSelectNodes(view).isSelected(view.signalsList[0])


@pytest.mark.ui
def test_applying_a_plot_configuration_selects_and_draws_it(view):
    fillTree(view, _vector())
    _plotConfiguration('drawn', [('foo/time_slice(i)/vector', 0, 0)],
                       abscissa='TIME')

    window = QVizApplyConfigurations(view)
    window.tabs.widget(0).listWidget.setCurrentRow(0)
    frame = window.apply(PLOT, andPlot=True)

    assert frame is not None
    assert pathsInSelection(view) == ['foo/time_slice(i)/vector']
    assert frame.panelCount() == 1


@pytest.mark.ui
def test_removing_a_configuration_deletes_the_file_and_its_entry(view,
                                                                 monkeypatch):
    _plotConfiguration('gone', [('foo/time_slice(i)/vector', 0, 0)])
    window = QVizApplyConfigurations(view)
    window.tabs.widget(0).listWidget.setCurrentRow(0)
    monkeypatch.setattr(QVizGlobalOperations, 'YesNo', lambda **kwargs: True)

    removed = window.remove(PLOT)

    assert not os.path.exists(removed)
    assert window.tabs.widget(0).listWidget.count() == 0


def _write(name, body):
    """A file in the configuration folder, whatever shape it was written in."""
    path = os.path.join(QVizConfigurationFile.directory(), name)
    with open(path, 'w') as handle:
        handle.write(body.strip())
    return path
