# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The colour a curve is drawn with depends on the ground the window paints.

A figure of curves and the Profiles plugin's table window draw the same kind of
line on two different grounds. Measured, asking the question that matters --
`backgroundBrush()` of the window, which is a `QGraphicsView` and paints its own
ground:

    curve figure   SolidPattern (0, 0, 0, 255)   -- pyqtgraph's own default
    plugin window  SolidPattern (255, 255, 255, 255) -- set by the plugin

The black is not an IMASViz choice: it is pyqtgraph's configuration default
(`'background': 'k'`), applied by `GraphicsView.__init__`. The white is the
plugin's, at `QVizTablePlotView.py:75`, and it is the only `setBackground` in the
package.

Do not ask `viewBox.background.brush()`. Measured on both windows, that
`QGraphicsRectItem` is **hidden** and its brush **NoBrush** -- pyqtgraph only
shows it when `setBackgroundColor` was called, which nowhere here does -- yet its
`color()` still answers `(0, 0, 0, 255)`. A probe that read it reported the
plugin's white window as black.

One palette cannot serve both grounds. Measured against that white, half of the
black palette is barely there: cyan **1,25**, chartreuse **1,30**, spring green
**1,35**, gold **1,40**, orange **2,33** (contrast ratios). So the plugin asks
`LIGHT_CURVE_COLOURS`, whose entries answer at least **4,5** there -- and the
plugin draws one of them, the first, on every panel: measured on the reference
case, its window holds **41** panels carrying **41 distinct parametrized paths**,
one panel per path, so a colour has nothing to group and a cycle would repeat the
same colour five times in one window.

The legacy this replaces: `QVizTablePlotView.setPen()` answered
`getRGBColorList()[0]` -- `#0000ff`, chosen by a walk over `GlobalColors.__dict__`
that happened to put blue first -- for all 41 curves, at width 3. **8** of that
list's **18** entries answer a contrast under 2 on the white they were drawn on
(`#FFFF00` **1,07**, cyan **1,25**, `#cce5ff` **1,29**). With the plugin off that
list, nothing in the package read it, and neither did the eighteen `*_HEX`
strings it walked.
"""

import os

import pytest

from PySide6.QtCore import Qt

import imasviz.VizUtils as vizUtils
from imasviz.VizGUI.VizPlot.QVizCurveColors import (CURVE_COLOURS,
                                                    LIGHT_CURVE_COLOURS,
                                                    LIGHT_CYCLE,
                                                    lightColourFor, lightNameFor)
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizTablePlotView \
    import QVizTablePlotView
from imasviz.VizUtils import GlobalColors

from support import ownership

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The ground each palette is picked for, and the floor a colour has to clear on
# it. Measured: the weakest entry of the light list answers 4,77 on white.
WHITE = (255, 255, 255)
CONTRAST_FLOOR = 4.5

# What a confidence band is filled with, wherever the band is offered -- and the
# plugin's panels offer it: their view box carries the same `QVizCurveErrors`.
BAND_RGB = (255, 0, 0)


def luminance(rgb):
    def channel(value):
        value = value / 255.0
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(value) for value in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(rgb, ground):
    lighter, darker = max(luminance(rgb), luminance(ground)), \
                      min(luminance(rgb), luminance(ground))
    return (lighter + 0.05) / (darker + 0.05)


def squaredDistance(first, second):
    return sum((a - b) ** 2 for a, b in zip(first, second))


def lightPalette():
    return [rgb for _, rgb in LIGHT_CURVE_COLOURS]


def names():
    return ', '.join('%s %r' % (name, rgb) for name, rgb in LIGHT_CURVE_COLOURS)


# -- the palette picked against the ground it is painted on ----------------

def test_every_colour_of_the_light_palette_is_legible_on_white():
    """A line has to stand out from the ground it is drawn on.

    The floor is not decoration: measured, `#FFFF00` answers **1,07** on white --
    the same window, a line nobody sees.
    """
    assert LIGHT_CYCLE == len(LIGHT_CURVE_COLOURS)
    assert len({rgb for rgb in lightPalette()}) == LIGHT_CYCLE

    for name, rgb in LIGHT_CURVE_COLOURS:
        ratio = contrast(rgb, WHITE)
        assert ratio >= CONTRAST_FLOOR, \
            '%s %r answers %.2f on white' % (name, rgb, ratio)


def test_the_light_palette_holds_no_band_colour_and_no_near_white():
    """The same two refusals the black palette makes, for the same reasons.

    Those panels carry `QVizCurveErrors` like a curve figure -- `CustomizedViewBox`
    builds the same object and offers the same three lines -- so a trace in the
    colour of a band over it is the confusion, wherever the band is offered. And
    three channels at or above 128 is a near-white: on a white ground it is the
    background, which is what three entries of the old hex list were.
    """
    assert BAND_RGB not in lightPalette()

    for name, rgb in LIGHT_CURVE_COLOURS:
        assert not all(value >= 128 for value in rgb), \
            '%s %r reads as background on the white it is drawn on' % (name, rgb)


def test_the_light_palette_stays_far_apart_where_its_cycle_closes():
    """The cycle is what a user sees when a window outlives the palette.

    Measured: the smallest squared rgb distance between two consecutive entries,
    the last and the first **included**, is **32 768**. The closing pair is the
    one a per-entry check misses.
    """
    colours = lightPalette()
    for index in range(LIGHT_CYCLE):
        following = colours[(index + 1) % LIGHT_CYCLE]
        gap = squaredDistance(colours[index], following)
        assert gap > 20000, '%s then %s: %.0f apart' \
                            % (lightNameFor(index), lightNameFor(index + 1), gap)


def test_the_black_palette_is_not_reusable_on_that_white():
    """Why there are two lists rather than one.

    Measured against the white of the plugin's window, **5** of the **8** colours
    a curve figure paints with answer under 2,5: cyan 1,25, chartreuse 1,30,
    spring green 1,35, gold 1,40, orange 2,33.
    """
    vanishing = [(name, rgb, contrast(rgb, WHITE))
                 for name, rgb in CURVE_COLOURS if contrast(rgb, WHITE) < 2.5]
    assert len(vanishing) == 5, 'measured: %r' % (vanishing,)


def test_the_light_palette_answers_the_question_a_window_asks():
    """`lightColourFor` cycles; `lightNameFor` names the colour it answers.

    A refusal and a test have to be able to say which colour was meant, as the
    black palette's accessors do.
    """
    assert lightColourFor(0) == LIGHT_CURVE_COLOURS[0][1]
    assert lightColourFor(LIGHT_CYCLE) == lightColourFor(0)
    assert lightNameFor(LIGHT_CYCLE) == lightNameFor(0)
    assert lightColourFor(3) == LIGHT_CURVE_COLOURS[3][1]


# -- the ground, asked the right way ---------------------------------------

@pytest.mark.ui
def test_the_two_windows_paint_the_two_grounds_the_palettes_are_picked_for(qapp):
    """`backgroundBrush()` of the window, which is what paints.

    Measured: a figure of curves answers `SolidPattern (0, 0, 0, 255)`, from
    pyqtgraph's own configuration default; the plugin's table window answers
    `SolidPattern (255, 255, 255, 255)`, which is the `setBackground` it sets for
    itself.
    """
    figure = ownership.keep(QVizCurvePlot(title='SlicesPlot1'))
    table = ownership.keep(QVizTablePlotView(None, None, 1, 'profiles_1d', -1))

    assert figure.pgPlotWidget.backgroundBrush().style() == \
        Qt.BrushStyle.SolidPattern
    assert figure.pgPlotWidget.backgroundBrush().color().getRgb()[:3] == (0, 0, 0)
    assert table.backgroundBrush().style() == Qt.BrushStyle.SolidPattern
    assert table.backgroundBrush().color().getRgb()[:3] == WHITE


@pytest.mark.ui
def test_a_view_box_is_not_what_paints_the_ground(qapp):
    """The reading that reported a white window as black.

    `ViewBox.background` is a `QGraphicsRectItem` pyqtgraph shows only when
    `setBackgroundColor` was called. Asked on both windows, offscreen and unseen:
    hidden, `NoBrush` -- and a `color()` of `(0, 0, 0, 255)` all the same.
    """
    figure = ownership.keep(QVizCurvePlot(title='SlicesPlot1'))
    table = ownership.keep(QVizTablePlotView(None, None, 1, 'profiles_1d', -1))
    boxes = [figure.pgPlotWidget.getPlotItem().getViewBox(), table.addViewBox()]

    for box in boxes:
        assert box.background.isVisible() is False
        assert box.background.brush().style() == Qt.BrushStyle.NoBrush
        assert box.background.brush().color().getRgb()[:3] == (0, 0, 0), \
            'the colour is there to be misread: %r' % (names(),)


# -- the guard: the hex walk may not come back -----------------------------

def test_no_module_of_the_package_builds_a_curve_colour_from_a_hex_walk():
    """The use is refused; the name survives only in the prose that buries it.

    Two docstrings of the package still tell what `getRGBColorList()` was -- 18
    rgb triples reached by walking `GlobalColors.__dict__` for every attribute
    ending in `HEX`, then moving `BLUE_HEX` to the front because a curve needed a
    first colour -- so a scan for the name would refuse its own record. What is
    refused here is the use: the attribute gone from the module that defined it
    and from the package surface, and no import line in the package naming it.
    """
    from imasviz.VizUtils import QVizGlobalValues as valuesModule

    assert not hasattr(valuesModule, 'getRGBColorList')
    assert not hasattr(vizUtils, 'getRGBColorList')

    importing = []
    for dirpath, _, fileNames in os.walk(os.path.join(REPO, 'imasviz')):
        for name in fileNames:
            if not name.endswith('.py'):
                continue
            source = os.path.join(dirpath, name)
            with open(source) as handle:
                for line in handle:
                    statement = line.strip()
                    if 'getRGBColorList' in statement and \
                            (statement.startswith('from ') or
                             statement.startswith('import ')):
                        importing.append(os.path.relpath(source, REPO))
                        break
    assert importing == [], 'still importing it: %s' % ', '.join(importing)


def test_the_interface_colours_stay_and_the_curve_colours_left_them():
    """`GlobalColors` is not dead -- it stopped answering for curves.

    The tree paints its nodes with `BLACK`, the preferences turn a number into
    `BLUE`/`RED`/`CYAN`..., the documentation panel fills itself with `LIGHT_CYAN`.
    What is gone is the eighteen `*_HEX` strings that existed only for the walk.
    """
    for brush in ('BLUE', 'RED', 'BLACK', 'CYAN', 'LIGHT_CYAN', 'LIGHT_GREY'):
        assert hasattr(GlobalColors, brush), 'the interface still asks %s' % brush
    assert callable(GlobalColors.getAvailableColorForNodes)

    hexAttributes = [name for name in vars(GlobalColors)
                     if not name.startswith('__') and name.endswith('_HEX')]
    assert hexAttributes == [], 'left over for nobody: %r' % (hexAttributes,)


def test_the_table_view_no_longer_builds_a_pen_of_its_own():
    """The plugin asked its own colour for 41 curves; it asks the palette now.

    Pinned so a hand-made pen cannot come back beside the shared answer: the
    colour of the curves themselves is pinned on the real window, in `test_51`.
    """
    assert not hasattr(QVizTablePlotView, 'setPen')
