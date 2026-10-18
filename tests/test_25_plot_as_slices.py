# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The plot command that goes through the tensor read, from selection to figure.

The curve figure and the read each have their own tests; what is checked here is
what only the command does: create a frame the api knows about, walk the
selection of one view or of all of them, keep a refusal from costing the user the
curves that did read, and leave nothing behind when nothing could be drawn.

A rank 3 quantity is in the selection on purpose. The legacy command refuses
anything the dictionary does not rank 0 or 1, so that case is the difference
between the two paths rather than a variation of one.
"""

import pytest

from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsSlices import QVizPlotAsSlices
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot

from support.fakes import FakeAxesNode

AOS, LEAF = 'AOS', 'LEAF'
ION = (AOS, 'foo', 'ion')
RADIAL = (LEAF, 'foo', 'dimension 1')

# Two time slices, two ions each, three radial points each.
VALUES = {'z_ion': [[[1., 2., 3.], [10., 20., 30.]],
                    [[4., 5., 6.], [40., 50., 60.]]]}


def _idsWith(leafValues):
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0., 1.]
    shape = next(iter(leafValues.values()))
    ids.profiles_1d = []
    for index in range(len(shape)):
        slice_ = type(str('Slice'), (), {})()
        slice_.time = None
        slice_.ion = []
        for ionIndex in range(len(shape[0])):
            ion = type(str('Ion'), (), {})()
            for leaf, values in leafValues.items():
                setattr(ion, leaf, values[index][ionIndex])
            slice_.ion.append(ion)
        ids.profiles_1d.append(slice_)
    return ids


def _rankThreeLeaf(ids=None):
    """foo.profiles_1d[itime].ion[j].z_ion: time drawn, ion and radius pinned."""
    return FakeAxesNode(ids if ids is not None else _idsWith(VALUES), 'foo',
                        'foo.profiles_1d[itime].ion[j]', 'FLT_1D', name='z_ion',
                        itimeIndex=0, coordinates=('1..N',),
                        indices={'i': '0', 'j': '1'}, lengths={'i': '2', 'j': '2'})


def _emptyRankThreeLeaf():
    """The same quantity in the same arrays, holding nothing."""
    ids = _idsWith(VALUES)
    for slice_ in ids.profiles_1d:
        for ion in slice_.ion:
            ion.z_ion = []
    return _rankThreeLeaf(ids)


def _scalarInTime():
    """foo.profiles_1d[itime].gap: time is the only axis, so nothing is pinned."""
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0., 1.]
    ids.profiles_1d = []
    for gap in (100., 200.):
        element = type(str('Element'), (), {})()
        element.time = None
        element.gap = gap
        ids.profiles_1d.append(element)
    return FakeAxesNode(ids, 'foo', 'foo.profiles_1d[itime]', 'FLT_0D', name='gap',
                        itimeIndex=0, coordinates=(), lengths={'i': '2'})


class FakeSource:
    def __init__(self, uri):
        self.uri = uri

    def dataKey(self, treeNode):
        return treeNode.getParametrizedDataPath()


class FakeView:
    """Enough of QVizDataTreeView for the command: a selection and a source."""

    def __init__(self, uri, nodes):
        self.uri = uri
        self.dataSource = FakeSource(uri)
        self.selectedItem = None
        self.selectedSignalsDict = {node.getParametrizedDataPath():
                                    {'QTreeWidgetItem': node} for node in nodes}
        self.imas_viz_api = None


class FakeApi:
    """The figure bookkeeping the command uses, without the window machinery."""

    def __init__(self, views):
        self.figureframes = {}
        self.figToNodes = {}
        self.DTVlist = list(views)
        for view in views:
            view.imas_viz_api = self

    def AddNodeToFigure(self, figureKey, key, tup):
        self.figToNodes.setdefault(figureKey, {})[key] = tup

    def DeleteFigure(self, figureKey):
        frame = self.figureframes.pop(figureKey, None)
        if frame is not None:
            frame.close()
        self.figToNodes.pop(figureKey, None)

    def GetFiguresKeys(self, figureType='Figure:'):
        return sorted(key for key in self.figureframes if key.startswith(figureType))


def _command(*nodes, all_DTV=True, otherViews=()):
    """A command over one view holding `nodes`, plus any number of other views."""
    view = FakeView('imas:hdf5?case=1', list(nodes))
    api = FakeApi([view] + list(otherViews))
    return QVizPlotAsSlices(dataTreeView=view, all_DTV=all_DTV)


def plotted(frame, index=0):
    x, y = frame.curves()[index].getData()
    return list(x), list(y)


@pytest.mark.ui
def test_the_command_builds_a_curve_figure_the_api_knows_about(qtbot):
    command = _command(_scalarInTime())
    frame = command.execute()

    assert isinstance(frame, QVizCurvePlot)
    assert command.api.figureframes[command.figureKey] is frame


@pytest.mark.ui
def test_every_selected_node_of_the_view_is_drawn(qtbot):
    frame = _command(_scalarInTime(), _rankThreeLeaf()).execute()

    assert frame.curveCount() == 2
    assert plotted(frame, 0) == ([0., 1.], [100., 200.])
    assert plotted(frame, 1) == ([0., 1.], [10., 40.])


@pytest.mark.ui
def test_a_rank_three_selection_is_not_refused(qtbot):
    # The legacy command logs 'Plots dimension larger than 1D are currently not
    # supported.' and stops here.
    frame = _command(_rankThreeLeaf()).execute()

    assert frame.curveCount() == 1
    assert frame.sliceControls.keys() == [ION, RADIAL]
    assert [row.nameLabel.text() for row in frame.sliceControls.rows()] == \
           ['ion:', 'dimension 1:']


@pytest.mark.ui
def test_the_curve_still_answers_its_controls_after_the_command_is_done(qtbot):
    # The command is gone by then; the frame holds the loop on its own.
    frame = _command(_rankThreeLeaf()).execute()

    frame.sliceControls.setIndex(ION, 0)

    assert plotted(frame)[1] == [1., 4.]


@pytest.mark.ui
def test_the_nodes_are_registered_under_the_figure(qtbot):
    command = _command(_scalarInTime(), _rankThreeLeaf())
    command.execute()
    registered = command.api.figToNodes[command.figureKey]

    assert sorted(registered) == ['foo.profiles_1d[itime].gap',
                                  'foo.profiles_1d[itime].ion[j].z_ion']
    assert registered['foo.profiles_1d[itime].gap'][0] == 'imas:hdf5?case=1'


@pytest.mark.ui
def test_one_unreadable_node_does_not_cost_the_other_curves(qtbot):
    frame = _command(_emptyRankThreeLeaf(), _scalarInTime()).execute()

    assert frame.curveCount() == 1
    assert plotted(frame) == ([0., 1.], [100., 200.])


@pytest.mark.ui
def test_a_figure_with_nothing_on_it_is_not_left_behind(qtbot):
    command = _command(_emptyRankThreeLeaf())

    with pytest.raises(ValueError):
        command.execute()

    assert command.api.figureframes == {}
    assert command.api.figToNodes == {}


@pytest.mark.ui
def test_no_selection_raises_and_leaves_no_frame(qtbot):
    command = _command()

    with pytest.raises(ValueError):
        command.execute()

    assert command.api.figureframes == {}


@pytest.mark.ui
def test_the_selections_of_all_views_are_drawn_on_one_figure(qtbot):
    other = FakeView('imas:hdf5?case=2', [_rankThreeLeaf()])
    frame = _command(_scalarInTime(), otherViews=[other]).execute()

    assert frame.curveCount() == 2


@pytest.mark.ui
def test_this_view_only_leaves_the_other_selections_alone(qtbot):
    other = FakeView('imas:hdf5?case=2', [_rankThreeLeaf()])
    frame = _command(_scalarInTime(), all_DTV=False, otherViews=[other]).execute()

    assert frame.curveCount() == 1


@pytest.mark.ui
def test_the_figure_keys_do_not_collide_with_the_legacy_figures(qtbot):
    # The legacy 'Figure:' keys are listed by the "add to an existing figure"
    # menu entries, which would be handed a frame they do not know how to fill.
    view = FakeView('imas:hdf5?case=1', [_scalarInTime()])
    api = FakeApi([view])
    api.figureframes['Figure:1'] = None
    api.figureframes['Figure:2'] = None

    first = QVizPlotAsSlices(dataTreeView=view)
    first.execute()
    second = QVizPlotAsSlices(dataTreeView=view)
    second.execute()

    assert first.figureKey == 'SlicesPlot1'
    assert second.figureKey == 'SlicesPlot2'
    assert api.GetFiguresKeys('Figure:') == ['Figure:1', 'Figure:2']
    assert api.GetFiguresKeys('SlicesPlot') == ['SlicesPlot1', 'SlicesPlot2']
