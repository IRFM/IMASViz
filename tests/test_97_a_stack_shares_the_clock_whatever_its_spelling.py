# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A Stacked Plot View shares the one clock, whatever its spelling.

The user's report, measured on the reference case before the change: the
selection `magnetics.flux_loop[0].flux.data` + `magnetics.bpol_probe[0].field.data`
is refused by a Stacked Plot View with

    "magnetics.bpol_probe[i].field.data" is read along time, not time:
    a stacked window draws every panel against the abscissa of the first
    quantity read. TablePlotView is the window for quantities that do not
    agree.

in **both** entries (`New ('TIME' axis)` and `New (default axis)`), while the
Table Plot View draws the two panels and a figure of curves draws the two
traces of the pair (test_59: `flux_loop(0)/flux/data` then
`bpol_probe(0)/field/data`, two colours, **17 344** points each).

What the tree answers for the two nodes, measured: `itime_index` is **-1** for
both (no array of structures carries the time index), `dynamicArrayAxis`
answers **None** for both, and each quantity is sampled along its **own
coordinate, which is a time base spelled under the structure that carries it**
-- `flux_loop(i1).flux.time` for the first, `bpol_probe(i1).field.time` for
the second, units `s`. The read (homogeneous_time 1) resolves both spellings
to `magnetics.time`. Two spellings of the one clock -- and the panel answered
them by their raw coordinate (two different keys, one name `time`), which is
how the window refused what every other figure of the application draws.

Pinned after the change:

* on the case, both entries draw the **2** panels, **17 344** samples each,
  on the same clock, the abscissa named `time`;
* on stubs of the measured shape -- a static array of structures, a 1D leaf
  whose own coordinate is a time base spelled under the structure -- the pair
  is taken by the column in both entries, while a quantity on a coordinate
  that is not the clock is still refused, named by its identity and pointed
  at the Table Plot View;
* the consistency: the panel answers the identity the curve figure uses
  (`QVizCurveAbscissa`'s `TIME`) for a clock spelled as a coordinate, so the
  two windows cannot answer differently for the same pair, and two different
  identities can no longer spell the same word in a refusal.
"""

import numpy as np
import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMdiArea

from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsStacked \
    import QVizPlotAsStacked
from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec
from imasviz.VizDataAccess.QVizCurveAbscissa import (TIME, choose,
                                                     dynamicArrayAxis,
                                                     identityOf)
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPanel import QVizPanel
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizStackedPlot import QVizStackedPlot
from imasviz.VizUtils import QVizPreferences

from conftest import CASE_DATA_DICTIONARY_VERSION, case_uri_or_skip
from support import ownership
from support.fakes import FakeAxesNode

TIMES = [0., 1., 2., 3., 4.]
LOOP_SAMPLES = [10. * t for t in TIMES]
PROBE_SAMPLES = [100. * t + 1. for t in TIMES]
POSITIONS = [0., 1., 2., 3.]

IDS_NAME = 'magnetics'
FIRST = 'magnetics/flux_loop(0)/flux/data'
SECOND = 'magnetics/bpol_probe(0)/field/data'
# The clock the read resolves the two spellings to, measured.
CLOCK_SAMPLES = 17344


def _stubIds(arrayName, innerName, values,
             coordinateName=None, coordinateValues=None):
    """The measured shape of the case: a static array, a structure, a 1D leaf.

    The dictionary keeps a per-structure `time` node under the structure
    (unfilled in the case): the leaf's own coordinate is that node, spelled
    `array(i1).inner.time`, and the axis it names is the IDS's `time` base.
    A coordinate that is not the clock is a node of the IDS the read descends
    to for its values.
    """
    ids = type(str('StubIds'), (), {})()
    props = type(str('Props'), (), {})()
    props.homogeneous_time = 1
    ids.ids_properties = props
    ids.time = list(TIMES)
    inner = type(str('Inner'), (), {})()
    inner.data = list(values)
    inner.time = []
    element = type(str('Element'), (), {})()
    setattr(element, innerName, inner)
    element.index = 1.
    setattr(ids, arrayName, [element])
    if coordinateName is not None:
        setattr(ids, coordinateName, list(coordinateValues))
    return ids


def node(arrayName, innerName, coordinate, values,
         coordinateName=None, coordinateValues=None, units='V'):
    """A 1D leaf under a static array of structures, as the case holds it.

    No array carries the time index (`itime_index` is -1 on both of the
    user's nodes), the leaf is 1D, its own coordinate is the one above.
    """
    ids = _stubIds(arrayName, innerName, values,
                   coordinateName=coordinateName,
                   coordinateValues=coordinateValues)
    return FakeAxesNode(
        idsRef=ids,
        idsName='foo',
        parametrizedPath='foo.' + arrayName + '[i].' + innerName,
        dataType='FLT_1D',
        name='data',
        itimeIndex=-1,
        coordinates=(coordinate,),
        indices={'i': '0'},
        lengths={'i': '1'},
        units=units,
        coordinateUnits={1: 's'},
        infoDict={'Path': 'foo/' + arrayName + '(i)/' + innerName +
                  '/data',
                  'occurrence': 0,
                  'name': 'data'},
        timeIndex=0,
        alongTime=False)


# The two spellings of the one clock, in the shape the case holds them.
FLUX = node('flux_loop', 'flux', 'flux_loop(i1).flux.time', LOOP_SAMPLES)
PROBE = node('bpol_probe', 'field', 'bpol_probe(i1).field.time',
             PROBE_SAMPLES)
# A coordinate that is not the clock: still a different abscissa.
POSITION = node('flux_loop', 'offset', 'loop_position', POSITIONS,
                coordinateName='loop_position', coordinateValues=POSITIONS)


@pytest.fixture
def view(qapp):
    """One shot view with a selection, and the api its figures register to.

    The shape of the selection entry the commands read comes from (test_37):
    the key is the parametrized data path, and the entry carries the uri.
    """

    class FakeSource(QObject):
        def __init__(self, uri):
            super().__init__()
            self.uri = uri
            self.name = 'NATIVE'

        def dataKey(self, treeNode):
            return treeNode.getParametrizedDataPath()

    class FakeView(QObject):
        def __init__(self):
            super().__init__()
            self.uri = 'imas:hdf5?case=97'
            self.dataSource = FakeSource(self.uri)
            self.selectedItem = None
            self.selectedSignalsDict = {}
            self.signalsList = []

    shot = FakeView()
    shot.mdi = QMdiArea()
    shot.imas_viz_api = Viz_API(parent=shot.mdi)
    shot.imas_viz_api.DTVlist = [shot]
    return shot


def select(view, *nodes):
    view.selectedSignalsDict = {n.getParametrizedDataPath():
                                {'index': index,
                                 'QTreeWidgetItem': n,
                                 'uri': view.dataSource.uri}
                                for index, n in enumerate(nodes)}
    view.selectedItem = nodes[0] if nodes else None
    view.signalsList = list(nodes)
    return view


def entry(view):
    return QVizSignalHandling(dataTreeView=view,
                              treeNode=view.selectedItem)


def stacks(view):
    return [frame for frame in view.imas_viz_api.figureframes.values()
            if isinstance(frame, QVizStackedPlot)]


def panelData(frame, index=0):
    x, y = frame.panels()[index].curves()[0].getData()
    return np.asarray(x), np.asarray(y)


def dropAllFigures(view):
    """The *Delete* line of the *Windows* menu, which the frame answers.

    The command showed the window, so a test that forgets it without taking it
    off the screen leaves a shown plot in the paint queue -- the hazard the
    ownership guard of the suite exists for. `DeleteFigure` goes through
    `closeWindow`: the window hides, leaves the queue, and goes.
    """
    for key in list(view.imas_viz_api.figureframes):
        view.imas_viz_api.DeleteFigure(key)


# ---------------------------------------------------------------------------
# The two spellings of the one clock are one abscissa, under either entry.

@pytest.mark.ui
def test_two_time_bases_are_one_abscissa_under_the_time_entry(view, caplog):
    select(view, FLUX, PROBE)

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='TIME')

    frame = stacks(view)[0]
    assert frame.panelCount() == 2
    assert frame.abscissaName() == 'time'
    np.testing.assert_allclose(panelData(frame, 0)[0], TIMES)
    np.testing.assert_allclose(panelData(frame, 0)[1], LOOP_SAMPLES)
    np.testing.assert_allclose(panelData(frame, 1)[0], TIMES)
    np.testing.assert_allclose(panelData(frame, 1)[1], PROBE_SAMPLES)
    assert 'is read along' not in caplog.text


@pytest.mark.ui
def test_two_time_bases_are_one_abscissa_under_the_default_entry(view, caplog):
    # The default entry left the reading of each quantity to itself; both
    # readings run along their own time base, and it is the same base, so the
    # column holds them under either entry.
    select(view, FLUX, PROBE)

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='DEFAULT')

    frame = stacks(view)[0]
    assert frame.panelCount() == 2
    assert frame.abscissaName() == 'time'
    np.testing.assert_allclose(panelData(frame, 1)[0], TIMES)
    assert 'is read along' not in caplog.text


@pytest.mark.ui
def test_a_quantity_off_the_clock_is_still_refused_and_named(view, caplog):
    # The fix unifies the spellings of the clock; a coordinate that is not
    # the clock stays a different abscissa, refused and pointed at the Table
    # Plot View as before, named by an identity that cannot share a word with
    # the one the window draws.
    select(view, FLUX, POSITION)

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='TIME')

    frame = stacks(view)[0]
    assert frame.panelCount() == 1
    assert 'loop_position' in caplog.text
    assert 'not time' in caplog.text
    assert 'TablePlotView' in caplog.text
    assert 'is read along loop_position' in caplog.text


# ---------------------------------------------------------------------------
# The panel answers the identity the curve figure already uses.

def test_the_panel_answers_the_curve_figure_identity_of_the_clock():
    # The measured pair, in stub shape: the two spellings answer one identity,
    # and it is the one the curve figure uses for them -- which is why the
    # figure of test_59 drew the pair while the stack refused it.
    for nodeLike in (FLUX, PROBE):
        spec = QVizAxesSpec.fromTreeNode(nodeLike)
        assert dynamicArrayAxis(spec) is None
        assert identityOf(spec.leafAxes()[0]) == TIME
        abscissa = QVizPanel.abscissaOf(spec, alongTime=False)
        assert abscissa[0] == TIME
        assert abscissa[1] == 'time'
        # The curve figure's own answer for the same pair: it takes it in.
        assert choose(spec, abscissa=TIME) == TIME


def test_a_walked_clock_answers_the_same_identity():
    # The clock walked by walking a dynamic array -- the world test_37's stubs
    # hold -- and the clock spelled as a coordinate: one identity either way,
    # so the column of the one and the figure of the other cannot drift apart
    # on the same pair.
    dynamic = FakeAxesNode(
        idsRef=_stubIds('time_slice', 'vector', LOOP_SAMPLES),
        idsName='foo',
        parametrizedPath='foo.time_slice[itime]',
        dataType='FLT_1D',
        name='data',
        itimeIndex=0,
        coordinates=('rho_tor',),
        indices={'i': '0'},
        lengths={'i': '5'},
        units='K',
        coordinateUnits={1: 'm'},
        infoDict={'Path': 'foo/time_slice(i)/data', 'occurrence': 0,
                  'name': 'data'},
        timeIndex=0,
        alongTime=True)
    walked = QVizPanel.abscissaOf(QVizAxesSpec.fromTreeNode(dynamic),
                                  alongTime=True)
    assert walked[0] == TIME
    assert walked[1] == 'time'

    off = QVizPanel.abscissaOf(QVizAxesSpec.fromTreeNode(POSITION),
                               alongTime=False)
    assert off[0] != TIME
    assert off[1] != 'time'


# ---------------------------------------------------------------------------
# The reference case, the pair the user selected: both entries draw it.

@pytest.fixture(scope='module')
def session(qapp):
    """One shot view of the reference case, with `magnetics` loaded in it.

    `qapp` is not decoration: the fixture builds a `QMainWindow`, and a Qt
    widget built before the `QApplication` exists aborts the process where it
    stands (test_59's fixture, the same one the case's pair is drawn on).
    """
    uri = case_uri_or_skip()
    if uri is None:
        pytest.skip('the reference case is not on disk')

    QVizPreferences().build()
    api = Viz_API()
    source = QVizDataSourceFactory().create(uri)
    source.dd_version = CASE_DATA_DICTIONARY_VERSION
    frame = api.CreateDataTree(source)
    view = frame.dataTreeView
    # The view and its api are what holds the loaded occurrence alive.
    ownership.keep(api)
    ownership.keep(view)
    ownership.keep(frame)
    QVizLoadOccurrence(dataTreeView=view, idsName=IDS_NAME,
                       occurrence=0, asynch=False).execute()
    return {'view': view, 'api': api,
            'nodes': {node.getPath(): node for node in view.signalsList}}


@pytest.mark.case
@pytest.mark.ui
def test_the_case_pair_shares_the_stack_under_both_entries(session, caplog):
    view = session['view']
    api = session['api']
    first = session['nodes'][FIRST]
    second = session['nodes'][SECOND]

    # The spellings that cost the user the refusal, and no others: no array of
    # structures carries the time index (the node holds `-1`, spelled the way
    # the parser writes it), and the leaf's own coordinate is a time base
    # spelled under the structure that carries it.
    assert first.getItimeIndex() == -1
    assert second.getItimeIndex() == -1
    assert first.coordinates == ['flux_loop(i1).flux.time']
    assert second.coordinates == ['bpol_probe(i1).field.time']

    for plotAxis in ('TIME', 'DEFAULT'):
        select(view, first, second)
        frame = QVizPlotAsStacked(dataTreeView=view, plotAxis=plotAxis).execute()
        assert frame.panelCount() == 2
        assert frame.abscissaName() == 'time'
        x0 = np.asarray(frame.panels()[0].curves()[0].getData()[0])
        x1 = np.asarray(frame.panels()[1].curves()[0].getData()[0])
        assert len(x0) == CLOCK_SAMPLES
        assert len(x1) == CLOCK_SAMPLES
        # Both panels stand on the same clock, whichever entry drew them.
        np.testing.assert_equal(x0, x1)
        dropAllFigures(view)
        del frame
    assert 'is read along' not in caplog.text
