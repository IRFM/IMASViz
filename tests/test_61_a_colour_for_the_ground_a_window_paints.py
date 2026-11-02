# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""One palette, because one ground: what a window paints behind a curve.

A curve figure and a panel of a Table Plot View draw the same kind of line, and
they draw it on the same ground. Measured, asking the question that matters --
`backgroundBrush()` of the window, which is a `QGraphicsView` and paints its own
ground:

    curve figure   SolidPattern (0, 0, 0, 255)   -- pyqtgraph's own default
    panel of a table window   SolidPattern (0, 0, 0, 255)  -- the same default

The black is not an IMASViz choice: it is pyqtgraph's configuration default
(`'background': 'k'`), applied by `GraphicsView.__init__`. Nothing in this package
touches it -- and this file is the guard that keeps it that way, because a window
that called `setBackground` would be drawing this palette on a ground it fails.

Do not ask `viewBox.background.brush()`. Measured, that `QGraphicsRectItem` is
**hidden** and its brush **NoBrush** -- pyqtgraph only shows it when
`setBackgroundColor` was called, which nowhere here does -- yet its `color()`
still answers `(0, 0, 0, 255)`. A probe that read it reported a window as black
when it was painted white.

That happened once. The Profiles plugin drew its own table (`QVizTablePlotView.py:
75`) over `setBackground((255, 255, 255))`, and against that white **5** of the
**8** colours of this palette are barely there: cyan **1,25**, chartreuse **1,30**,
spring green **1,35**, gold **1,40**, orange **2,33. A second palette was written
for that window -- 8 dark colours, weakest contrast **4,77** on white -- and it
went with the window it was written for. A panel of the application's Table Plot
View is painted by `QVizPanel`, which never calls `setBackground`, so it is black
like a curve figure and asks the same palette.

The legacy the light palette replaced: `QVizTablePlotView.setPen()` answered
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
from imasviz.VizGUI.VizPlot.QVizCurveColors import (CURVE_COLOURS, CYCLE,
                                                    colourFor)
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPanel import QVizPanel
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlot import QVizTablePlot
from imasviz.VizUtils import GlobalColors

from support import ownership

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The two grounds, and the floor a colour has to clear on the one windows paint.
# Measured on the palette: the weakest entry on black answers **4,66** (violet),
# the strongest on white answers **2,33** (orange). The two numbers are why there
# is one list and a refusal where the other ground would come from.
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
CONTRAST_FLOOR = 4.5

# What a confidence band is filled with, wherever the band is offered -- and a
# panel offers it: `QVizPanel` builds the same `QVizCurveErrors` a figure does.
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


def palette():
    return [rgb for _, rgb in CURVE_COLOURS]


def names():
    return ', '.join('%s %r' % (name, rgb) for name, rgb in CURVE_COLOURS)


# -- the palette, asked against the ground it is painted on ---------------

def test_every_colour_is_legible_on_the_ground_windows_paint():
    """A line has to stand out from the ground it is drawn on.

    The floor is not decoration: measured, `#FFFF00` answers **1,07** on black --
    the same window, a line nobody sees. Weakest here: violet **4,66**.
    """
    assert CYCLE == len(CURVE_COLOURS) == len(palette())
    assert len(set(palette())) == CYCLE

    for name, rgb in CURVE_COLOURS:
        ratio = contrast(rgb, BLACK)
        assert ratio >= CONTRAST_FLOOR, \
            '%s %r answers %.2f on black' % (name, rgb, ratio)


def test_the_palette_holds_no_band_colour_and_no_near_white():
    """Two refusals, for two reasons the palette cannot work without.

    Those panels carry `QVizCurveErrors` like a curve figure, so a trace in the
    colour of a band over it is the confusion, wherever the band is offered. And
    three channels at or above 128 is a near-white: on a dark ground it is
    background noise, which is what three entries of the old hex list were.
    """
    assert BAND_RGB not in palette()

    for name, rgb in CURVE_COLOURS:
        assert not all(value >= 128 for value in rgb), \
            '%s %r reads as background on the ground it is drawn on' % (name, rgb)


def test_the_palette_stays_far_apart_where_its_cycle_closes():
    """The cycle is what a user sees when a selection is longer than the palette.

    Measured: the smallest squared rgb distance between two consecutive entries,
    the last and the first **included**, is **81 154** (cyan then chartreuse). The
    closing pair is the one a per-entry check misses.
    """
    colours = palette()
    for index in range(CYCLE):
        following = colours[(index + 1) % CYCLE]
        gap = squaredDistance(colours[index], following)
        assert gap > 20000, '%s then %s: %.0f apart' \
                            % (CURVE_COLOURS[index][0],
                               CURVE_COLOURS[(index + 1) % CYCLE][0], gap)


def test_the_palette_vanishes_on_a_white_ground():
    """Why a window may not paint one -- and why the second palette is gone.

    Measured against white, **5** of the **8** colours answer under 2,5: cyan
    1,25, chartreuse 1,30, spring green 1,35, gold 1,40, orange 2,33. A second
    palette existed for that ground and cost a window to justify; refusing the
    ground is the cheaper half of the same decision.
    """
    vanishing = [(name, rgb, contrast(rgb, WHITE))
                 for name, rgb in CURVE_COLOURS if contrast(rgb, WHITE) < 2.5]
    assert len(vanishing) == 5, 'measured: %r' % (vanishing,)


def test_the_palette_answers_the_question_a_window_asks():
    """`colourFor` cycles; the name of the colour it answers can be said.

    A refusal and a test have to be able to say which colour was meant. The
    second palette's accessors (`lightColourFor`, `lightNameFor`) are gone with
    it: a module answering two palettes is a module asking which ground a window
    paints, and no window asks that.
    """
    assert colourFor(0) == CURVE_COLOURS[0][1]
    assert colourFor(CYCLE) == colourFor(0)
    assert colourFor(3) == CURVE_COLOURS[3][1]

    from imasviz.VizGUI.VizPlot import QVizCurveColors as module
    for gone in ('LIGHT_CURVE_COLOURS', 'LIGHT_CYCLE', 'lightColourFor',
                 'lightNameFor'):
        assert not hasattr(module, gone), '%s came back beside one palette' % gone


# -- the ground, asked the right way ---------------------------------------

@pytest.mark.ui
def test_a_figure_and_a_panel_paint_the_same_ground(qapp):
    """`backgroundBrush()` of the window, which is what paints.

    Measured: both answer `SolidPattern (0, 0, 0, 255)`, from pyqtgraph's own
    configuration default. A panel is a `QWidget` holding a `PlotWidget`, so its
    ground is its own view's, and it is the same one a figure gets.
    """
    figure = ownership.keep(QVizCurvePlot(title='SlicesPlot1'))
    table = ownership.keep(QVizTablePlot(title='TablePlotView:probe'))
    panel = ownership.keep(QVizPanel(table))

    for view in (figure.pgPlotWidget, panel.pgPlotWidget):
        assert view.backgroundBrush().style() == Qt.BrushStyle.SolidPattern
        assert view.backgroundBrush().color().getRgb()[:3] == BLACK, \
            'the palette is picked for black: %s' % names()


@pytest.mark.ui
def test_a_view_box_is_not_what_paints_the_ground(qapp):
    """The reading that reported a white window as black.

    `ViewBox.background` is a `QGraphicsRectItem` pyqtgraph shows only when
    `setBackgroundColor` was called. Asked offscreen and unseen: hidden,
    `NoBrush` -- and a `color()` of `(0, 0, 0, 255)` all the same.
    """
    figure = ownership.keep(QVizCurvePlot(title='SlicesPlot1'))
    table = ownership.keep(QVizTablePlot(title='TablePlotView:probe'))
    panel = ownership.keep(QVizPanel(table))

    for view in (figure.pgPlotWidget, panel.pgPlotWidget):
        box = view.getPlotItem().getViewBox()
        assert box.background.isVisible() is False
        assert box.background.brush().style() == Qt.BrushStyle.NoBrush
        assert box.background.brush().color().getRgb()[:3] == BLACK, \
            'the colour is there to be misread: %r' % (names(),)


def test_no_window_of_the_package_paints_another_ground():
    """The refusal that replaces the second palette.

    Measured: the only `setBackground` in the package was the Profiles plugin's
    own table window, at line 75 of the module that is now deleted. A window
    asking for another ground is a window the palette fails on, and the failure
    is invisible -- the traces draw, they are just barely there.

    Read off the syntax tree, because the name is in the prose of four modules
    that explain what it did and why it is gone: a line scan would refuse its own
    record, as the `getRGBColorList` guard below had to learn.
    """
    import ast

    painting = []
    for dirpath, _, fileNames in os.walk(os.path.join(REPO, 'imasviz')):
        for name in fileNames:
            if not name.endswith('.py'):
                continue
            source = os.path.join(dirpath, name)
            with open(source) as handle:
                tree = ast.parse(handle.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and \
                        isinstance(node.func, ast.Attribute) and \
                        node.func.attr in ('setBackground',
                                           'setBackgroundColor'):
                    painting.append('%s:%d' % (os.path.relpath(source, REPO),
                                               node.lineno))
    assert painting == [], 'a window paints a ground the palette fails on: %s' \
                           % ', '.join(painting)


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


def test_no_module_of_the_package_builds_a_pen_of_its_own():
    """The plugin asked its own colour for 41 curves; it asks the palette now.

    The window that did it is deleted, and so is the answer it gave: `setPen()`
    of `QVizTablePlotView` answered `getRGBColorList()[0]` for every curve.
    Pinned so a hand-made pen cannot come back beside the shared one -- the
    colour of the curves themselves is pinned on a real figure in `test_59`.
    """
    assert not os.path.exists(os.path.join(
        REPO, 'imasviz', 'VizPlugins', 'viz_Profiles', 'viz_profiles',
        'QVizTablePlotView.py'))

    building = []
    for dirpath, _, fileNames in os.walk(os.path.join(REPO, 'imasviz')):
        for name in fileNames:
            if not name.endswith('.py'):
                continue
            source = os.path.join(dirpath, name)
            with open(source) as handle:
                for number, line in enumerate(handle, 1):
                    if line.strip().startswith('def setPen'):
                        building.append('%s:%d' % (os.path.relpath(source, REPO),
                                                   number))
    assert building == [], 'a module builds a trace pen of its own: %s' \
                           % ', '.join(building)
