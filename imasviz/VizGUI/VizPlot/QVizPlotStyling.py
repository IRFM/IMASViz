# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Who offers the **Configure Plot** window, and what a hand leaves behind.

The dialogue (`QVizPlotStyleUI`) has been in the package since T32 and the manual
has documented its entry under *Plot Configuration and Customization* all along.
Only the plots of the Profiles plugin offered it: the three questions it asks --
`styleCurves()`, `styleText()`, `styleMargins()` -- were answered in one place,
`CustomizedViewBox`, and nothing else. The figures a user actually draws by hand
answered none of them, so the documented entry was simply not on the menu of the
window it documents.

This module is the other half of that. A frame that draws traces holds one of
these, hangs the entry on the menu pyqtgraph built for the view box, and keeps the
record of what the window changed. The entry goes on the **view box** menu for the
same reason the error-bar lines did (`QVizCurveErrors`): the menu is an instance's
own, so nothing written here reaches another figure.

Why a record is needed at all: every trace carries a pen. The palette hands one
out (`QVizCurveColors`), so "does this curve have a colour?" cannot tell the
colour a user picked from the one the cycle picked -- and writing all of them into
a session would freeze the palette into the files and lose the contrast work T33
measured for it. What is kept is therefore *which* traces and *which* lines of
text a hand was on, and their values are read off the item when someone asks. A
window cancelled rolls that record back with the values.

Two measured facts of pyqtgraph 0.13.7 shape this file:

* `AxisItem.setLabel(text, units=...)` clears nothing -- it writes `labelStyle`
  only `if len(args) > 0` (`AxisItem.py:341`), and `text`/`units`/`unitPrefix` are
  named parameters, not style keywords. So the relabel a figure does when the next
  quantity arrives leaves a hand-styled axis alone, and no writer here has to
  defend the style. `LabelItem.setText` merges the kwargs it is given
  (`LabelItem.py:48-51`), so the title behaves the same way.
* A legend swatch needs no keeping either: `LegendItem.ItemSample.paint` reads
  `self.item.opts` at paint time, so a trace recoloured here recolours its swatch.

The helper holds its frame through a `weakref` and never a bound method of it --
the cycle a bound method makes is what has this package segfaulting on this Qt
stack (`QVizCurveErrors`, and the ownership guard of tests/test_44).
"""

import weakref

import pyqtgraph as pg

from PySide6.QtGui import QAction

from imasviz.VizGUI.VizPlot.QVizPlotStyleUI import (QVizPlotStyleUI, penOf,
                                                    styleNameOf, symbolNameOf)
from imasviz.VizUtils import GlobalPgSymbols, GlobalQtStyles

# The words the manual uses, spelled once here: a figure of curves and a panel of
# the Profiles plugin answer the same entry, so they had better carry the same one.
ENTRY = 'Configure Plot'

# The properties of a trace and of a line of text, and the attribute names the
# session file writes them with. One list each, so the writer and the reader of a
# session cannot disagree about what a <Style> holds.
CURVE_ATTRIBUTES = ('color', 'style', 'width', 'symbol', 'size', 'fill',
                    'outline')
TEXT_ATTRIBUTES = ('text', 'bold', 'italic', 'size')


def curveStyle(curve):
    """What one trace is drawn with, in the words a session file writes."""
    pen = penOf(curve)
    return {'color': pen.color().name(),
            'style': styleNameOf(pen),
            'width': '%g' % pen.width(),
            'symbol': symbolNameOf(curve.opts['symbol']),
            'size': '%g' % float(curve.opts['symbolSize']),
            'fill': pg.mkBrush(curve.opts['symbolBrush']).color().name(),
            'outline': pg.mkPen(curve.opts['symbolPen']).color().name()}


def applyCurveStyle(curve, style):
    """Write back what `curveStyle` spelled out; a key that is absent is untouched.

    The pen is read from the curve rather than rebuilt, so a key the file does not
    name -- a join style, a cap -- keeps what it had.
    """
    pen = penOf(curve)
    if style.get('color'):
        pen.setColor(pg.mkColor(style['color']))
    if style.get('style') in GlobalQtStyles.stylesDict:
        pen.setStyle(GlobalQtStyles.stylesDict[style['style']])
    if style.get('width'):
        pen.setWidth(float(style['width']))
    curve.setPen(pen)
    if style.get('symbol') in GlobalPgSymbols.symbolsDict:
        curve.setSymbol(GlobalPgSymbols.symbolsDict[style['symbol']])
    if style.get('size'):
        curve.setSymbolSize(float(style['size']))
    if style.get('fill'):
        curve.setSymbolBrush(pg.mkColor(style['fill']))
    if style.get('outline'):
        curve.setSymbolPen(pg.mkColor(style['outline']))


def textStyle(plotItem, side):
    """How one line of text is drawn: 'title', or the side of an axis label."""
    if side == 'title':
        label = plotItem.titleLabel
        opts = label.opts
        return {'text': label.text or '',
                'bold': _flag(bool(opts.get('bold'))),
                'italic': _flag(bool(opts.get('italic'))),
                'size': str(opts.get('size') or '')}
    axis = plotItem.getAxis(side)
    style = axis.labelStyle
    return {'text': axis.labelText or '',
            'bold': _flag(style.get('font-weight') == 'bold'),
            'italic': _flag(style.get('font-style') == 'italic'),
            'size': str(style.get('font-size') or '')}


def applyTextStyle(plotItem, side, style):
    """Put one line of text back the way `textStyle` found it."""
    bold = style.get('bold') == '1'
    italic = style.get('italic') == '1'
    if side == 'title':
        knobs = {'bold': bold, 'italic': italic}
        if style.get('size'):
            knobs['size'] = style['size']
        plotItem.titleLabel.setText(style.get('text', '') or
                                    plotItem.titleLabel.text or '', **knobs)
        return
    axis = plotItem.getAxis(side)
    axisStyle = dict(axis.labelStyle)
    axisStyle['font-weight'] = 'bold' if bold else 'normal'
    axisStyle['font-style'] = 'italic' if italic else 'normal'
    if style.get('size'):
        axisStyle['font-size'] = style['size']
    axis.setLabel(style.get('text', '') or axis.labelText, **axisStyle)


def _flag(answered):
    return '1' if answered else '0'


class QVizPlotStyling(object):
    """The *Configure Plot* entry of one window, and what a hand changed there."""

    def __init__(self, source):
        """
        Arguments:
            source (object) : the frame or panel that draws the traces. It answers
                the dialogue's three questions -- `styleCurves()`, `styleText()`,
                `styleMargins()` -- and `tracesForStyling()`, the [(treeNode, index,
                curve)] this window draws.
        """
        self._source = weakref.ref(source)
        # {target: None} in the order touched. A target is a curve, or the side of
        # a line of text; one dict per source, because two panels of a table both
        # have a left axis and their styles are two different questions.
        self._touched = {}
        self._before = None
        self.dialog = None

    # ---------------------------------------------------------------------- menu

    def addMenuEntry(self, menu):
        """Hang the entry on that view box's menu, and answer for it."""
        action = QAction(ENTRY, menu)
        action.triggered.connect(self.show)
        menu.addAction(action)
        return action

    def show(self):
        """Open the window on this source; None once the source is gone."""
        source = self._source()
        if source is None:
            return None
        self._before = dict(self._touched)
        self.dialog = QVizPlotStyleUI(styleSource=source, onChange=self._mark,
                                      onReject=self._rolledBack)
        self.dialog.show()
        return self.dialog

    # ----------------------------------------------------------------- the record

    def _mark(self, target):
        self._touched[target] = None

    def _rolledBack(self):
        """Cancel said nothing was changed: the record goes back with the values."""
        self._touched = dict(self._before or {})

    def touched(self, curve):
        return curve in self._touched

    def mark(self, target):
        """Record a target as hand-set, from outside a window: a session replay."""
        self._touched[target] = None

    def styledCurves(self):
        """The traces a hand was on, as [(treeNode, index, {attribute: value})].

        Read off the live curves, and only for the traces this window still draws:
        a curve the figure took back out is not styled any more, and one the
        palette coloured is not hand-styled.
        """
        source = self._source()
        if source is None:
            return []
        return [(treeNode, index, curveStyle(curve))
                for treeNode, index, curve in source.tracesForStyling()
                if curve in self._touched]

    def styledText(self):
        """The lines of text a hand was on, as [(side, {attribute: value})]."""
        source = self._source()
        if source is None:
            return []
        plotItem = source.styleText()
        return [(side, textStyle(plotItem, side))
                for side in self._touched if isinstance(side, str)]

    # ------------------------------------------------------------------- replaying

    def replayCurves(self, styles):
        """Put recorded styles back on the traces this source draws.

        `styles` is [(treeNode, index, {attribute: value})], as a session recorded
        them for the window. A trace this source does not draw any more costs its
        entry and nothing else -- the caller is the one that knows which quantity
        named it, and says so. A trace that comes back styled is recorded as
        hand-styled, so saving the session again keeps it.
        """
        source = self._source()
        if source is None:
            return 0
        drawn = {}
        for treeNode, index, curve in source.tracesForStyling():
            key = styleKey(treeNode)
            if key is not None:
                drawn[(key, index)] = curve
        applied = 0
        for treeNode, index, style in styles:
            curve = drawn.get((styleKey(treeNode), index))
            if curve is None:
                continue
            applyCurveStyle(curve, style)
            self._touched[curve] = None
            applied += 1
        return applied

    def replayText(self, styles):
        """Put recorded text styles back on this source's title and axis labels."""
        source = self._source()
        if source is None:
            return 0
        plotItem = source.styleText()
        for side, style in styles:
            applyTextStyle(plotItem, side, style)
            self._touched[side] = None
        return len(styles)


def sourcesOf(window):
    """Every object of this window that answers the styling contract.

    A figure of curves is its own source. A table and a stacked window answer one
    panel at a time: each panel owns its plot item, its traces and its record, and
    the dialogue opened on a panel styles that panel alone.
    """
    panels = getattr(window, 'panels', None)
    if panels is not None:
        return list(panels())
    return [window]


def styleKey(treeNode):
    """What a styled trace is filed under: the path of its quantity and its run.

    The identity the session file writes, and deliberately not the node object:
    the frame keeps the node it drew with, `figToNodes` keeps the one the gesture
    named, and a Table Plot View fills its panels from a configuration file, so the
    three are not guaranteed to be one and the same object. None for anything that
    cannot answer -- an entry naming no quantity matches no trace, and the figure's
    own labels are the only thing a None key is asked to match.
    """
    getPath = getattr(treeNode, 'getPath', None)
    getOccurrence = getattr(treeNode, 'getOccurrence', None)
    if getPath is None or getOccurrence is None:
        return None
    return getPath(), getOccurrence()


def styledTraces(window):
    """[(treeNode, index, {attribute: value})] for every trace a hand coloured."""
    return [entry for source in stylableSources(window)
            for entry in source.styling.styledCurves()]


def styledText(window):
    """[(treeNode, side, {attribute: value})] for every label a hand styled.

    `treeNode` is None for the title and the axes of the window itself -- a figure
    of curves has one plot and one set of labels -- and the quantity a panel draws
    for the labels of that panel. That is exactly where the session file writes
    them: a `<TextStyle>` under the `<Figure>`, or under the `<Quantity>` whose
    panel it belongs to.
    """
    return [(getattr(source, 'treeNode', None), side, style)
            for source in stylableSources(window)
            for side, style in source.styling.styledText()]


def replayCurves(window, styles):
    """Apply recorded trace styles across a window; returns how many landed."""
    return sum(source.styling.replayCurves(styles)
               for source in stylableSources(window))


def replayText(window, styles):
    """Apply recorded label styles across a window; returns how many landed.

    Each source takes the entries that name it: the window itself for those whose
    quantity is None -- a figure of curves has one plot and one set of labels --
    and a panel for those naming the quantity that panel draws.
    """
    return sum(
        source.styling.replayText([(side, style)
                                   for node, side, style in styles
                                   if styleKey(node)
                                   == styleKey(getattr(source, 'treeNode',
                                                       None))])
        for source in stylableSources(window))


def stylableSources(window):
    """The sources of this window that keep a record of a hand.

    A picture figure draws images and no traces, and a window a plugin drew is not
    one of these four at all: neither carries a record, and a session that walks
    every window it has meets them on the way.
    """
    return [source for source in sourcesOf(window)
            if getattr(source, 'styling', None) is not None]
