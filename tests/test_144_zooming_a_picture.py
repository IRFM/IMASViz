# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The zoom of the window that holds pictures, and the gesture that answers each half of it.

Reported, in the user's own words: « si l'utilisateur demande un zoom (temporel)
d'une image, l'agent ne sait pas le faire et tente des appels mcp qui échouent.
Un exemple est l'ids soft_x_rays, le signal brightness, pour le choc 54924.
il n'est pas possible de réduire la fenêtre temporelle. »

The shape the report came from, drawn on the shot from ``test_80``, reads one
energy band over 6356 time samples per channel, as a window of pictures
across the channels the case holds: the abscissa of every picture is the
time the report wanted to shrink, and before this file nothing addressed
either half -- ``set_axis_range`` refused the picture window (its layout
carries no ``getViewBox()`` the gesture can reach), no gesture took the
window the pictures sit on, and the band of sliders had no row to pose.
The three that answer it now:

* **the span of the pictures** -- ``set_axis_range`` takes the picture window
  in: the same span pinned on the axis set of **each** of its pictures (the
  window is one scale and one span, so a time zoom of a strip whose abscissa
  is its time is the ``x`` range, in the seconds its time axis holds), and
  ``auto=True`` takes the span off, on all of them. The half pair is refused
  there as on the curves.
* **the window of pictures** -- ``set_image_window`` moves it (``start``: the
  pictures are re-read in place, the scale a hand settled stays, and the answer
  spells each picture the window shows, with the value the axis carries at it)
  and resizes it (``count``: the window rebuilds its pictures on its own start;
  a scale a hand put there comes back after, the one nobody touched settles
  again over the pictures it holds now). In the GUI the same resize is the
  count box beside the start slider. Past the axis the bound holds: the extent
  of the axis, named, not a slip past it; a window not read across an axis
  holds one picture, not a window, and its refusal points at ``set_axis_range``.
* **the rows of the band** -- ``set_slice_index`` poses one of them, named, at
  an index in its extent (the window re-reads the one it is posed at; the
  answer is the state the band holds). The axis the window already shows is
  no row of the band: the refusal says so and points at ``set_image_window``;
  a row the band does not hold: the ones it does, named; an index past the
  extent: the bound that holds it.

The in-memory part keeps ``test_26``'s quantity (a 2D leaf under an enclosing
dynamic array, with and without a frames axis) on a core that holds no case;
the case part is the shot that reported it, ``soft_x_rays`` of WEST 54924,
driven through ``McpGuiCore`` the way ``test_137`` drives the curves.
"""

import numpy as np
import pytest

from imasviz.VizAgent.core import McpGuiCore
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot

import support.ownership as ownership

from support.fakes import FakeAxesNode

from conftest import CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip

# --------------------------------------------------------------------------
# The stubs, the same quantity test_26 holds in memory
# --------------------------------------------------------------------------

AOS, LEAF = 'AOS', 'LEAF'
TIME_SLICE = (AOS, 'foo', 'time_slice')
PROFILES_2D = (AOS, 'foo', 'profiles_2d')

RHO = [0., 1., 2., 3.]
THETA = [0., .25, .5, .75, 1.]
TIMES = [0., 1., 2., 3., 4.]
SLICES = 3
TREE_TIME = 1
TREE_SLICE = 2
WINDOW = [1, 2, 3]


def _psi_values(timeIndex, sliceIndex):
    """One 2D slice, every element carrying where in the quantity it sits."""
    return [[1000. * timeIndex + 100. * sliceIndex + 10. * radial + vertical
             for vertical in range(len(THETA))]
            for radial in range(len(RHO))]


def _psi_ids(times=TIMES):
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = list(times)
    ids.rho_tor = list(RHO)
    ids.theta_poloidal = list(THETA)
    ids.time_slice = []
    for timeIndex in range(len(times)):
        timeSlice = type(str('TimeSlice'), (), {})()
        timeSlice.time = None
        timeSlice.profiles_2d = []
        for sliceIndex in range(SLICES):
            element = type(str('Profiles2d'), (), {})()
            element.time = None
            element.psi = _psi_values(timeIndex, sliceIndex)
            timeSlice.profiles_2d.append(element)
        ids.time_slice.append(timeSlice)
    return ids


def _psi(times=TIMES):
    """The window quantity: three time slices, a band row of profiles_2d."""
    return FakeAxesNode(_psi_ids(times), 'foo',
                        'foo.time_slice[itime].profiles_2d[j]',
                        'FLT_2D', name='psi', units='Pa', itimeIndex=0,
                        coordinates=('rho_tor', 'theta_poloidal'),
                        coordinateUnits={1: 'm', 2: 'rad'},
                        indices={'i': str(TREE_TIME), 'j': str(TREE_SLICE)},
                        lengths={'i': str(len(times)), 'j': str(SLICES)})


def _matrix():
    """The single picture: a 2D leaf at IDS level, nothing to read across."""
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0.]
    ids.matrix = [[1., 2., 3.], [4., 5., 6.]]
    return FakeAxesNode(ids, 'foo', 'foo', 'FLT_2D', name='matrix',
                        coordinates=('1..N', '1..M'))


# --------------------------------------------------------------------------
# The stub core: no case, the frames registered the way test_122 does
# --------------------------------------------------------------------------


@pytest.fixture
def core(qtbot):
    """A core that holds no case, with the frames of this file registered.

    ``test_26`` builds the frames on its own; ``test_122`` registers a frame
    on a caseless core with ``api.figureframes[key] = frame``. Both at once:
    the frames are the real ``QVizImagePlot``, and the keys are the ones the
    gestures address them by.
    """
    session = McpGuiCore()

    window = QVizImagePlot(title='Image:1')
    qtbot.addWidget(window)
    window.plot(_psi())

    single = QVizImagePlot(title='Image:2')
    qtbot.addWidget(single)
    single.plot(_matrix())

    session.api.figureframes['Image1'] = ownership.keep(window)
    session.api.figureframes['Image2'] = ownership.keep(single)
    return {'core': session, 'window': window, 'single': single}


def _picture(figure, index=0):
    """The numbers actually on screen, one picture at a time (test_26's)."""
    return figure.images()[index].image


def _viewBox(figure, index=0):
    return figure.plotItems()[index].getViewBox()


def _xrange(vb):
    return [float(v) for v in vb.state['viewRange'][0]]


def _auto(vb):
    return bool(vb.state['autoRange'][0])


# --------------------------------------------------------------------------
# set_axis_range on the pictures, the half of the report it was refused on
# --------------------------------------------------------------------------


@pytest.mark.ui
def test_the_span_is_pinned_on_every_picture(core):
    """The report's ask, on the quantity it came from: a time zoom of a
    window is the `x` range, and it is pinned on each of the pictures the
    window shows -- the window is one scale and one span, so a span on one
    of them would be a question the other two answer differently."""
    session, window = core['core'], core['window']

    answer = session.set_axis_range('Image1', xmin=1., xmax=2.)
    assert answer['pinned'] is True
    assert answer['xRange'][0] <= 1. and answer['xRange'][1] >= 2.
    # On every picture, not just the first: the span the answer reports is
    # the one each of them sits on.
    for position in range(window.imageCount()):
        vb = _viewBox(window, position)
        assert vb.state['autoRange'][0] == 0, \
            'the pin left autoRange running on picture %d' % position
        assert _xrange(vb)[0] <= 1. and _xrange(vb)[1] >= 2., \
            'picture %d does not sit on the span the span was set to' % position


@pytest.mark.ui
def test_the_span_auto_takes_the_span_off_on_every_picture(core):
    session, window = core['core'], core['window']

    session.set_axis_range('Image1', xmin=1., xmax=2.)
    answer = session.set_axis_range('Image1', auto=True)
    assert answer['auto'] is True
    for position in range(window.imageCount()):
        assert _auto(_viewBox(window, position)), \
            'picture %d keeps the pin the auto ask took off' % position


@pytest.mark.ui
def test_the_span_of_a_single_picture_is_the_span_of_its_axes(core):
    """The reported shape, addressed by the gesture that answers it: a
    window of one picture pins on the axis it drew -- a 2D leaf at IDS level
    is one, and its x span is the one the strip's time axis carries."""
    session, single = core['core'], core['single']

    assert single.imageCount() == 1
    answer = session.set_axis_range('Image2', xmin=0., xmax=3.)
    assert answer['pinned'] is True
    vb = single.plotItems()[0].getViewBox()
    assert _xrange(vb)[0] <= 0. and _xrange(vb)[1] >= 3.
    session.set_axis_range('Image2', auto=True)


@pytest.mark.ui
def test_the_span_refuses_a_half_pair_on_a_picture_window(core):
    session = core['core']
    with pytest.raises(ValueError) as excinfo:
        session.set_axis_range('Image1', xmin=1.)
    assert 'together' in str(excinfo.value)


@pytest.mark.ui
def test_the_span_refuses_no_axis_name(core):
    session = core['core']
    with pytest.raises(ValueError) as excinfo:
        session.set_axis_range('Image1')
    assert 'at least one axis' in str(excinfo.value)


# --------------------------------------------------------------------------
# The shot that reported it: WEST 54924, soft_x_rays, the single-pictures strip
# --------------------------------------------------------------------------

STRIP_PATH = 'soft_x_rays/channel(0)/brightness/data'


@pytest.fixture(scope='module')
def strip_case(qapp, tmp_path_factory):
    """The reported shape, end to end, on the shot that reported it.

    The report's leaf, ``soft_x_rays/channel(0)/brightness/data``, is one
    energy band over 6356 time samples, and the figure it draws is a
    window of three pictures read across the 45 channels the case holds:
    time is the abscissa of each picture (the ``x`` span the report asked
    to shrink), the channels are on the window, and there is no band of
    sliders because the only other axis -- the band -- is drawn as the
    ordinate. The shape of each of the three gestures is pinned on the
    case the report was taken on.
    """
    uri = case_uri_or_skip()
    if uri is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)

    home = tmp_path_factory.mktemp('stripHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    session = McpGuiCore()
    try:
        session.open_case(uri, CASE_DATA_DICTIONARY_VERSION)
        session.load_ids(uri, 'soft_x_rays', 0)
        figure = session.plot_one(uri, STRIP_PATH)
        key = figure['figure']
        frame = session.api.figureframes[key]
        assert key.startswith('Image'), \
            'the strip is a picture; %r is not one' % key
        ownership.keep(frame)
        yield {
            'session': session, 'key': key, 'frame': frame,
            'uri': uri, 'home': home,
        }
    finally:
        patch.undo()


@pytest.mark.case
@pytest.mark.ui
def test_the_strip_time_zoom_is_the_x_span_of_each_picture(strip_case):
    """The report's ask, answered on the shape it took it on: the time
    is the abscissa of each picture, so a time zoom is the ``x`` span,
    in the seconds the axis holds -- pinned on every picture, because
    the window is one scale and one span, and the answer reports that
    one span. The times are read off the view the figure settled in,
    whatever the case holds at those samples: a sub-span of them is a
    zoom the report could ask and the answer reads back."""
    session, key, frame = strip_case['session'], strip_case['key'], strip_case['frame']

    lo, hi = _xrange(frame.plotItems()[0].getViewBox())
    assert hi > lo
    span_lo, span_hi = lo + (hi - lo) / 4., lo + 3. * (hi - lo) / 4.

    answer = session.set_axis_range(key, xmin=span_lo, xmax=span_hi)

    assert answer['pinned'] is True
    assert answer['xRange'][0] <= span_lo and answer['xRange'][1] >= span_hi
    for position in range(frame.imageCount()):
        viewbox = frame.plotItems()[position].getViewBox()
        assert viewbox.state['autoRange'][0] == 0, \
            'the span is not off the re-fit on picture %d' % position
        assert _xrange(viewbox)[0] <= span_lo and _xrange(viewbox)[1] >= span_hi, \
            'picture %d does not sit on the span the report asked for' % position
    # Back, the way a zoom is let go: the re-fit returns on every
    # picture at once, the window staying one scale and one span.
    restored = session.set_axis_range(key, auto=True)
    assert restored['auto'] is True
    for position in range(frame.imageCount()):
        assert bool(frame.plotItems()[position].getViewBox()
                    .state['autoRange'][0]), \
            'picture %d keeps the pin the auto ask took off' % position
