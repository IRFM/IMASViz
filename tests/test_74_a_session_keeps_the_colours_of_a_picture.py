# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A session keeps the colours of a picture window, and only what a hand left.

`test_73` pins the window: one map and one range, every picture, and what a hand
moving either leaves behind. `test_66` pins the file: a `<ColourScale>` written is a
`<ColourScale>` read, and one that cannot be put back is refused at the file. What
neither can pin is the promise those two exist for -- colour a picture this morning,
close the application, open the session tomorrow, and the picture is still that
colour over that range.

So everything here goes through the two commands. The scale is left the way a user
leaves it (a drag on the bar's handles, a name picked in the chooser), it is written
by `QVizSaveSession.scaleOf` off the live window, and it is put back by
`QVizRestoreSession.applyColourScale` on a window that never saw the first one --
the run the user comes back to, since the one they left is closed with the window.

Three refusals are worth more than the round trip, and all three are here:

* a map this node cannot draw. A session written on an install that reads
  matplotlib's 182 extra maps names a colour the next one has never heard of.
  `pyqtgraph` answers that with a `FileNotFoundError` naming a path under its own
  package, which is not a sentence about the user's picture -- so the name is
  logged, the window keeps the colours it opens with, and the **range still goes
  on**: two answers, and losing the number the user set because a colour is
  missing would hide the half that still means something;
* a window that holds no picture at all -- the file wrote a picture under that key
  and the case now draws curves there. Said in the log of the case, and nothing
  else about that window is touched;
* a window nobody dressed, which answers nothing. Since T33 every trace carries a
  pen and since this row every picture carries the map this node opens with, so a
  session describing either would freeze a default into the file: a case opened a
  month later would draw the colours of the day it was saved instead of the ones
  chosen for the contrast in *that* case.

The pictures are stubs, for the reason `test_73` gives: no reference case on this
checkout holds a filled rank-2 leaf outside the radiance of `test_28`, which is
where the same promises are checked on real values.
"""

import logging

import numpy as np
import pytest

from imasviz.VizGUI.VizConfigurations.QVizSessionFile import (
    COLOUR_SCALE_ATTRIBUTES, QVizSessionFigure, QVizSessionFile,
    QVizSessionQuantity, IMAGE)
from imasviz.VizGUI.VizGUICommands.VizSession.QVizRestoreSession \
    import QVizRestoreSession
from imasviz.VizGUI.VizGUICommands.VizSession.QVizSaveSession \
    import QVizSaveSession
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot
from imasviz.VizGUI.VizPlot.QVizColourScales import DEFAULT_MAP, mapNamed
from imasviz.Viz_API import Viz_API

from support.fakes import FakeAxesNode

THETA = [0., .25, .5, .75, 1.]
RHO = [0., 1., 2., 3.]
TIMES = [0., 1., 2., 3., 4.]
SLICES = 3
TREE_SLICE = 2

URI = 'imas:hdf5?case=1'
FIGURE_KEY = 'SlicesImage1'
ANOTHER_MAP = 'CET-L9'
# A map name this node cannot resolve: what a session written on an install that
# reads matplotlib's extra maps looks like on one that does not.
NOT_A_MAP = 'cet-plasma-2026'


def psi(timeIndex, sliceIndex):
    return [[1000. * timeIndex + 100. * sliceIndex + 10. * radial + vertical
             for vertical in range(len(THETA))]
            for radial in range(len(RHO))]


def _psi():
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = list(TIMES)
    ids.rho_tor = list(RHO)
    ids.theta_poloidal = list(THETA)
    ids.time_slice = []
    for timeIndex in range(len(TIMES)):
        timeSlice = type(str('TimeSlice'), (), {})()
        timeSlice.time = None
        timeSlice.profiles_2d = []
        for sliceIndex in range(SLICES):
            element = type(str('Profiles2d'), (), {})()
            element.time = None
            element.psi = psi(timeIndex, sliceIndex)
            timeSlice.profiles_2d.append(element)
        ids.time_slice.append(timeSlice)
    return FakeAxesNode(ids, 'foo', 'foo.time_slice[itime].profiles_2d[j]',
                        'FLT_2D', name='psi', units='Pa', itimeIndex=0,
                        coordinates=('rho_tor', 'theta_poloidal'),
                        coordinateUnits={1: 'm', 2: 'rad'},
                        indices={'i': '1', 'j': str(TREE_SLICE)},
                        lengths={'i': str(len(TIMES)), 'j': str(SLICES)})


class StubView:
    """The shot view a refusal is logged into -- a logger name, and nothing else."""

    uri = URI


def aRun():
    """An api of a run that never saw the window being put back.

    The command takes the session it restores into; `applyColourScale` asks it for
    nothing -- the window comes from the figure's key, and the file has already been
    read -- so an empty api is exactly the state of the run the user opens.
    """
    return Viz_API()


def aPictureWindow(qtbot, key=FIGURE_KEY):
    """A window of three pictures, drawn as the gesture draws it."""
    window = QVizImagePlot(title=key)
    qtbot.addWidget(window)
    window.plot(_psi())
    return window


def aFigure(scale):
    return QVizSessionFigure(key=FIGURE_KEY, kind=IMAGE,
                             quantities=[QVizSessionQuantity('foo/psi', 0, URI,
                                                             None, None)],
                             axis=None, tensor=True, scale=scale)


def dragBar(window, region=(900., 2400.)):
    window.colorBar.region.setRegion(region)
    return tuple(float(value) for value in window.colorBar.levels())


def mapOf(window):
    return [image.getColorMap().name for image in window.images()]


def levelsOf(window):
    return [tuple(float(value) for value in image.getLevels())
            for image in window.images()]


# ------------------------------------------------------------------ the save

@pytest.mark.ui
def test_a_picture_window_nobody_dressed_answers_no_scale(qtbot):
    """The map it draws with is a default of this node, not a choice of that user."""
    window = aPictureWindow(qtbot)

    assert QVizSaveSession.scaleOf(window) is None


@pytest.mark.ui
def test_a_dragged_range_is_written_and_the_colours_are_not(qtbot):
    window = aPictureWindow(qtbot)
    moved = dragBar(window)

    scale = QVizSaveSession.scaleOf(window)

    assert (scale.map, scale.low, scale.high) == (None,) + moved


@pytest.mark.ui
def test_a_chosen_map_is_written_and_the_range_is_not(qtbot):
    window = aPictureWindow(qtbot)

    window.colourScale.setColourMap(ANOTHER_MAP)

    scale = QVizSaveSession.scaleOf(window)
    assert scale.map == ANOTHER_MAP
    assert (scale.low, scale.high) == (None, None), \
        'a span nobody moved is the span the pictures settle on'


@pytest.mark.ui
def test_a_curve_figure_answers_no_colour_scale(qtbot):
    """A figure of curves dresses its traces one by one -- `QVizPlotStyling`'s
    question. It has no picture to colour, so the session is told nothing."""
    frame = QVizCurvePlot(title='SlicesPlot1')
    qtbot.addWidget(frame)

    assert QVizSaveSession.scaleOf(frame) is None


@pytest.mark.ui
def test_the_record_a_window_gives_is_the_record_the_file_writes(qtbot):
    """The other half of the seam `test_66` pins from the file's side.

    `state()` answers a three-part tuple and `scaleOf` lays it over the record the
    writer walks. Both halves are named here because the order is the only thing
    holding them together: a `(low, high, map)` answer would write a range as a map
    name, and the file would refuse it with a sentence about a name.
    """
    window = aPictureWindow(qtbot)
    moved = dragBar(window)
    window.colourScale.setColourMap(ANOTHER_MAP)

    scale = QVizSaveSession.scaleOf(window)

    assert scale._fields == COLOUR_SCALE_ATTRIBUTES
    assert (scale.map, scale.low, scale.high) == (ANOTHER_MAP,) + moved

    written = QVizSessionFile(cases=[], figures=[aFigure(scale)]).write(
        QVizSessionFile.named('picture'))

    assert QVizSessionFile.read(written).figures[0].scale == scale


# ---------------------------------------------------------------- the restore

@pytest.mark.ui
def test_the_colours_and_the_range_come_back_on_a_window_that_never_saw_them(qtbot):
    """The session the user comes back to, on a window drawn from scratch."""
    window = aPictureWindow(qtbot)
    moved = dragBar(window)
    window.colourScale.setColourMap(ANOTHER_MAP)
    scale = QVizSaveSession.scaleOf(window)
    other = aPictureWindow(qtbot, key='SlicesImage2')

    QVizRestoreSession(aRun()).applyColourScale(aFigure(scale), other, StubView())

    assert mapOf(other) == [ANOTHER_MAP] * 3
    assert levelsOf(other) == [moved] * 3
    assert other.colourLevels() == moved


@pytest.mark.ui
def test_a_replayed_scale_is_written_again_as_the_hand_it_stands_for(qtbot):
    """Otherwise the second close of the session loses what the first restore put
    back: a replay is a hand, and the file has to say the same thing twice."""
    window = aPictureWindow(qtbot)
    moved = dragBar(window)
    scale = QVizSaveSession.scaleOf(window)
    other = aPictureWindow(qtbot, key='SlicesImage2')

    QVizRestoreSession(aRun()).applyColourScale(aFigure(scale), other, StubView())

    again = QVizSaveSession.scaleOf(other)
    assert (again.map, again.low, again.high) == (None,) + moved


@pytest.mark.ui
def test_a_map_this_node_cannot_draw_is_named_and_the_range_still_goes_on(qtbot,
                                                                          caplog):
    """Two answers in one element, and one of them is still puttable.

    The name in the log is the name the file wrote -- not the `FileNotFoundError`
    of a path under pyqtgraph's package, which says nothing about the user's
    picture. And the window draws at the range the file named, with the colours it
    opens with: a missing colour is not a reason to lose the number.
    """
    window = aPictureWindow(qtbot)
    moved = dragBar(window)
    other = aPictureWindow(qtbot, key='SlicesImage2')
    caplog.set_level(logging.WARNING, logger=URI)

    QVizRestoreSession(aRun()).applyColourScale(
        aFigure(scale=_ScaleLike(map=NOT_A_MAP, low=moved[0], high=moved[1])),
        other, StubView())

    assert NOT_A_MAP in caplog.text
    assert mapOf(other) == [DEFAULT_MAP] * 3
    assert levelsOf(other) == [moved] * 3


@pytest.mark.ui
def test_a_window_that_draws_no_picture_says_which_figure_and_what_kind(qtbot,
                                                                       caplog):
    """A file that wrote a picture and now draws curves under that key.

    The key and the kind are both named because that is how the user knows which
    window to look at -- and the refusal costs nothing else: the window is drawn,
    its own state comes back from the rest of the file.
    """
    frame = QVizCurvePlot(title=FIGURE_KEY)
    qtbot.addWidget(frame)
    caplog.set_level(logging.WARNING, logger=URI)

    QVizRestoreSession(aRun()).applyColourScale(
        aFigure(scale=_ScaleLike(map=ANOTHER_MAP, low=1., high=2.)),
        frame, StubView())

    assert FIGURE_KEY in caplog.text and IMAGE in caplog.text
    assert 'no picture' in caplog.text
    assert not hasattr(frame, 'colourScale'), \
        'a figure of curves has no picture to colour, and no scale to be fooled by'


@pytest.mark.ui
def test_a_figure_naming_no_scale_costs_no_word_and_no_window(qtbot, caplog):
    """A version 4 file, or a picture nobody dressed: nothing to put back is not a
    failure to put something back."""
    window = aPictureWindow(qtbot)
    caplog.set_level(logging.WARNING, logger=URI)

    QVizRestoreSession(aRun()).applyColourScale(aFigure(None), window, StubView())

    assert caplog.text == ''
    assert mapOf(window) == [DEFAULT_MAP] * 3


# ------------------------------------------------------------- the map itself

@pytest.mark.ui
def test_a_map_written_by_the_other_menu_is_still_resolved(qtbot):
    """pyqtgraph's own right-click menu on the bar reaches matplotlib's maps too.

    A name picked there is an honest name to read back when this node can resolve
    it, so this does not restrict the file to the 71 names of its own chooser -- it
    only says what happens when a node cannot.
    """
    from imasviz.VizGUI.VizPlot.QVizColourScales import isKnown

    extra = [name for name in ('viridis', 'plasma', 'cet_l', 'seismic')
             if isKnown(name)]

    assert 'viridis' in extra
    window = aPictureWindow(qtbot)
    for name in extra:
        window.colourScale.setColourMap(name)
        assert mapOf(window) == [name] * 3
        assert mapNamed(name).name == name


@pytest.mark.ui
def test_the_colours_of_a_replayed_window_are_the_colours_of_its_pictures(qtbot):
    """The map is not a property of the record: it is on every picture's lookup
    table, which is what the screen is painted from.

    Compared with what the window was drawn with rather than with a table built off
    the map by hand: `ImageItem` builds its own from the map, at its own size, and
    an assertion on that construction would be about pyqtgraph, not about the
    picture the user sees.
    """
    window = aPictureWindow(qtbot)
    before = [image.lut for image in window.images()]

    window.colourScale.setColourMap(ANOTHER_MAP)

    luts = [image.lut for image in window.images()]
    assert all(lut is not None for lut in luts)
    assert np.array_equal(luts[0], luts[2])
    assert not np.array_equal(luts[0], before[0]), \
        'the chosen map never reached the picture it was chosen for'


class _ScaleLike(object):
    """The three attributes `applyColourScale` asks of a record, no more.

    The file's own namedtuple would make these tests pass on a file that never
    existed; what the command asks is three names, and this answers exactly them.
    """

    def __init__(self, map=None, low=None, high=None):
        self.map = map
        self.low = low
        self.high = high
