# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The plot command that goes through the tensor read, from selection to figure.

The curve figure, the image figure and the read each have their own tests; what is
checked here is what only the command does: build a frame the api knows about, walk
the selection of one view or of all of them, keep a refusal from costing the user
the curves that did read, and leave nothing behind when nothing could be drawn.
Which frame a quantity is sent to is the subject of test_27.

A rank 3 quantity is in the selection on purpose. The legacy command refuses
anything the dictionary does not rank 0 or 1, so that case is the difference
between the two paths rather than a variation of one.
"""

import pytest

from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsSlices import QVizPlotAsSlices
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot

from support.fakes import FakeAxesNode
from support.ownership import keep
from support.plotting import FakeView, FakeApi, plotCommand, plotted

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


def _curve(*nodes, **kwargs):
    """Run the command and hand back its single curve figure."""
    figures = plotCommand(*nodes, **kwargs).execute()
    assert [type(frame) for frame in figures] == [QVizCurvePlot]
    return figures[0]


@pytest.mark.ui
def test_the_command_builds_a_curve_figure_the_api_knows_about(qtbot):
    command = plotCommand(_scalarInTime())
    figures = command.execute()

    assert isinstance(figures[0], QVizCurvePlot)
    assert command.api.figureframes[command.curveFigure.figureKey] is figures[0]


@pytest.mark.ui
def test_every_selected_node_of_the_view_is_drawn(qtbot):
    frame = _curve(_scalarInTime(), _rankThreeLeaf())

    assert frame.curveCount() == 2
    assert plotted(frame, 0) == ([0., 1.], [100., 200.])
    assert plotted(frame, 1) == ([0., 1.], [10., 40.])


@pytest.mark.ui
def test_a_rank_three_selection_is_not_refused(qtbot):
    # The legacy command logs 'Plots dimension larger than 1D are currently not
    # supported.' and stops here. The ion array the tree is standing on is fixed
    # and spelled in the legend, so only the leaf's own coordinate gets a control.
    frame = _curve(_rankThreeLeaf())

    assert frame.curveCount() == 1
    assert frame.sliceControls.keys() == [RADIAL]
    assert [row.nameLabel.text() for row in frame.sliceControls.rows()] == \
           ['dimension 1:']
    assert [text.text for _, text in
            frame.pgPlotWidget.getPlotItem().legend.items] == \
           ['foo.profiles_1d[itime].ion[1].z_ion']


@pytest.mark.ui
def test_the_curve_still_answers_its_controls_after_the_command_is_done(qtbot):
    # The command is gone by then; the frame holds the loop on its own.
    frame = _curve(_rankThreeLeaf())

    frame.sliceControls.setIndex(RADIAL, 2)

    assert plotted(frame)[1] == [30., 60.]


@pytest.mark.ui
def test_the_nodes_are_registered_under_the_figure(qtbot):
    command = plotCommand(_scalarInTime(), _rankThreeLeaf())
    command.execute()
    registered = command.api.figToNodes[command.curveFigure.figureKey]

    assert sorted(registered) == ['foo.profiles_1d[itime].gap',
                                  'foo.profiles_1d[itime].ion[j].z_ion']
    assert registered['foo.profiles_1d[itime].gap'][0] == 'imas:hdf5?case=1'


@pytest.mark.ui
def test_one_unreadable_node_does_not_cost_the_other_curves(qtbot):
    frame = _curve(_emptyRankThreeLeaf(), _scalarInTime())

    assert frame.curveCount() == 1
    assert plotted(frame) == ([0., 1.], [100., 200.])


@pytest.mark.ui
def test_a_figure_with_nothing_on_it_is_not_left_behind(qtbot):
    command = plotCommand(_emptyRankThreeLeaf())

    with pytest.raises(ValueError):
        command.execute()

    assert command.api.figureframes == {}
    assert command.api.figToNodes == {}


@pytest.mark.ui
def test_no_selection_raises_and_leaves_no_frame(qtbot):
    command = plotCommand()

    with pytest.raises(ValueError):
        command.execute()

    assert command.api.figureframes == {}


@pytest.mark.ui
def test_the_selections_of_all_views_are_drawn_on_one_figure(qtbot):
    other = FakeView('imas:hdf5?case=2', [_rankThreeLeaf()])
    frame = _curve(_scalarInTime(), otherViews=[other])

    assert frame.curveCount() == 2


@pytest.mark.ui
def test_this_view_only_leaves_the_other_selections_alone(qtbot):
    other = FakeView('imas:hdf5?case=2', [_rankThreeLeaf()])
    frame = _curve(_scalarInTime(), all_DTV=False, otherViews=[other])

    assert frame.curveCount() == 1


@pytest.mark.ui
def test_the_figure_keys_do_not_collide_with_the_legacy_figures(qtbot):
    # The legacy 'Figure:' keys are listed by the "add to an existing figure"
    # menu entries, which would be handed a frame they do not know how to fill.
    view = FakeView('imas:hdf5?case=1', [_scalarInTime()])
    # This is the one test here that builds its commands by hand instead of
    # through the helper, so nothing else outlives the call: the api is what
    # holds the two frames this draws, and the command shows them
    # (QVizPlotAsSlices.show), so dropping the api drops two windows Qt has
    # already painted -- see support/ownership.py.
    api = keep(FakeApi([view]))
    api.figureframes['Figure:1'] = None
    api.figureframes['Figure:2'] = None

    first = QVizPlotAsSlices(dataTreeView=view)
    first.execute()
    second = QVizPlotAsSlices(dataTreeView=view)
    second.execute()

    assert first.curveFigure.figureKey == 'SlicesPlot1'
    assert second.curveFigure.figureKey == 'SlicesPlot2'
    assert api.GetFiguresKeys('Figure:') == ['Figure:1', 'Figure:2']
    assert api.GetFiguresKeys('SlicesPlot') == ['SlicesPlot1', 'SlicesPlot2']
