# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Styling a plot by hand: the **Configure Plot** dialogue.

The manual documents it under *Plot Configuration and Customization*: a window
listing the plots of a plot display and the properties that can be changed by
hand. It is offered by the plots of the Profiles plugin, and the manual says
twice that a :guilabel:`Table Plot View` panel and a :guilabel:`Stacked Plot
View` display do not offer it.

The contract with the caller is **asked, not guessed**. The view box that offers
the entry answers three questions, and each answer decides what is on screen:

    styleCurves()    the curves hand styling may change
    styleText()      the plot item holding the title and the axis labels
    styleMargins()   the layout whose margins to set, or None for no section

The dialogue this replaces walked `viewBox.qWidgetParent.objectName()` through
four branches -- `TablePlotView`, `StackedPlotView`, `QVizPlugin`, and a last one
reading `qWidgetParent.pgPlotWidget.centralWidget.legend`. Measured on the only
caller there is: that object name answers **'QVizPlugin'**, so two branches never
run and the fourth is dead for every frame in the package -- `hasattr(
qWidgetParent, 'pgPlotWidget')` answers **False**. Asked directly instead, the
same window hands over its `PlotItem`, and `listDataItems()` answers its curves:
measured on a panel holding 4 curves plus an `ErrorBarItem`, an `InfiniteLine`
and a `FillBetweenItem`, it answers **4** `PlotDataItem`s and none of the three
decorations -- so the hand-written list of item types to skip goes with it.

Three measured defects it carried, and this file does not.

**Every row edited the last curve.** The old dialogue kept one flat dictionary,
`eventsData`, whose keys were rewritten once per row in the building loop, and
all eight `updatePDItem*` methods read that dictionary back. Measured with **3**
curves in one view box and **9** colour buttons on the tab: changing the first
row's colour left the first curve *and* the second curve untouched -- every row
wrote the item the loop had reached last. Here one `CurveStyle` object per curve
owns its curve and its widgets.

**The header did not describe the columns.** The header was chosen from the
caller's *name* -- eight labels, the first being `Line`, for the legend marker --
while the row was built from the legend the caller actually had, and the plugin's
panels have none: measured, `plotItem.legend` answers **None** on all **41** of
them. So the first widget of a row, a colour button, landed under the label
`Line`, and every label was one column off. Here one list of labels builds the
header and the rows from the same order, so they cannot disagree.

**Cancel left everything changed.** Every change was applied live, and nothing
recorded what came before: measured, a margin written through the dialogue read
back **(40, 9, 9, 9)** after `reject()`. Here each section reads what it is about
to change when the window opens, and `reject()` writes it back.

Margins are asked of the window, which is what knows where its panels live.
Measured on the plugin's own `QVizTablePlotView`: `centralWidget` **is** `ci`; the
layout that positions the panels is `ci.layout`, a `QGraphicsGridLayout` reading
**(9, 9, 9, 9)** on a fresh window, and setting its left margin to 120 moved the
three panels from x = 9.0, 305.0, 601.0 to 120.0, 379.0, 638.0. The name the old
code probed for, `centralLayout`, answers **`RuntimeError: Internal C++ object
(QGraphicsGridLayout) already deleted`** -- pyqtgraph builds that layout for a
central widget `GraphicsLayoutWidget` then throws away when it installs its own
`ci`. The old code tested `hasattr(plotWidget, 'centralLayout')`, got **True**,
and wrote `centralWidget.layout`: right by luck, through a dangling name. A
window that has no panel layout answers None and gets no section, in place of the
bare `QWidget()` the old fallback handed back.

The Legend section is gone, and with it `SampleCopyFromLegend` -- **339** lines.
Measured, the dialogue answers **3** sections on its only caller, because there
is no legend to copy a marker from, and no figure offers the entry at all.
Nothing documented dies: `doc/source` names no legend styling, and what the
legend says is the curve's own label, which no section here touches.
"""

import pyqtgraph as pg

from PySide6.QtCore import Qt
from PySide6.QtGui import QPen
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog,
                               QDialogButtonBox, QDoubleSpinBox, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QScrollArea, QSpinBox, QTabWidget, QVBoxLayout,
                               QWidget)

from imasviz.VizUtils import GlobalIcons, GlobalPgSymbols, GlobalQtStyles

# What pyqtgraph leaves a fresh panel layout at, measured (9.0, 9.0, 9.0, 9.0) on
# the plugin's own window. The old dialogue called (10, 10, 10, 10) the default:
# a number nothing in the package answers.
DEFAULT_MARGINS = (9, 9, 9, 9)

# The size pyqtgraph draws a label at when its style says nothing. Measured on a
# fresh axis: `labelStyle` answers {'color': '#969696'} and no font-size at all.
DEFAULT_FONT_SIZE = 15

# The sides the dialogue offers an axis label for, in the order it shows them.
AXIS_SIDES = ('bottom', 'left', 'top', 'right')

# The columns of the curve section, after the curve's own name. One list, read
# both for the header and for the row: the old dialogue chose its header from the
# caller's name and built its row from what the caller had, and the two differed
# by a column.
CURVE_COLUMNS = ('Color', 'Style', 'Thickness', 'Symbol', 'Symbol Size',
                 'Symbol Color', 'Symbol Outline Color')


def penOf(curve):
    """The pen a curve is drawn with, always a real `QPen`.

    A curve drawn without a pen carries pyqtgraph's instance default, the plain
    tuple (200, 200, 200) -- measured. The old dialogue read `opts['pen'].color()`
    straight off that and died with `AttributeError: 'tuple' object has no
    attribute 'color'` on the first such curve.
    """
    pen = curve.opts['pen']
    if isinstance(pen, QPen):
        return QPen(pen)
    return pg.mkPen(pen) if pen is not None else QPen()


def styleNameOf(pen):
    """The name `GlobalQtStyles` gives this pen's style."""
    for name, style in GlobalQtStyles.stylesDict.items():
        if pen.style() == style:
            return name
    return next(iter(GlobalQtStyles.stylesDict))


def symbolNameOf(symbol):
    """The name `GlobalPgSymbols` gives this symbol, `'None'` when unmapped.

    A curve drawn without a symbol answers `opts['symbol'] == None`, which the
    dictionary does map -- to `'None'` -- but the old code reached for
    `list(values).index(symbol)`, which answers a `ValueError` for any symbol it
    has never seen, and named nothing.
    """
    for name, value in GlobalPgSymbols.symbolsDict.items():
        if value == symbol:
            return name
    return 'None'


def fontSizeOf(style):
    """The size a label carries, `DEFAULT_FONT_SIZE` when it says nothing.

    A title carries it under `size` in its own opts, an axis under `font-size` in
    a CSS-ish style. Measured on a fresh panel: the title answers '11pt', the
    axis answers `{'color': '#969696'}` and no size at all. Reading only one of
    the two keys shows a number the label is not drawn at, and the first change
    jumps the label to it.
    """
    size = style.get('font-size', style.get('size', DEFAULT_FONT_SIZE))
    try:
        return int(float(str(size).rstrip('pxpt')))
    except ValueError:
        return DEFAULT_FONT_SIZE


class CurveStyle(object):
    """One curve, and the seven properties the dialogue may change on it.

    One of these per drawn curve -- and that is the point: the old dialogue held
    one flat dictionary for the whole tab, written once per row and read back by
    every callback, so all rows wrote the same, last, curve.
    """

    def __init__(self, curve, parent):
        self.curve = curve
        # What this curve looked like when the window opened, so Cancel can put
        # it back -- the changes are applied live, as the manual describes them.
        pen = penOf(curve)
        self.original = {
            'pen': QPen(pen),
            'symbol': curve.opts['symbol'],
            'symbolSize': curve.opts['symbolSize'],
            'symbolBrush': curve.opts['symbolBrush'],
            'symbolPen': curve.opts['symbolPen'],
        }

        self.name = QLabel(str(curve.opts.get('name') or ''), parent)
        self.name.setMinimumWidth(120)

        self.colorButton = pg.ColorButton(color=pen.color(), parent=parent)
        self.colorButton.sigColorChanging.connect(self.setColour)

        self.styleBox = QComboBox(parent)
        self.styleBox.addItems(list(GlobalQtStyles.stylesDict.keys()))
        self.styleBox.setCurrentText(styleNameOf(pen))
        self.styleBox.currentIndexChanged.connect(self.setStyle)

        self.widthBox = QDoubleSpinBox(parent)
        self.widthBox.setMaximum(50.0)
        self.widthBox.setMinimum(0.0)
        self.widthBox.setSingleStep(0.5)
        self.widthBox.setValue(pen.width())
        self.widthBox.valueChanged.connect(self.setWidth)

        self.symbolBox = QComboBox(parent)
        self.symbolBox.addItems(list(GlobalPgSymbols.symbolsDict.keys()))
        self.symbolBox.setCurrentText(symbolNameOf(curve.opts['symbol']))
        self.symbolBox.currentIndexChanged.connect(self.setSymbol)

        self.symbolSizeBox = QDoubleSpinBox(parent)
        self.symbolSizeBox.setMaximum(100.0)
        self.symbolSizeBox.setMinimum(0.0)
        self.symbolSizeBox.setSingleStep(0.5)
        self.symbolSizeBox.setValue(curve.opts['symbolSize'])
        self.symbolSizeBox.valueChanged.connect(self.setSymbolSize)

        self.symbolColorButton = pg.ColorButton(
            color=pg.mkBrush(curve.opts['symbolBrush']).color(), parent=parent)
        self.symbolColorButton.sigColorChanging.connect(self.setSymbolBrush)

        self.symbolOutlineButton = pg.ColorButton(
            color=pg.mkPen(curve.opts['symbolPen']).color(), parent=parent)
        self.symbolOutlineButton.sigColorChanging.connect(self.setSymbolPen)

    def cells(self):
        """The widgets of this curve's row, in `CURVE_COLUMNS` order."""
        return [self.colorButton, self.styleBox, self.widthBox, self.symbolBox,
                self.symbolSizeBox, self.symbolColorButton,
                self.symbolOutlineButton]

    # -- writing: one property, this curve, live --------------------------

    def setColour(self):
        pen = penOf(self.curve)
        pen.setColor(self.colorButton.color())
        self.curve.setPen(pen)

    def setStyle(self):
        pen = penOf(self.curve)
        pen.setStyle(GlobalQtStyles.stylesDict[self.styleBox.currentText()])
        self.curve.setPen(pen)

    def setWidth(self):
        pen = penOf(self.curve)
        pen.setWidth(self.widthBox.value())
        self.curve.setPen(pen)

    def setSymbol(self):
        self.curve.setSymbol(GlobalPgSymbols.symbolsDict[
            self.symbolBox.currentText()])

    def setSymbolSize(self):
        self.curve.setSymbolSize(self.symbolSizeBox.value())

    def setSymbolBrush(self):
        self.curve.setSymbolBrush(self.symbolColorButton.color())

    def setSymbolPen(self):
        self.curve.setSymbolPen(self.symbolOutlineButton.color())

    def restore(self):
        """Put back the pen and the symbols this curve had on opening."""
        self.curve.setPen(QPen(self.original['pen']))
        self.curve.setSymbol(self.original['symbol'])
        self.curve.setSymbolSize(self.original['symbolSize'])
        self.curve.setSymbolBrush(self.original['symbolBrush'])
        self.curve.setSymbolPen(self.original['symbolPen'])


class TextLabel(QWidget):
    """One line of text and its three style knobs, over a heading.

    A plot title and an axis label are the same question -- what text, bold,
    italic, what size -- with different ways in. The subclass answers `write()`
    and `restore()`; the widgets and their state live here once.
    """

    COLUMNS = ('Text', 'Bold', 'Italic', 'Size')

    def __init__(self, heading, text, style, parent=None):
        super(TextLabel, self).__init__(parent)

        self.originalText = text
        self.originalStyle = dict(style)

        self.lineEdit = QLineEdit(text, self)
        self.lineEdit.textChanged.connect(self.write)

        self.boldButton = QPushButton('', self)
        self.boldButton.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'bold'))
        self.boldButton.setCheckable(True)
        self.boldButton.toggled.connect(self.write)

        self.italicButton = QPushButton('', self)
        self.italicButton.setIcon(
            GlobalIcons.getCustomQIcon(QApplication, 'italic'))
        self.italicButton.setCheckable(True)
        self.italicButton.toggled.connect(self.write)

        self.sizeBox = QSpinBox(self)
        self.sizeBox.setMaximum(100)
        self.sizeBox.setMinimum(1)
        self.sizeBox.setSuffix('px')
        self.sizeBox.setValue(fontSizeOf(style))
        self.sizeBox.valueChanged.connect(self.write)

        self.setUpButtons(style)

        title = QLabel(heading, self)
        title.setMinimumWidth(110)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(title)
        layout.addWidget(self.lineEdit)
        layout.addWidget(self.boldButton)
        layout.addWidget(self.italicButton)
        layout.addWidget(self.sizeBox)

    def setUpButtons(self, style):
        """How this label says bold and italic, which is not one way.

        A title carries `bold`/`italic` booleans in its own opts; an axis carries
        `font-weight`/`font-style` in a CSS-ish style. Measured on a fresh axis,
        that style answers only `{'color': '#969696'}` -- so neither knob starts
        pressed, which is what the label really looks like.
        """
        self.boldButton.setChecked(bool(style.get('bold')))
        self.italicButton.setChecked(bool(style.get('italic')))

    def text(self):
        return self.lineEdit.text()

    def size(self):
        return '%dpx' % self.sizeBox.value()

    def bold(self):
        return self.boldButton.isChecked()

    def italic(self):
        return self.italicButton.isChecked()

    def write(self):
        raise NotImplementedError

    def restore(self):
        raise NotImplementedError


class TitleLabel(TextLabel):
    """The plot's own title."""

    def __init__(self, titleLabel, parent=None):
        TextLabel.__init__(self, 'Title', titleLabel.text, titleLabel.opts,
                           parent)
        self.titleLabel = titleLabel

    def write(self):
        """Re-set the text with the style: a style change only lands with it.

        Measured on the dialogue this replaces, which had found the same thing:
        setting the attribute alone leaves the label painted as it was until the
        text is set again.
        """
        self.titleLabel.setText(self.text(), size=self.size(),
                                bold=self.bold(), italic=self.italic())

    def restore(self):
        """Write the title back as it was, knobs included.

        `LabelItem.setText(text, **kwargs)` updates the opts it is given and
        leaves the others alone. Measured on a fresh panel, those opts are
        `{'color': None, 'justify': 'center', 'size': '11pt'}` -- no `bold`, no
        `italic` -- so handing that dict back left a title bold after Cancel,
        which is what a probe measured before these two lines forced the knobs.
        """
        style = dict(self.originalStyle)
        style.setdefault('bold', False)
        style.setdefault('italic', False)
        self.titleLabel.setText(self.originalText, **style)


class AxisLabel(TextLabel):
    """The label of one axis, written the way pyqtgraph reads a label style."""

    def setUpButtons(self, style):
        self.boldButton.setChecked(style.get('font-weight') == 'bold')
        self.italicButton.setChecked(style.get('font-style') == 'italic')

    def __init__(self, axis, side, parent=None):
        TextLabel.__init__(self, 'Axis %s' % side.capitalize(), axis.labelText,
                           axis.labelStyle, parent)
        self.axis = axis

    def write(self):
        style = dict(self.axis.labelStyle)
        style['font-weight'] = 'bold' if self.bold() else 'normal'
        style['font-style'] = 'italic' if self.italic() else 'normal'
        style['font-size'] = self.size()
        self.axis.setLabel(self.text(), **style)

    def restore(self):
        self.axis.setLabel(self.originalText, **self.originalStyle)


class QVizPlotStyleUI(QDialog):
    """The Configure Plot dialogue, built from what the caller answers.

    Arguments:
        viewBox (pg.ViewBox) : the view box that offered the entry. It answers
                               `styleCurves()`, `styleText()` and
                               `styleMargins()`, as the Profiles plugin's own
                               `CustomizedViewBox` does.
    """

    def __init__(self, viewBox, parent=None, size=(1000, 400)):
        super(QVizPlotStyleUI, self).__init__(parent)

        self.viewBox = viewBox
        self.curves = [CurveStyle(curve, self) for curve in viewBox.styleCurves()]
        self.plotItem = viewBox.styleText()
        self.marginsLayout = viewBox.styleMargins()

        self.setObjectName("QVizPlotStyleUI")
        heading = self.plotItem.titleLabel.text or ''
        self.setWindowTitle('Configure Plot - %s' % heading if heading
                            else 'Configure Plot')
        self.resize(*size)

        self.titleEditor = TitleLabel(self.plotItem.titleLabel, self)
        self.axisEditors = self.labelsOfAxes()
        self.marginBoxes = None

        layout = QVBoxLayout(self)
        self.tabWidget = QTabWidget(self)
        self.tabWidget.addTab(self.curveTab(), 'Curve Properties')
        self.tabWidget.addTab(self.textTab(), 'Text Properties')
        if self.marginsLayout is not None:
            self.tabWidget.addTab(self.marginTab(), 'Plot Design Properties')
        layout.addWidget(self.tabWidget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                                   Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # -- what the caller answers, turned into sections --------------------

    def labelsOfAxes(self):
        """The axes this plot draws a label for.

        Filtered on what the axis really draws, not on the four names: measured
        on a plugin panel, all four axes exist, but the top and the right answer
        an empty `labelText` and a hidden label, so two rows would describe
        nothing -- and the old dialogue offered all four whatever the panel was.
        """
        editors = []
        for side in AXIS_SIDES:
            axis = self.plotItem.getAxis(side)
            if not axis.labelText and not axis.label.isVisible():
                continue
            editors.append(AxisLabel(axis, side, self))
        return editors

    def curveTab(self):
        """One row per curve, and a header built from those same rows."""
        tab = QWidget(self)
        outer = QGridLayout(tab)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(tab)
        scroll.setWidgetResizable(True)
        content = QWidget(scroll)
        grid = QGridLayout(content)

        name = QLabel('Curve')
        name.setMinimumWidth(120)
        grid.addWidget(name, 0, 0)
        for column, label in enumerate(CURVE_COLUMNS):
            grid.addWidget(QLabel(label), 0, column + 1)
        for row, curve in enumerate(self.curves):
            grid.addWidget(curve.name, row + 1, 0)
            for column, cell in enumerate(curve.cells()):
                grid.addWidget(cell, row + 1, column + 1)

        content.setLayout(grid)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        return tab

    def textTab(self):
        """The title, then the axes that carry a label."""
        tab = QWidget(self)
        layout = QGridLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)

        grid = QGridLayout()
        grid.addWidget(QLabel('Property'), 0, 0)
        for column, label in enumerate(TextLabel.COLUMNS):
            grid.addWidget(QLabel(label), 0, column + 1)
        grid.addWidget(self.titleEditor, 1, 0, 1, 5)
        for row, editor in enumerate(self.axisEditors):
            grid.addWidget(editor, row + 2, 0, 1, 5)

        layout.addLayout(grid, 0, 0)
        return tab

    def marginTab(self):
        """The margins of the layout the caller named, with two ways back."""
        tab = QWidget(self)
        layout = QGridLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)

        self.originalMargins = self.marginsLayout.getContentsMargins()
        self.marginBoxes = {}
        for column, side in enumerate(('Left', 'Top', 'Right', 'Bottom')):
            box = QSpinBox(tab)
            box.setMaximum(250)
            box.setMinimum(0)
            box.setValue(int(self.originalMargins[column]))
            box.valueChanged.connect(self.setMargins)
            self.marginBoxes[side] = box
            layout.addWidget(QLabel(side), 0, column)
            layout.addWidget(box, 1, column)

        self.previousButton = QPushButton('Restore previous', tab)
        self.previousButton.clicked.connect(self.restorePreviousMargins)
        layout.addWidget(self.previousButton, 2, 0, 1, 2)

        self.defaultButton = QPushButton('Restore default', tab)
        self.defaultButton.clicked.connect(self.restoreDefaultMargins)
        layout.addWidget(self.defaultButton, 2, 2, 1, 2)
        return tab

    # -- margins -----------------------------------------------------------

    def setMargins(self):
        self.marginsLayout.setContentsMargins(
            self.marginBoxes['Left'].value(), self.marginBoxes['Top'].value(),
            self.marginBoxes['Right'].value(), self.marginBoxes['Bottom'].value())

    def showMargins(self, margins):
        for side, value in zip(('Left', 'Top', 'Right', 'Bottom'), margins):
            self.marginBoxes[side].setValue(int(value))

    def restorePreviousMargins(self):
        self.showMargins(self.originalMargins)

    def restoreDefaultMargins(self):
        self.showMargins(DEFAULT_MARGINS)

    # -- Cancel means Cancel -----------------------------------------------

    def reject(self):
        """Write back what each section found when the window opened.

        Measured on the dialogue this replaces: `reject()` changed nothing, so a
        margin written through it was still there afterwards -- the changes are
        live, and without this the button only closes the window.
        """
        for curve in self.curves:
            curve.restore()
        self.titleEditor.restore()
        for editor in self.axisEditors:
            editor.restore()
        if self.marginsLayout is not None:
            self.showMargins(self.originalMargins)
        super(QVizPlotStyleUI, self).reject()
