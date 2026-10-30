# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The colour scale a picture is drawn with, and what a hand may change on it.

A picture says nothing about its values until something maps them to colours.
Before this module, an image window handed pyqtgraph an array and a level range
and let the mapping fall to its default: a grey ramp, which is a fine answer to
"is there data here" and a poor one to "where does this profile peak, and by how
much over that one". Three pictures of the same quantity side by side ask that
second question, and a grey ramp answers it with two greys nobody separates.

The scale is one answer per **window**, not per picture -- the same rule that
fixes the level range over all the pictures. A map chosen for one picture would
make the colour mean two things on one screen, which is the mistake the level
scale exists to prevent.

What is asked of pyqtgraph here is small and was measured on
`PyQtGraph/0.13.7-foss-2023b` before being written down:

* **71** maps ship with the package (`colormap.listMaps()`, read from
  `colors/maps/*.csv|hex` -- `viridis`, `cividis`, `turbo` and the CET family).
  Another **182** names resolve through matplotlib, which is what the library's
  own right-click menu on a `ColorBarItem` offers;
* an unknown name is not answered with a default: `colormap.get('nope')` raises
  `FileNotFoundError` naming a path under the package. That path is not a word a
  user has anything to read, so `mapNamed` refuses by the name it was given;
* a `ColorMap` answers `getGradient()` with a `QLinearGradient` of **256** stops,
  which is what a swatch is painted from -- a list of 71 names means nothing to a
  hand picking one;
* a `ColorBarItem` adjusts its levels in multiples of `rounding`, **1** by
  default, and refuses a span under it. Measured on a quantity spanning
  `0,011 .. 0,023`: dragging the handles with the default answers `(0, 1)` -- the
  scale of the whole window collapses to one unit nobody asked for. So the
  rounding is derived from the scale the window settled on (`roundingFor`), and
  measured again at `span/1000` the same drag answers a scale of the right order.

The default is `viridis`: it ships here (CC0), it is uniform in perceptual
distance -- an equal step in colour for an equal step in value, which is what
reading a level off a picture asks -- and it is legible to a colour-blind eye.
It is the same map on every picture of a window, so the pictures stay
comparable, which is the promise the level scale already makes.
"""

import math
import weakref

import pyqtgraph as pg

# What a window opens with, and what a session that names no map settles back on.
DEFAULT_MAP = 'viridis'

# The drag of a handle moves the level by a multiple of this. Derived, never
# asked: `rounding=1` on a quantity of order 0,01 flattens the scale to one unit.
ROUNDING_DIVISOR = 1000.0
# A scale of no span at all (a flat picture) still has to answer a number, or the
# library divides by it.
MINIMUM_ROUNDING = 1e-12


def mapNames():
    """The maps this node can draw with, in the order a chooser lists them.

    Sorted because the list is read by eye: `listMaps()` answers the order of
    `listdir`, which is the order the filesystem happens to hand the files back.
    """
    return sorted(pg.colormap.listMaps())


def isKnown(name):
    """Whether that name is a map -- asked before a refusal is written."""
    try:
        mapNamed(name)
        return True
    except ValueError:
        return False


def mapNamed(name):
    """The `ColorMap` one name stands for, refused by the name it was given.

    Two places can name a map: this application, which lists what ships with the
    package, and pyqtgraph's own menu on the colour bar, which also reaches the
    maps matplotlib knows. Both are honest names to read back, so both are
    resolved -- bundled first, then matplotlib, so a name the package ships is
    never answered by a library that may not be there tomorrow.

    What pyqtgraph answers for a name that is neither is a `FileNotFoundError`
    naming a file under its own installation. The user chose a *name*, so the
    refusal says the name.
    """
    if not name:
        raise ValueError('A colour scale names no map: a picture is drawn with '
                         'one of the %d maps this node holds, "%s" by default.'
                         % (len(pg.colormap.listMaps()), DEFAULT_MAP))
    try:
        return pg.colormap.get(name)
    except Exception:
        pass
    try:
        return pg.colormap.get(name, source='matplotlib')
    except Exception:
        raise ValueError('"%s" is not a colour map this node can draw with: it '
                         'holds %d of its own (%s, %s, %s, ...) and reads '
                         'matplotlib for the rest.'
                         % (name, len(pg.colormap.listMaps()), DEFAULT_MAP,
                            'cividis', 'CET-L9'))


def roundingFor(levels):
    """What a handle moves the scale by, out of the scale the window settled on.

    A thousandth of the span: fine enough to set a level to the eye on any
    quantity, coarse enough that the numbers keep the digits they had. A scale
    with no span answers the floor rather than nothing -- the library divides the
    drag by this number.
    """
    if levels is None:
        return MINIMUM_ROUNDING
    low, high = levels
    try:
        span = float(high) - float(low)
    except (TypeError, ValueError):
        return MINIMUM_ROUNDING
    if not math.isfinite(span) or span <= 0.0:
        return MINIMUM_ROUNDING
    return max(span / ROUNDING_DIVISOR, MINIMUM_ROUNDING)


def swatchPixmap(colorMap, width=96, height=14):
    """A strip of one map, so a name is chosen on the colours it stands for.

    Painted from the map's own gradient rather than sampled by hand: the maps are
    not linear in hue and a three-colour sample of `CET-D1` would answer two
    blues, hiding the mid-point that makes a diverging map the answer to a
    question about a sign.
    """
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QBrush, QGradient, QImage, QPainter, QPixmap

    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(Qt.GlobalColor.black)
    painter = QPainter(image)
    gradient = colorMap.getGradient()
    gradient.setStart(QPointF(0.0, 0.0))
    gradient.setFinalStop(QPointF(float(width), 0.0))
    gradient.setCoordinateMode(QGradient.CoordinateMode.ObjectMode)
    painter.fillRect(QRectF(0.0, 0.0, float(width), float(height)),
                     QBrush(gradient))
    painter.end()
    return QPixmap.fromImage(image)


class QVizImageColourScale(object):
    """One picture window's colour scale, and what a hand changed on it.

    Held by the window, holding the window back through a `weakref` -- the shape
    `QVizCurveErrors` was written in for the same reason. A helper kept on a Qt
    widget may not hold one of its bound methods: the cycle hands the widget to
    the cyclic collector, and on this Qt a widget freed there is freed while Qt
    still owes it a paint event. The dialogue is therefore handed a method of
    *this* object, which reaches the window through the weak reference.

    It answers two questions for the window and keeps one record:

    * which map the pictures are drawn with -- one answer for the window, so the
      colour means the same thing on every picture;
    * where the level range stands, which the window owns (`colourLevels`) and
      this only moves when a hand drags a handle;
    * whether a hand was on either, which is the whole of what a session is told.
      The scale a window settled for itself is not a hand: writing it would pin
      the span of the day the file was written onto a case opened a month later,
      which is the argument the curve palette already makes.
    """

    def __init__(self, window, defaultMap=DEFAULT_MAP):
        self._window = weakref.ref(window)
        self.mapName = defaultMap
        self.mapTouched = False
        self.levelsTouched = False
        # The chooser and the menu lines, kept because a Qt widget no Python
        # reference holds dies with the wrapper that made it.
        self.chooser = None
        self._actions = []

    # ------------------------------------------------------------------- wiring
    def bind(self, colorBar, images, plotItems):
        """Hand the bar the pictures it answers for, and the menu that opens here.

        One `setImageItem` call with the **list**: the library replaces its list on
        every call (`img_list = [weakref.ref(item) for item in img]`), so handing
        the pictures one at a time -- as this window used to, on the reading that
        a bar drives one image -- leaves it driving the last one. Measured: three
        pictures and one call answer `len(img_list) == 3`, and the map and the
        levels then land on all three.

        The map is set *after* the images are bound: `setColorMap` is what pushes
        the lookup table onto each of them.
        """
        colorBar.setImageItem(list(images))
        colorBar.setColorMap(mapNamed(self.mapName))
        colorBar.sigLevelsChanged.connect(self.levelMoved)
        self._addMenuEntries(plotItems)

    def _addMenuEntries(self, plotItems):
        """One *Colour Scale...* line on each picture's menu.

        The pictures share one scale, so the line answers the window wherever it
        was clicked -- and clicking it on picture two recolouring picture one is
        the honest answer, not a surprise: the bar says one range for all three.
        """
        from PySide6.QtGui import QAction

        from imasviz.VizGUI.VizPlot.QVizColourScaleUI import ENTRY

        for plotItem in plotItems:
            action = QAction(ENTRY, plotItem.getViewBox())
            action.triggered.connect(self.choose)
            plotItem.getViewBox().menu.addAction(action)
            self._actions.append(action)

    # ------------------------------------------------------------------ answers
    def colourMap(self):
        return self.mapName

    def setColourMap(self, name):
        """Draw every picture with that map, and remember a hand chose it.

        Raises the refusal `mapNamed` answers -- a name this node cannot draw --
        and leaves the window alone: a picture that lost its colours because a
        name was misspelled in a session file is worse than the default it keeps.
        """
        window = self._window()
        resolved = mapNamed(name)
        self.mapName = name
        self.mapTouched = True
        if window is not None and window.colorBar is not None:
            window.colorBar.setColorMap(resolved)

    def levelMoved(self, colorBar):
        """A handle was dragged: the window's scale moves with it, and is a hand.

        The bar has already pushed the new range onto every bound picture when it
        emits, so this only records it. Measured: one drag of both handles emits
        **3** times -- the window keeps the last answer, which is the same one.
        """
        window = self._window()
        if window is None:
            # A bar that outlived its window cannot have been dragged on it: the
            # record would be a hand on a figure that is already closed.
            return
        self.levelsTouched = True
        window.setColourLevels(tuple(float(value) for value in colorBar.levels()))

    def choose(self):
        """Open the chooser on the map this window draws with."""
        from imasviz.VizGUI.VizPlot.QVizColourScaleUI import QVizColourScaleUI

        window = self._window()
        if window is None:
            return None
        self.chooser = QVizColourScaleUI(parent=window, current=self.mapName,
                                         onChosen=self.setColourMap)
        self.chooser.show()
        return self.chooser

    # ------------------------------------------------------------- the session
    def state(self):
        """What a session is told: nothing, or `(map, low, high)` with its holes.

        A part nobody touched answers None, so a file says only what a hand set:
        a session that changed the colours keeps the span the pictures settle on,
        and one that changed the span keeps whatever map this node draws with.
        """
        window = self._window()
        if window is None or not (self.mapTouched or self.levelsTouched):
            # A window that is gone has no scale to keep either: the record of a
            # hand on a figure that closed would name neither a map nor a range,
            # which is exactly what the reader of a session file refuses.
            return None
        levels = window.colourLevels()
        low, high = (None, None) if levels is None else (levels[0], levels[1])
        return (self.mapName if self.mapTouched else None,
                low if self.levelsTouched else None,
                high if self.levelsTouched else None)

    def restore(self, name=None, low=None, high=None):
        """Put a saved scale back -- and count as the hand it stands for.

        A replay is a hand: closing that run again has to write the same file, or
        a session would lose the scale the first time it was opened.
        """
        if name is not None:
            self.setColourMap(name)
        window = self._window()
        if (low is not None or high is not None) and window is not None:
            if window.colorBar is not None:
                # `values` with a hole keeps the other end: a file naming only a
                # map must not answer the span it never named.
                window.colorBar.setLevels(values=(low, high))
                window.setColourLevels(tuple(float(value)
                                             for value in window.colorBar.levels()))
            self.levelsTouched = True


def colourScaleOf(window):
    """What a session is told of this window's scale, or None for a window that
    has no scale to keep.

    A curve figure has no colour scale -- it dresses traces one by one, which is
    `QVizPlotStyling`'s question -- so it answers no `colourScale` and is written
    as nothing. Table and Stacked windows draw curves too, and hold no picture.
    """
    scale = getattr(window, 'colourScale', None)
    return None if scale is None else scale.state()


def restoreColourScale(window, name=None, low=None, high=None):
    """Put a saved scale back on a window, answering whether it can hold one.

    The caller says what a refusal costs -- a scale written for a window the file
    now redraws as something else is worth a line in the log of the case, and
    nothing else. A name this node cannot draw is raised, not swallowed: it is the
    one half of the refusal the session cannot answer by itself.
    """
    scale = getattr(window, 'colourScale', None)
    if scale is None:
        return False
    scale.restore(name=name, low=low, high=high)
    return True
