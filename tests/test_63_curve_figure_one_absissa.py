# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""One curve figure, one abscissa -- asked of the figure, not of the quantity.

A curve figure has one bottom label, so the question "may this quantity be added
to that figure?" is about the abscissa the figure already draws. Three places
used to answer it separately and none of them knew the figure: the menus compared
a key taken off the quantity's axes, the read fell back on a string the frame
carried, and the label said whatever the last trace said. Measured on the
reference case (WEST 54924 at DD 3.35.0) before the change, on the two leaves of
one `profiles_1d` structure:

    key of `.f`     ('LEAF', 'equilibrium', 'time_slice(itime).profiles_1d.psi')
    key of `.psi`   ('LEAF', 'equilibrium', 'dimension 1')
    the gate        False for both

and a figure opened on `.f` drew 101 points against `psi`, then drew `.psi`
against its index (101 points, 0 ... 100) and relabelled the figure's single
bottom axis `dimension 1` -- while the history the manual documents is 49 points
along 32,13 s ... 48,55 s.

What is pinned here is the single answer: an abscissa is an **identity**, the
figure settles it with its first curve and carries it, the read follows it, and a
quantity that cannot run along it is refused by name. Time first, because IMAS
spells the same clock three ways depending on
`ids_properties.homogeneous_time`: the dynamic array (`IDS.time`) at 1, the
coordinate `<aos>/time` at 0 -- and those are one abscissa, not two.

The stubs answer the identities and drive the figure; the last four tests take the
same answers from the reference case, so the shape a stub asserts is the shape a
real case draws. A stub holds its grid outside the arrays of structures, because
that is what the reader can walk: it descends a coordinate one name at a time and
indexes an array only when the runtime hands it an `IDSStructArray`. That is the
`core_profiles` shape -- `grid_1d.rho` names the axis of every `profiles_1d[i]`
leaf -- and the decorated spelling the reference case uses for `equilibrium`
(`time_slice(itime).profiles_1d.psi`) is pinned by the identity tests and by the
case tests, which read it whole.
"""

import pytest

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec
from imasviz.VizDataAccess.QVizCurveAbscissa import TIME
from imasviz.VizDataAccess.QVizCurveAbscissa import abscissae, choose, describe
from imasviz.VizDataAccess.QVizCurveAbscissa import normaliseCoordinate
from imasviz.VizDataAccess.QVizNodePlotting import QVizNodePlotting
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot

from support.fakes import FakeAxesNode
from support.ownership import keep

# One grid, named by the dictionary, shared by every leaf of the array. The
# decoration on a coordinate name says which element of which enclosing array it
# was read at, so it does not belong to the identity -- but the two leaves below
# are read under one name, and so answer one abscissa.
GRID = 'grid_1d.rho'


def _ids(homogeneousTime=0):
    """A `core_profiles` shape: one grid, a dynamic array of leaves, a clock.

    `homogeneous_time` is set, not implied: it is what decides whether the case
    spells its clock as `IDS.time` or under the array that carries the quantity,
    and the two spellings have to answer one abscissa all the same.
    """
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = homogeneousTime
    ids.time = [32., 48.]
    ids.grid_1d = type(str('Grid'), (), {})()
    ids.grid_1d.rho = [0., 1., 2.]
    ids.profiles_1d = []
    for index, moment in enumerate((32., 48.)):
        element = type(str('Slice'), (), {})()
        element.time = None if homogeneousTime else moment
        element.density = [10. * (index + 1)] * 3
        element.temperature = [20. * (index + 1)] * 3
        element.ip = 100. + index
        ids.profiles_1d.append(element)
    return ids


def _leaf(name, coordinate=GRID, coordinateUnits='m'):
    """One 1D leaf of the dynamic array, sampled on one named grid."""
    return FakeAxesNode(_ids(), 'foo', 'foo.profiles_1d[itime]', 'FLT_1D',
                        name=name, itimeIndex=0, coordinates=(coordinate,),
                        coordinateUnits={1: coordinateUnits},
                        indices={'i': '0'}, lengths={'i': '2'})


def _scalarInTime():
    """A scalar held by the dynamic array: no axis of its own but the clock."""
    return FakeAxesNode(_ids(), 'foo', 'foo.profiles_1d[itime]', 'FLT_0D',
                        name='ip', itimeIndex=0, coordinates=(),
                        indices={'i': '0'}, lengths={'i': '2'})


def _leafOnAnUnnamedAxis(units=None):
    """A leaf whose axis the dictionary leaves unbounded, so `1..N`."""
    return FakeAxesNode(_ids(), 'foo', 'foo.profiles_1d[itime]', 'FLT_1D',
                        name='psi', itimeIndex=0, coordinates=('1..N',),
                        coordinateUnits=({1: units} if units else {}),
                        indices={'i': '0'}, lengths={'i': '2'})


def _leafTimedByItsOwnCoordinate():
    """A 1D leaf whose own coordinate *is* a time base.

    The reference case spells it `magnetics.flux_loop(i1).flux.time`: at
    `homogeneous_time == 1` the quantity sits under a static array and its axis
    is spelled as a coordinate ending in `time`, not as the dynamic array. Same
    clock, other spelling.
    """
    ids = _ids(homogeneousTime=1)
    ids.flux = type(str('Flux'), (), {})()
    ids.flux.time = [32., 48.]
    ids.flux.data = [7., 9.]
    return FakeAxesNode(ids, 'foo', 'foo.flux', 'FLT_1D', name='data',
                        coordinates=('flux.time',), coordinateUnits={1: 's'},
                        alongTime=False)


def _axes(node):
    return QVizAxesSpec.fromTreeNode(node)


def bottom(figure):
    return figure.pgPlotWidget.getAxis('bottom').labelText


def plotted(figure, index=0):
    x, y = figure.curves()[index].getData()
    return list(x), list(y)


@pytest.fixture
def figure(qtbot):
    widget = QVizCurvePlot(title='Figure:1')
    qtbot.addWidget(widget)
    return widget


# -- an abscissa is an identity, not a spelling ---------------------------------

def test_the_two_imas_spellings_of_one_clock_are_one_absissa():
    """The dynamic array's base and a `<aos>/time` coordinate name one axis.

    `homogeneous_time` decides which spelling a case uses, so two quantities of
    one shot can spell their clock differently. Keyed apart, a quantity read
    along one is refused from a figure drawing the other -- the refusal this
    module exists to remove.
    """
    assert abscissae(_axes(_scalarInTime())) == [TIME]
    assert abscissae(_axes(_leafTimedByItsOwnCoordinate())) == [TIME]
    assert describe(TIME) == 'time'


def test_a_quantity_on_the_clock_and_one_in_the_dynamic_array_share_it():
    """Refusing this pair is symptom one: no way to add a curve along time."""
    assert choose(_axes(_leaf('density')), TIME) == TIME
    assert choose(_axes(_leafTimedByItsOwnCoordinate()), TIME) == TIME


def test_the_loop_decoration_of_a_coordinate_is_not_part_of_its_identity():
    """`time_slice(itime).profiles_1d.psi` names one grid, decoration aside.

    The decoration says which element of which enclosing array the coordinate
    belongs to; the shadow tree spells the same road with slashes and the tree
    node with dots, and neither says which axis the grid is.
    """
    assert normaliseCoordinate('time_slice(itime).profiles_1d.psi') == \
        'time_slice.profiles_1d.psi'
    assert normaliseCoordinate('time_slice[itime]/profiles_1d/psi') == \
        'time_slice.profiles_1d.psi'
    assert normaliseCoordinate('flux_loop(i1).flux.time') == 'flux_loop.flux.time'
    assert normaliseCoordinate('foo/grid_1d/rho', 'foo') == 'grid_1d.rho'


def test_two_leaves_of_one_array_answer_one_absissa():
    """The pair the user could not put in one figure, at the identity level."""
    assert abscissae(_axes(_leaf('density'))) == \
        abscissae(_axes(_leaf('temperature')))
    grid = ('coordinate', GRID.replace('grid_1d', 'grid_1d'))
    assert choose(_axes(_leaf('temperature')), grid) == grid


def test_an_axis_the_dictionary_leaves_unnamed_is_keyed_by_its_units():
    """`1..N` names no node, so what two such axes can share is their unit.

    Measured on the reference case: `.psi` declares `1...N` and no unit, and what
    the read draws under it is the element rank -- the same numbers whatever the
    structure, so two of them are one abscissa. A named grid stays a different
    abscissa from an unnamed one: the numbers under it are not the same numbers.
    """
    unnamed = abscissae(_axes(_leafOnAnUnnamedAxis()))
    named = abscissae(_axes(_leaf('density')))
    assert unnamed == [TIME, ('dimension', '')]
    assert named == [TIME, ('coordinate', 'grid_1d.rho')]
    assert choose(_axes(_leafOnAnUnnamedAxis()), named[1]) is None
    assert choose(_axes(_leaf('density')), unnamed[1]) is None
    assert choose(_axes(_leafOnAnUnnamedAxis()), TIME) == TIME
    assert describe(unnamed[1]) == 'its index'
    assert abscissae(_axes(_leafOnAnUnnamedAxis('m')))[1] != \
        abscissae(_axes(_leafOnAnUnnamedAxis('s')))[1]


def test_a_quantity_of_two_axes_of_its_own_offers_no_curve_absissa():
    """That is a picture and not a curve, and the frame routing says so."""
    leaf = FakeAxesNode(_ids(), 'foo', 'foo.profiles_1d[itime]', 'FLT_2D',
                        name='matrix', itimeIndex=0,
                        coordinates=(GRID, '1..N'), coordinateUnits={1: 'm'},
                        indices={'i': '0'}, lengths={'i': '2'})
    assert QVizNodePlotting(leaf).curveAbscissae() == []
    assert choose(_axes(leaf), TIME) is None


# -- the figure settles its abscissa and carries it -----------------------------

@pytest.mark.ui
def test_a_fresh_figure_of_a_dynamic_quantity_runs_along_time(figure):
    """What the plain entry draws on a quantity of the dynamic array.

    Not a taste: the manual plots **equilibrium.time_slice[0].profiles_1d.f**
    through :guilabel:`Plot ... -> figure -> New` and states the result -- X is
    ``equilibrium.time``, Y is ``profiles_1d.f[0]`` over all the time slices
    (*Plotting 1D arrays as a function of time*). Measured before the change, the
    same entry drew 101 points against `psi` on that leaf, because the frame
    carried `plotAxis = 'DEFAULT'` and the legacy rule answered
    `is1DAndDynamic() -> False` for a 1D quantity. That is the user's second
    complaint: the spatial coordinate taken as X instead of the clock.
    """
    figure.plot(_leaf('density'))
    assert figure.abscissa == TIME
    assert bottom(figure) == 'time'
    assert plotted(figure) == ([32., 48.], [10., 20.])


@pytest.mark.ui
def test_the_coordinate_entry_runs_the_same_quantity_along_its_grid(figure):
    """The other documented entry, and the abscissa it settles."""
    figure.plot(_leaf('density'), as_function_of_time=False)
    assert figure.abscissa == ('coordinate', 'grid_1d.rho')
    assert describe(figure.abscissa) == 'grid_1d.rho'
    assert bottom(figure) == 'rho'
    assert plotted(figure)[0] == [0., 1., 2.]


@pytest.mark.ui
def test_a_second_trace_is_read_along_the_absissa_of_the_figure(figure):
    """Symptom two: the added curve took its own axis, not the figure's.

    Measured before on the reference case: `.f` drew 101 points against `psi`,
    then `.psi` drew 101 points against its index in the same figure. Here the
    figure runs along time, so both traces carry the two time slices -- and the
    grid points are what the figure leaves out.
    """
    figure.plot(_leaf('density'), as_function_of_time=True)
    figure.plot(_leaf('temperature'))
    assert [len(x) for x, _ in (plotted(figure, 0), plotted(figure, 1))] == [2, 2]
    assert plotted(figure, 0)[1] == [10., 20.]
    assert plotted(figure, 1)[1] == [20., 40.]
    assert bottom(figure) == 'time'


@pytest.mark.ui
def test_the_bottom_label_is_not_rewritten_by_a_later_trace(figure):
    """The figure has one bottom label, so the first curve gets to name it."""
    figure.plot(_leaf('density'), as_function_of_time=False)
    settled = bottom(figure)
    figure.plot(_leaf('temperature'))
    assert bottom(figure) == settled == 'rho'


@pytest.mark.ui
def test_a_scalar_in_the_dynamic_array_joins_a_history_by_its_clock(figure):
    figure.plot(_leaf('density'), as_function_of_time=True)
    figure.plot(_scalarInTime())
    assert plotted(figure, 1) == ([32., 48.], [100., 101.])


@pytest.mark.ui
def test_a_quantity_that_cannot_follow_the_figure_is_refused_by_name(figure):
    """Both sides are named: what the figure draws, and what this one runs along."""
    figure.plot(_leaf('density'), as_function_of_time=False)
    with pytest.raises(ValueError) as refused:
        figure.plot(_leafTimedByItsOwnCoordinate())
    message = str(refused.value)
    assert 'foo.flux.data' in message
    assert 'grid_1d.rho' in message
    assert 'it runs along time' in message


@pytest.mark.ui
def test_a_history_figure_keeps_reading_the_traces_it_already_has(figure):
    """A slider re-reads a trace along the abscissa it was drawn on.

    Each row carries its own abscissa for that reason: a figure cannot re-read
    one curve along its quantity's default and the next along its own.
    """
    figure.plot(_leaf('density'), as_function_of_time=True)
    assert [trace.abscissa for trace in figure.traces()] == [TIME]
    figure.refresh()
    assert plotted(figure)[1] == [10., 20.]


@pytest.mark.ui
def test_a_scalar_held_by_a_static_array_joins_the_figure_it_is_added_to(figure):
    """No axis of its own, so the figure's abscissa is the only one it can have.

    The value is then spread over that axis, and the read says so in the log of
    the case: a flat line is one value, not a measurement. Refused on an empty
    figure, where there is nothing to spread it over.
    """
    from support.fakes import FakeAxesNode

    ids = _ids()
    ids.gap = []
    for value in (7., 9.):
        element = type(str('Gap'), (), {})()
        element.value = value
        ids.gap.append(element)
    held = FakeAxesNode(ids, 'foo', 'foo.gap[i]', 'FLT_0D', name='value',
                        coordinates=(), indices={'i': '1'}, lengths={'i': '2'},
                        alongTime=False)
    assert abscissae(_axes(held)) == []

    with pytest.raises(ValueError) as refused:
        figure.plot(held)
    assert 'value' in str(refused.value)
    assert figure.curveCount() == 0

    figure.plot(_leaf('density'), as_function_of_time=False)
    assert figure.plot(held) == 1
    assert plotted(figure, 1) == ([0., 1., 2.], [9., 9., 9.])


# -- the gate the two menus ask -------------------------------------------------

def test_the_gate_asks_the_figure_and_not_a_spelling(qtbot):
    """One open figure, one answer per quantity -- asked of what the figure draws."""
    from imasviz.Viz_API import Viz_API

    history = keep(QVizCurvePlot(title='SlicesPlot1'))
    history.figureKey = 'SlicesPlot1'
    history.plot(_leaf('density'), as_function_of_time=True)
    api = Viz_API()
    api.figureframes[history.figureKey] = history

    assert api.figureDrawsSameCurveAxis('SlicesPlot1', _leaf('temperature'))
    assert api.figureDrawsSameCurveAxis('SlicesPlot1', _leafOnAnUnnamedAxis())
    assert api.figureDrawsSameCurveAxis('SlicesPlot1',
                                        _leafTimedByItsOwnCoordinate())
    assert api.figureDrawsSameCurveAxis('SlicesPlot1', _scalarInTime())

    profile = keep(QVizCurvePlot(title='SlicesPlot2'))
    profile.figureKey = 'SlicesPlot2'
    profile.plot(_leaf('density'), as_function_of_time=False)
    api.figureframes[profile.figureKey] = profile
    assert api.figureDrawsSameCurveAxis('SlicesPlot2', _leaf('temperature'))
    assert not api.figureDrawsSameCurveAxis('SlicesPlot2',
                                            _leafTimedByItsOwnCoordinate())
    assert not api.figureDrawsSameCurveAxis('SlicesPlot2',
                                            _leafOnAnUnnamedAxis())
    # A quantity with no axis of its own is the one thing that always fits: it has
    # no abscissa to disagree with, so it is spread over the one the figure draws.
    assert api.figureDrawsSameCurveAxis('SlicesPlot2', _scalarInTime())


def test_the_curve_frame_carries_no_axis_spelling_any_more(qtbot):
    """The string the read used to fall back on is gone with the reading.

    The table and the stacked window still answer `plotAxis`: their menu entries
    are documented as *New (default axis)* and *New ('TIME' axis)*, and one
    abscissa is chosen for a whole selection there. A curve figure answers an
    identity instead, so a second vocabulary for the same question cannot come
    back.
    """
    frame = keep(QVizCurvePlot(title='Figure:1'))
    assert not hasattr(frame, 'plotAxis')
    assert not hasattr(frame, 'getPlotAxis')
    assert not hasattr(frame, 'setPlotAxis')


def test_the_answer_is_asked_once_and_not_reimplemented():
    """The key the menus compared by spelling is gone from the classes.

    `curveAxisKey` answered a string off the axes and the gate compared two of
    them, which is how two leaves of one structure came to name two abscissae.
    What is left is `curveAbscissae`, which hands out identities for the same
    question the figure and the read answer.
    """
    assert not hasattr(QVizNodePlotting, 'curveAxisKey')
    assert not hasattr(QVizNodePlotting, 'curveAxis')
    assert hasattr(QVizNodePlotting, 'curveAbscissae')


# -- the same answers, taken from the reference case ----------------------------

@pytest.fixture(scope='module')
def caseBundle(qapp, request):
    from support import caseTrees
    return caseTrees.loadCaseTrees(qapp, ['equilibrium', 'magnetics'],
                                   request=request)


def caseNode(bundle, idsName, text):
    """One leaf of the reference case, built the way the shot view builds it."""
    from conftest import CASE_DATA_DICTIONARY_VERSION, case_uri_or_skip
    from support import caseTrees as helper
    from support.fakes import FakeTreeView
    from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource

    uri = case_uri_or_skip()
    for element, path in helper.shadowTreePaths(bundle['trees'][idsName],
                                                idsName):
        if element.text != text or element.get('parametrizedPath') is None:
            continue
        view = FakeTreeView(uri=uri)
        view.dataSource = QVizIMASDataSource('west 54924', uri)
        view.dataSource.dd_version = CASE_DATA_DICTIONARY_VERSION
        return helper.nodeAsTheBuilderBuildsIt(element, idsName,
                                               bundle['runtime'][idsName], view,
                                               path=path)
    raise AssertionError('no leaf %r in the shadow tree of %s' % (text, idsName))


PROFILE = 'equilibrium.time_slice[i].profiles_1d.f'
GRID_LEAF = 'equilibrium.time_slice[i].profiles_1d.psi'
SCALAR = 'equilibrium.time_slice[i].global_quantities.ip'
# The homogeneous IDS spells the same clock as a coordinate of the leaf.
FLUX = 'magnetics.flux_loop[i].flux.data'


def idsOf(text):
    """Which of the two IDS walked here holds that leaf."""
    return 'magnetics' if text == FLUX else 'equilibrium'


@pytest.mark.case
def test_the_case_holds_the_two_spellings_of_its_clock(caseBundle):
    """`equilibrium` is inhomogeneous, `magnetics` homogeneous -- measured."""
    assert caseBundle['runtime']['equilibrium'].ids_properties.homogeneous_time == 0
    assert caseBundle['runtime']['magnetics'].ids_properties.homogeneous_time == 1

    profile = abscissae(_axes(caseNode(caseBundle, 'equilibrium', PROFILE)))
    flux = abscissae(_axes(caseNode(caseBundle, 'magnetics', FLUX)))
    # Time first, on both: `equilibrium` at homogeneous_time 0 spells its clock
    # as the dynamic array, `magnetics` at 1 as a coordinate of the leaf.
    assert profile == [TIME, ('coordinate', 'time_slice.profiles_1d.psi')]
    assert flux == [TIME]
    # The grid the case declares carries the loop decoration the identity takes
    # out; `.psi` itself declares `1...N` and no unit, which is why the two are
    # not one abscissa along the grid, and why both are one along time.
    assert abscissae(_axes(caseNode(caseBundle, 'equilibrium', GRID_LEAF))) == \
        [TIME, ('dimension', '')]


@pytest.mark.ui
@pytest.mark.case
def test_the_plain_entry_on_the_case_draws_the_history(caseBundle, qtbot):
    """What the manual says the plain entry draws, on the leaf it demonstrates.

    The manual's own walkthrough is **equilibrium.time_slice[0].profiles_1d.f**
    plotted to a new figure: X is `equilibrium.time`. Measured before the change,
    that entry drew 101 points against `psi` and labelled the bottom axis `psi`,
    then 101 more against the index when a second quantity joined -- 49 points
    along 32,13 s ... 48,55 s is what the case holds for the clock.
    """
    frame = keep(QVizCurvePlot(title='default'))
    frame.plot(caseNode(caseBundle, 'equilibrium', PROFILE))

    assert frame.abscissa == TIME
    assert bottom(frame) == 'time'
    assert len(plotted(frame)[0]) == 49
    assert plotted(frame)[0][0] == pytest.approx(32.1336784362793)


@pytest.mark.ui
@pytest.mark.case
def test_the_case_draws_every_trace_of_a_history_along_time(caseBundle, qtbot):
    """49 points at 32,13 s ... 48,55 s for all three leaves of one IDS.

    Measured before the change: the second trace of such a figure carried 101
    points against its index, and the figure's bottom label ended up naming it.
    """
    frame = keep(QVizCurvePlot(title='history'))
    frame.plot(caseNode(caseBundle, 'equilibrium', SCALAR), as_function_of_time=True)
    for text in (PROFILE, GRID_LEAF):
        frame.plot(caseNode(caseBundle, 'equilibrium', text))

    assert bottom(frame) == 'time'
    assert [len(x) for x, _ in (plotted(frame, index)
                                for index in range(frame.curveCount()))] == \
        [49] * 3
    first = plotted(frame)[0]
    assert first[0] == pytest.approx(32.1336784362793)
    assert first[-1] == pytest.approx(48.54828643798828)


@pytest.mark.ui
@pytest.mark.case
def test_a_figure_of_the_case_refuses_what_it_cannot_read(caseBundle, qtbot):
    """Asked for its grid instead of the clock, the figure keeps that grid.

    Both the abscissa and the label come from the first curve. A quantity of
    another IDS, read along its own clock, is refused for the figure it cannot
    follow -- and named, along with what both run along. The scalar of the same
    IDS is not refused: it has no axis of its own, so the figure's grid is the
    only abscissa it can have, and the read says in the log that the line is one
    value spread over it.
    """
    frame = keep(QVizCurvePlot(title='profile'))
    frame.plot(caseNode(caseBundle, 'equilibrium', PROFILE),
               as_function_of_time=False)
    assert frame.abscissa == ('coordinate', 'time_slice.profiles_1d.psi')
    assert len(plotted(frame)[0]) == 101
    assert bottom(frame) == 'psi'

    with pytest.raises(ValueError) as refused:
        frame.plot(caseNode(caseBundle, 'magnetics', FLUX))
    message = str(refused.value)
    assert 'magnetics.flux_loop[i].flux.data' in message
    assert 'time_slice.profiles_1d.psi' in message
    assert 'it runs along time' in message
    assert bottom(frame) == 'psi'

    assert frame.plot(caseNode(caseBundle, 'equilibrium', SCALAR)) == 1
    values = plotted(frame, 1)[1]
    assert len(values) == 101
    assert len(set(values)) == 1


@pytest.mark.case
def test_the_case_offers_the_grid_leaf_to_a_history_and_not_to_a_profile(caseBundle):
    """The gate answers with the figure, on numbers the case itself drew."""
    from imasviz.Viz_API import Viz_API

    api = Viz_API()
    history = keep(QVizCurvePlot(title='SlicesPlot1'))
    history.figureKey = 'SlicesPlot1'
    history.plot(caseNode(caseBundle, 'equilibrium', SCALAR), as_function_of_time=True)
    api.figureframes[history.figureKey] = history
    for text in (PROFILE, GRID_LEAF, FLUX, SCALAR):
        assert api.figureDrawsSameCurveAxis(
            'SlicesPlot1', caseNode(caseBundle, idsOf(text), text)), text

    profile = keep(QVizCurvePlot(title='SlicesPlot2'))
    profile.figureKey = 'SlicesPlot2'
    profile.plot(caseNode(caseBundle, 'equilibrium', PROFILE),
                 as_function_of_time=False)
    api.figureframes[profile.figureKey] = profile
    for text in (PROFILE, SCALAR):
        assert api.figureDrawsSameCurveAxis(
            'SlicesPlot2', caseNode(caseBundle, 'equilibrium', text)), text
    for text in (GRID_LEAF, FLUX):
        assert not api.figureDrawsSameCurveAxis(
            'SlicesPlot2', caseNode(caseBundle, idsOf(text), text)), text
