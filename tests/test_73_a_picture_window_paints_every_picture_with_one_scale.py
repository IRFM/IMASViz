# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""One colour scale per picture window -- one map, one range, every picture.

A picture says nothing until something maps its values to colours. Before this
row, a window of three pictures handed pyqtgraph an array and a level range and
let the mapping fall to its default grey ramp; and the one element that was
supposed to say what the colours mean -- the colour bar -- was built
`interactive=False` and bound to **one** of the three images.

That second half is a defect that existed before any colour map was asked for,
and it is what most of this file pins. `ColorBarItem.setImageItem` replaces its
list on every call (`img_list = [weakref.ref(item) for item in img]`,
`ColorBarItem.py:194`), so calling it once per picture leaves the bar driving the
last one. Two consequences, both measured on 0.13.7 before this file was written:

* the bar was built with no `values`, so it took the levels off the one image it
  was bound to -- measured `(0.0, 15.0)` on a window whose scale is
  `(0.0, 215.0)`. The numbers beside the colour ramp were not the scale the
  pictures were drawn against, which is the one question a colour bar answers;
* `colorMapMenu` is **True** by default, so a right click on the bar already
  opened pyqtgraph's map list -- and `setColorMap` pushes the lookup table onto
  the bound images only. Measured on three pictures: `images luts [False, False,
  False]`, and after picking a map, one coloured picture and two greys. So the
  documented refusal of that menu was keeping a half-painted window off the
  screen rather than an honest one.

The other half is what the user asked for: false colour, chosen and kept. So the
default is `viridis` -- it ships here, it is uniform in perceptual distance and
legible to a colour-blind eye -- and the range is movable, because the only
person who knows which part of a radiance is worth separating is the one looking
at it. The range then **holds**: a window move re-reads the pictures against the
scale that is on screen, not against the min and max of what came in. Measured,
`setImage` without `levels` re-fits every picture to its own data -- a re-read of
a 20x20 slice answered `(0, 399)` over a window scaled to `(0, 215)`.

Nothing here opens a case: the stubs are the ones `test_26` draws its pictures
from, for the reason it gives (no reference case on this checkout holds a filled
rank-2 leaf outside the radiance of `test_28`).
"""

import weakref

import numpy as np
import pytest

from imasviz.VizGUI.VizPlot.QVizColourScaleUI import ENTRY
from imasviz.VizGUI.VizPlot.QVizColourScales import (DEFAULT_MAP, QVizImageColourScale,
                                                     colourScaleOf, mapNamed,
                                                     mapNames, restoreColourScale,
                                                     roundingFor)
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPreviewPlot import QVizPreviewPlot

from support.fakes import FakeAxesNode

THETA = [0., .25, .5, .75, 1.]
RHO = [0., 1., 2., 3.]
TIMES = [0., 1., 2., 3., 4.]
SLICES = 3
TREE_TIME = 1
TREE_SLICE = 2
WINDOW = [TREE_TIME, TREE_TIME + 1, TREE_TIME + 2]

ANOTHER_MAP = 'CET-L9'


def psi(timeIndex, sliceIndex):
    """One 2D slice, every element carrying where in the quantity it sits."""
    return [[1000. * timeIndex + 100. * sliceIndex + 10. * radial + vertical
             for vertical in range(len(THETA))]
            for radial in range(len(RHO))]


def _psi():
    """equilibrium-like: three pictures of `psi`, the window on time slice 1."""
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
                        indices={'i': str(TREE_TIME), 'j': str(TREE_SLICE)},
                        lengths={'i': str(len(TIMES)), 'j': str(SLICES)})


def _small():
    """A 2D leaf whose whole span is a hundredth: the rounding is what breaks here."""
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0.]
    ids.emissivity = [[0.011, 0.012, 0.013], [0.014, 0.015, 0.023]]
    return FakeAxesNode(ids, 'foo', 'foo', 'FLT_2D', name='emissivity',
                        coordinates=('1..N', '1..M'))


@pytest.fixture
def figure(qtbot):
    widget = QVizImagePlot(title='SlicesImage1')
    qtbot.addWidget(widget)
    widget.plot(_psi())
    return widget


# ------------------------------------------------------------------- helpers

def levelsOf(image):
    return tuple(float(value) for value in image.getLevels())


def pictureLevels(figure):
    return [levelsOf(image) for image in figure.images()]


def lutOf(image):
    """The colours the picture is drawn with, or None for pyqtgraph's grey ramp."""
    return image.lut


def dragBar(figure, region=(90., 250.)):
    """The two handles of the colour bar, moved the way a drag moves them.

    `LinearRegionItem.setRegion` emits what a mouse drag emits, and the bar
    answers by pushing the new range onto every image it is bound to.
    """
    figure.colorBar.region.setRegion(region)
    return tuple(float(value) for value in figure.colorBar.levels())


# ------------------------------------------------------- one map, every picture

@pytest.mark.ui
def test_every_picture_is_drawn_with_a_map_of_this_node(figure):
    """Not a grey ramp, and the same map on all three.

    Measured before this row: three pictures, `images luts [False, False,
    False]` -- no lookup table anywhere, so the colours were the library's
    default black-to-white and a level could not be read off a picture.
    """
    luts = [lutOf(image) for image in figure.images()]

    assert all(lut is not None for lut in luts)
    assert np.array_equal(luts[0], luts[1]) and np.array_equal(luts[1], luts[2])
    assert [image.getColorMap().name for image in figure.images()] \
        == [DEFAULT_MAP] * 3


@pytest.mark.ui
def test_the_bar_drives_every_picture_and_not_the_last_one_handed_to_it(figure):
    """The bug the whole row sits on, pinned on the library's own bookkeeping."""
    assert len(figure.colorBar.img_list) == 3
    assert [reference() is not None for reference in figure.colorBar.img_list] \
        == [True, True, True]


@pytest.mark.ui
def test_the_bar_numbers_are_the_scale_the_pictures_are_drawn_against(figure):
    """One question, one answer.

    Measured before: the bar was built with no `values`, so it took the levels off
    the single image it was bound to -- `(0.0, 15.0)` beside pictures drawn
    against `(0.0, 215.0)`. A user reading a level off the ramp read a number the
    colours did not stand for.
    """
    scale = figure.colourLevels()

    assert tuple(float(value) for value in figure.colorBar.levels()) == scale
    assert pictureLevels(figure) == [scale] * 3


@pytest.mark.ui
def test_the_scale_spans_the_pictures_and_is_not_the_first_ones(figure):
    """The two assertions have to be together: one without the other is vacuous.

    The scale covers all three pictures, and the first picture's own span is
    strictly inside it -- which is what makes the test above say something. Had
    the bar kept the first picture's range, this figure would answer a scale whose
    high end is two thirds below what is on screen.
    """
    low, high = figure.colourLevels()
    drawn = [np.asarray(image.image) for image in figure.images()]

    assert low <= min(float(values.min()) for values in drawn)
    assert high >= max(float(values.max()) for values in drawn)
    firstLow, firstHigh = float(drawn[0].min()), float(drawn[0].max())
    assert firstHigh < high


# ------------------------------------------------------- a range under a hand

@pytest.mark.ui
def test_a_drag_on_the_bar_rescales_every_picture_at_once(figure):
    before = pictureLevels(figure)

    moved = dragBar(figure)

    assert moved != before[0]
    assert pictureLevels(figure) == [moved] * 3
    assert figure.colourLevels() == moved


@pytest.mark.ui
def test_the_range_a_hand_set_holds_while_the_window_of_pictures_moves(figure):
    """The two promises the same window makes, and they can contradict.

    A window move re-reads three new slices. Fitting the scale to them would be
    the per-picture re-fit the manual rules out, and would pull the range out
    from under a hand that has just set it. So the re-read hands pyqtgraph the
    values *and* the range: measured, `setImage` without `levels` re-fits,
    answering `(0, 399)` for a 20x20 slice inside a window scaled to `(0, 215)`.
    """
    moved = dragBar(figure)

    figure.framesControls.setStart(0)

    assert figure.colourLevels() == moved
    assert pictureLevels(figure) == [moved] * 3
    assert tuple(float(value) for value in figure.colorBar.levels()) == moved


@pytest.mark.ui
def test_the_handles_move_a_small_quantity_in_steps_of_that_quantity(figure):
    """`rounding` is derived, because the library's default is one **unit**.

    Measured on a quantity spanning `0,011 .. 0,023`: dragging the handles with
    `rounding=1` answers `(0, 1)` -- the scale of the window is replaced by one
    unit nobody asked for, and the pictures go blank. A thousandth of the span
    answers a range of the same order as the data.
    """
    small = QVizImagePlot(title='SlicesImage2')
    small.plot(_small())
    span = small.colourLevels()[1] - small.colourLevels()[0]

    assert small.colorBar.rounding == pytest.approx(span / 1000.0)
    assert roundingFor((0., span)) == pytest.approx(span / 1000.0)

    moved = dragBar(small)

    assert abs(moved[1]) < 1.0 and abs(moved[0]) < 1.0, \
        'the handles moved a hundredth-scale quantity to a whole-unit scale'


# ------------------------------------------------------------- choosing a map

@pytest.mark.ui
def test_a_map_chosen_on_the_window_recolours_every_picture(figure):
    before = [lutOf(image) for image in figure.images()]

    figure.colourScale.setColourMap(ANOTHER_MAP)

    after = [lutOf(image) for image in figure.images()]
    assert [image.getColorMap().name for image in figure.images()] \
        == [ANOTHER_MAP] * 3
    assert all(not np.array_equal(old, new) for old, new in zip(before, after))
    assert np.array_equal(after[0], after[2])
    assert figure.colorBar.colorMap().name == ANOTHER_MAP


@pytest.mark.ui
def test_a_map_this_node_cannot_draw_is_refused_by_the_name_it_was_given(figure):
    """`colormap.get` answers a `FileNotFoundError` naming a path in its package.

    The user chose a *name*, so the refusal says the name; and the window keeps
    the map it had, because a picture that lost its colours over a misspelled
    session file is worse than the colours it had.
    """
    before = [lutOf(image) for image in figure.images()]

    with pytest.raises(ValueError) as raised:
        figure.colourScale.setColourMap('no-such-colour-map')

    assert 'no-such-colour-map' in str(raised.value)
    assert figure.colourScale.colourMap() == DEFAULT_MAP
    for old, image in zip(before, figure.images()):
        assert lutOf(image) is old, 'a refused name cost the picture its colours'


@pytest.mark.ui
def test_the_menu_offers_the_colour_scale_on_every_picture(figure):
    """A bar 25 pixels wide is not a way to find a command.

    The line answers the window, wherever it was clicked -- the pictures share one
    scale, so picking a map on picture two recolouring picture one is the honest
    answer and the bar says so.
    """
    lines = [[action.text() for action in plotItem.getViewBox().menu.actions()
              if action.text() == ENTRY]
             for plotItem in figure.plotItems()]

    assert len(lines) == 3
    assert all(line == [ENTRY] for line in lines)


# ------------------------------------------------------------------- chooser

@pytest.mark.ui
def test_the_chooser_shows_the_maps_as_the_colours_they_stand_for(figure):
    chooser = figure.colourScale.choose()

    assert chooser is figure.colourScale.chooser
    assert chooser.maps.count() == len(mapNames())
    assert chooser.chosenName() == DEFAULT_MAP
    assert not chooser.maps.item(0).icon().isNull(), \
        'a name with no strip beside it: %d names are not choosable by eye' \
        % len(mapNames())


@pytest.mark.ui
def test_the_chooser_narrows_to_what_is_typed_and_answers_that_name(figure):
    chooser = figure.colourScale.choose()

    chooser.filter.setText('CET-L9')

    assert [chooser.maps.item(i).text()
            for i in range(chooser.maps.count())] == [ANOTHER_MAP]

    chooser.maps.setCurrentRow(0)
    chooser.accept()

    assert figure.colourScale.colourMap() == ANOTHER_MAP
    assert figure.images()[0].getColorMap().name == ANOTHER_MAP


@pytest.mark.ui
def test_a_filter_matching_nothing_is_not_an_answer(figure):
    """Closing on an empty list must not put a map nobody chose on the window."""
    chooser = figure.colourScale.choose()

    chooser.filter.setText('nothing-matches-this')
    chooser.accept()

    assert chooser.chosenName() is None
    assert chooser.isVisible()
    assert figure.colourScale.colourMap() == DEFAULT_MAP


# ------------------------------------------------------ what a hand was on

@pytest.mark.ui
def test_a_scale_the_window_settled_for_itself_is_written_as_nothing(figure):
    assert colourScaleOf(figure) is None


@pytest.mark.ui
def test_a_dragged_range_is_written_and_the_map_is_not(figure):
    moved = dragBar(figure)

    colorMap, low, high = colourScaleOf(figure)

    assert colorMap is None, 'the colours nobody changed are not a hand'
    assert (low, high) == moved


@pytest.mark.ui
def test_a_chosen_map_is_written_and_the_range_is_not(figure):
    figure.colourScale.setColourMap(ANOTHER_MAP)

    colorMap, low, high = colourScaleOf(figure)

    assert colorMap == ANOTHER_MAP
    assert (low, high) == (None, None), \
        'a span nobody moved is the span the pictures settle on'


@pytest.mark.ui
def test_a_replayed_scale_counts_as_the_hand_it_stands_for(figure):
    """Otherwise the second close loses what the first restore put back."""
    figure.colourScale.restore(name=ANOTHER_MAP, low=1250.0, high=2900.0)

    assert colourScaleOf(figure) == (ANOTHER_MAP, 1250.0, 2900.0)
    assert figure.colourLevels() == (1250.0, 2900.0)
    assert pictureLevels(figure) == [(1250.0, 2900.0)] * 3


@pytest.mark.ui
def test_a_replayed_map_this_node_cannot_draw_is_the_callers_to_say(figure):
    with pytest.raises(ValueError):
        figure.colourScale.restore(name='no-such-colour-map', low=1.0, high=2.0)

    assert figure.colourScale.colourMap() == DEFAULT_MAP


# ------------------------------------------------------------- the panel, the map

@pytest.mark.ui
def test_the_preview_panel_pictures_with_the_same_map(qtbot):
    """A thumbnail is a question about where the data is, and a grey ramp answers
    "is anything here" while hiding where it peaks. The level range is left to fit
    the one slice: nothing in a thumbnail is compared to a neighbour."""
    panel = QVizPreviewPlot(title='preview')
    qtbot.addWidget(panel)

    assert panel.imageItem.getColorMap() is mapNamed(DEFAULT_MAP)


# --------------------------------------------------------------- ownership

class _ShapeOfAPictureWindow(object):
    """Just enough of a window for a scale to be wired to one, and freed."""

    def __init__(self):
        self.colorBar = None
        self.levels = (0., 1.)

    def colourLevels(self):
        return self.levels

    def setColourLevels(self, levels):
        self.levels = levels


class _StubBar(object):
    """The bar as the scale meets it: it already moved, it only has to say where."""

    def __init__(self, levels):
        self._levels = levels

    def levels(self):
        return self._levels


@pytest.mark.ui
def test_the_colour_scale_holds_its_window_weakly(qapp):
    """The `QVizCurveErrors` rule, again: a helper kept on a Qt widget may not
    reach back into it strongly.

    The behavioural form of this test -- build a window, drop it, ask whether it
    is gone -- is `test_58`'s, and it cannot be used on this frame: a bare
    `QVizImagePlot` is already held by the closures of its own `_makeSliceButtons`
    (`cad1c3c`, and a bare window answers the same as one that plotted), so the
    answer would say nothing about the scale. What is pinned here is the shape the
    rule asks for -- a weak reference and no bound method -- on the real window,
    and the answers once the owner is gone on one that can actually be freed.
    """
    window = _ShapeOfAPictureWindow()
    scale = QVizImageColourScale(window)
    reference = weakref.ref(window)

    assert reference() is window

    del window

    assert reference() is None, 'the scale keeps its window alive'
    # And what it answers once the owner is gone is nothing, not an exception: a
    # session saving a figure that closed in the meantime asks a question, and the
    # honest answer is that no hand is on anything.
    assert scale.state() is None
    scale.levelMoved(_StubBar((1., 2.)))
    assert scale.state() is None, 'a record of a window that is gone is not a hand'


@pytest.mark.ui
def test_the_colour_scale_reaches_its_window_through_one_weak_reference(figure):
    """No bound method of the window is kept anywhere in the record.

    The menu line and the chooser are the two ways the scale could reach back: the
    first is connected to a method of the *scale*, the second is parented to the
    window, so Qt owns it and takes it down with the pictures it was opened on.
    """
    scale = figure.colourScale

    assert isinstance(scale._window, weakref.ref)
    assert scale._window() is figure

    chooser = scale.choose()
    assert chooser.parent() is figure


@pytest.mark.ui
def test_a_window_that_holds_no_scale_answers_nothing(qapp):
    """A curve figure dresses traces one by one -- `QVizPlotStyling`'s question --
    so it has no colour scale, and a session saving it is told nothing rather than
    an empty answer it would have to interpret."""
    assert colourScaleOf(type(str('Other'), (), {})()) is None
    assert restoreColourScale(type(str('Other'), (), {})(), name=ANOTHER_MAP) is False

