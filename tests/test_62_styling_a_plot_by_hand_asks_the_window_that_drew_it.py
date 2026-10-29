# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Styling a plot by hand: what the Configure Plot dialogue is asked, and what
Cancel gives back.

The manual documents the entry under *Plot Configuration and Customization*, and
it belongs to the plots of the Profiles plugin. The window those plots live in is
the plugin's own `QVizTablePlotView`, so these tests build that window empty and
add the curves by hand: every number here is about the dialogue and its contract
with the caller, not about what a case answers.

Three defects the replaced dialogue carried, pinned here so they cannot come
back.

**All rows wrote one curve.** The old tab kept a single flat `eventsData`
dictionary, rewritten once per row in the building loop, and its eight
`updatePDItem*` methods read that back. Measured with 3 curves in one view box:
changing the first row's colour left the first curve *and* the second untouched.

**The header did not describe the row.** Eight header labels, chosen from the
caller's *name*, for seven widgets -- measured, the first widget of a row, a
colour button, sat under the label `Line`, because the caller has no legend
marker: `plotItem.legend` answers None on all **41** of the plugin's panels.

**Cancel changed nothing.** Measured: a margin written through the old dialogue
read back `(40.0, 9.0, 9.0, 9.0)` after `reject()` -- the changes are live, and
nothing had recorded what came before.

And the contract: the view box answers `styleCurves()`, `styleText()` and
`styleMargins()`. The old dialogue asked none of that; it walked
`qWidgetParent.objectName()` through four branches -- `TablePlotView`,
`StackedPlotView`, `QVizPlugin` and a dead `else` reading `pgPlotWidget`, an
attribute no frame of the package has (measured False). The only caller answers
**'QVizPlugin'**, so two of the four never ran and one cannot.
"""

import os

import pytest

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from imasviz.VizGUI.VizPlot.QVizPlotStyleUI import (AXIS_SIDES,
                                                    CURVE_COLUMNS,
                                                    DEFAULT_MARGINS,
                                                    QVizPlotStyleUI,
                                                    fontSizeOf, penOf,
                                                    styleNameOf, symbolNameOf)
from imasviz.VizPlugins.viz_Profiles.viz_profiles.CustomizedViewBox \
    import CustomizedViewBox
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizTablePlotView \
    import QVizTablePlotView
from imasviz.VizUtils import GlobalPgSymbols, GlobalQtStyles

from support import ownership

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# What pyqtgraph leaves a curve drawn without a pen at, measured, and what a
# fresh axis carries -- a colour and no size, no weight, no style.
LIBRARY_PEN_RGB = (200, 200, 200)
FRESH_AXIS_STYLE = {'color': '#969696'}


class NoPanelLayout:
    """A window that answers no layout for its panels."""

    def panelLayout(self):
        return None


def pluginPanel(table=None, withLayout=True):
    """One panel of the plugin's own window, with a curve drawn the plugin's way.

    The view box has to be the plugin's subclass, built by hand: `addViewBox()`
    is pyqtgraph's and answers a plain `ViewBox`, which answers none of the three
    questions the dialogue asks.
    """
    if table is None:
        table = ownership.keep(QVizTablePlotView(None, None, 1, 'profiles_1d',
                                                 -1))
    box = CustomizedViewBox(qWidgetParent=table if withLayout else NoPanelLayout(),
                            imas_viz_api=None)
    plotItem = table.addPlot(x=[0, 1, 2], y=[1, 2, 3], title='probe panel',
                             viewBox=box)
    # The plugin does this itself at the end of its `plot()`; pyqtgraph 0.13.7
    # gives a ViewBox no `plotItem` of its own.
    box.plotItem = plotItem
    box.plotAxis = 'TIME'
    plotItem.setLabel('left', 'the left label')
    plotItem.setLabel('bottom', 'the bottom label')
    return table, box, plotItem


def curveNames(dialog):
    return [curve.opts.get('name') for curve in
            [style.curve for style in dialog.curves]]


def headerLabels(dialog):
    """The labels of the curve section's header row, left to right."""
    grid = gridOf(dialog)
    return [grid.itemAtPosition(0, column).widget().text()
            for column in range(10)
            if grid.itemAtPosition(0, column) is not None
            and isinstance(grid.itemAtPosition(0, column).widget(), QLabel)]


def gridOf(dialog):
    """The grid the rows of the curve section live in."""
    return dialog.curves[0].cells()[0].parentWidget().layout()


def rowCells(dialog, row):
    grid = gridOf(dialog)
    return [grid.itemAtPosition(row, column).widget()
            for column in range(10)
            if grid.itemAtPosition(row, column) is not None
            and grid.itemAtPosition(row, column).widget() is not None]


def penRGB(curve):
    return penOf(curve).color().getRgb()[:3]


def rowOf(dialog, curve):
    """The row of one curve, taken by identity.

    The panel `pluginPanel` builds already holds a curve -- the one `addPlot`
    drew -- so a row is never at a position counted from the curve added later.
    """
    rows = [style for style in dialog.curves if style.curve is curve]
    assert len(rows) == 1, 'one row per curve: %d for %r' % (len(rows), curve)
    return rows[0]


def tabsOf(dialog):
    return [dialog.tabWidget.tabText(index)
            for index in range(dialog.tabWidget.count())]


# -- the contract: three answers, asked of the caller ----------------------

@pytest.mark.ui
def test_the_window_that_drew_the_curve_answers_the_three_questions(qapp):
    """`styleCurves` / `styleText` / `styleMargins`, on the plugin's own classes.

    Measured on the window the manual describes: the third answer **is**
    `ci.layout`, the grid that positions the panels.
    """
    table, box, plotItem = pluginPanel()
    extra = plotItem.plot([4, 5, 6], pen=pg.mkPen((128, 0, 0)), name='extra')

    assert box.styleCurves() == list(plotItem.listDataItems())
    assert len(box.styleCurves()) == 2
    assert box.styleText() is plotItem
    assert box.styleMargins() is table.ci.layout


@pytest.mark.ui
def test_a_decoration_of_the_plot_is_not_offered_as_a_curve(qapp):
    """Error bars and the band are drawn on the panel, not styled as curves.

    `listDataItems()` answers the `PlotDataItem`s and nothing else: measured on a
    panel holding 4 curves plus an `ErrorBarItem`, an `InfiniteLine` and a
    `FillBetweenItem` -- all three of those in `addedItems` -- it answers **4**.
    So the answer needs no list of item types to skip, and cannot offer a
    decoration as if it were one of the traces.
    """
    table, box, plotItem = pluginPanel()
    plotItem.plot([1, 2, 3], name='only')
    line = pg.InfiniteLine(pos=1.0)
    plotItem.addItem(line)
    # Arrays, not lists: `ErrorBarItem.paint` divides `height` into the samples,
    # and a list there raises inside a paint event -- where nothing catches it.
    error = pg.ErrorBarItem(x=np.array([1., 2., 3.]), y=np.array([1., 2., 3.]),
                            height=np.array([.1, .1, .1]))
    plotItem.addItem(error)

    assert line in box.addedItems and error in box.addedItems, \
        'the two decorations are in the scene'
    # The replaced tab built one row per `viewBox.addedItems` entry, and that
    # list holds the decorations: measured on a panel holding 5 curves and 3 of
    # them, it answers **8**, where `listDataItems()` answers **5**. Here the
    # answer is the curves and nothing else, so no skip-list is needed.
    assert len(box.addedItems) == 4 and len(box.styleCurves()) == 2
    assert box.styleCurves() == list(plotItem.listDataItems())
    assert line not in box.styleCurves() and error not in box.styleCurves()


@pytest.mark.ui
def test_a_window_with_no_panel_layout_gets_no_margins_section(qapp):
    """In place of the bare `QWidget()` the old fallback handed back.

    Measured: three sections when the window answers a layout, two when it
    answers None -- and the two sections that stay are the ones that need
    nothing from a layout.
    """
    table, laidOut, _ = pluginPanel()
    _, bare, _ = pluginPanel(table=table, withLayout=False)

    assert tabsOf(QVizPlotStyleUI(styleSource=laidOut)) == \
        ['Curve Properties', 'Text Properties', 'Plot Design Properties']
    assert tabsOf(QVizPlotStyleUI(styleSource=bare)) == \
        ['Curve Properties', 'Text Properties']


# -- the curve section -----------------------------------------------------

@pytest.mark.ui
def test_the_header_labels_are_the_columns_of_a_row(qapp):
    """One list builds both, so they cannot be a column apart.

    Measured on the replaced dialogue: an eight-label header, the first reading
    `Line`, over a row whose first widget was a colour button -- the caller it
    was built for has no legend to take a marker from.
    """
    table, box, plotItem = pluginPanel()
    plotItem.plot([1, 2, 3], name='first')
    dialog = QVizPlotStyleUI(styleSource=box)

    assert headerLabels(dialog) == ['Curve'] + list(CURVE_COLUMNS)
    for row in range(1, len(dialog.curves) + 1):
        assert len(rowCells(dialog, row)) == len(CURVE_COLUMNS) + 1

    cells = dialog.curves[0].cells()
    assert [type(cell).__name__ for cell in cells[:1]] == ['ColorButton']
    assert len(cells) == len(CURVE_COLUMNS)


@pytest.mark.ui
def test_a_curve_drawn_without_a_pen_still_opens_the_dialogue(qapp):
    """`penOf`, and the crash it stands between the user and.

    Measured on the replaced dialogue, on exactly this panel: it read
    `pdItem.opts['pen'].color()` and died with `AttributeError: 'tuple' object
    has no attribute 'color'` -- pyqtgraph leaves a pen-less curve the plain
    tuple (200, 200, 200).
    """
    table, box, plotItem = pluginPanel()
    unstyled = plotItem.plot([7, 8, 9], name='no pen given')
    assert unstyled.opts['pen'] == LIBRARY_PEN_RGB

    dialog = QVizPlotStyleUI(styleSource=box)
    row = [style for style in dialog.curves if style.curve is unstyled][0]

    assert penOf(unstyled).color().getRgb()[:3] == LIBRARY_PEN_RGB
    assert row.colorButton.color().getRgb()[:3] == LIBRARY_PEN_RGB
    assert row.styleBox.currentText() == 'Solid Line'
    assert row.symbolBox.currentText() == 'None'


@pytest.mark.ui
def test_a_row_changes_the_curve_it_is_the_row_of(qapp):
    """The defect the old flat dictionary left, pinned the other way round.

    Measured before: with 3 curves in one view box and 9 colour buttons on the
    tab, the first row changed neither the first nor the second curve -- every
    row wrote the item the building loop had reached last.
    """
    table, box, plotItem = pluginPanel()
    first = plotItem.plot([1, 2, 3], pen=pg.mkPen((0, 0, 128)), name='first')
    second = plotItem.plot([4, 5, 6], pen=pg.mkPen((128, 0, 0)), name='second')
    dialog = QVizPlotStyleUI(styleSource=box)

    rows = {}
    rows['first'] = rowOf(dialog, first)
    rows['second'] = rowOf(dialog, second)
    rows['first'].colorButton.setColor((7, 7, 7))
    rows['first'].colorButton.sigColorChanging.emit(rows['first'].colorButton)
    rows['second'].widthBox.setValue(9.0)

    assert penRGB(first) == (7, 7, 7), 'its own row did not reach its own curve'
    assert penRGB(second) == (128, 0, 0), 'a row reached another curve'
    assert penOf(second).width() == 9.0
    assert penOf(first).width() != 9.0


@pytest.mark.ui
def test_the_style_and_symbol_boxes_answer_the_shared_dictionaries(qapp):
    """The two lists are the package's, and the row reads and writes them.

    `Hide Line` is `Qt.NoPen` in `GlobalQtStyles`, and the `'None'` key of
    `GlobalPgSymbols` is `None` -- a symbol box that could not answer that would
    have no way to take a symbol back off.
    """
    table, box, plotItem = pluginPanel()
    curve = plotItem.plot([1, 2, 3], pen=pg.mkPen((0, 0, 128)), name='only')
    dialog = QVizPlotStyleUI(styleSource=box)
    row = rowOf(dialog, curve)

    assert list(GlobalQtStyles.stylesDict) == \
        [row.styleBox.itemText(index) for index in range(row.styleBox.count())]
    assert list(GlobalPgSymbols.symbolsDict) == \
        [row.symbolBox.itemText(index) for index in range(row.symbolBox.count())]

    row.styleBox.setCurrentText('Hide Line')
    assert penOf(curve).style() == Qt.PenStyle.NoPen
    row.symbolBox.setCurrentText('Triangle Down')
    assert curve.opts['symbol'] == GlobalPgSymbols.symbolsDict['Triangle Down']
    row.symbolSizeBox.setValue(24.0)
    assert curve.opts['symbolSize'] == 24.0


@pytest.mark.ui
def test_a_name_the_dictionaries_do_not_hold_answers_their_default(qapp):
    """`styleNameOf` and `symbolNameOf` refuse nothing.

    The replaced code took an index out of the dictionary's values, which answers
    a `ValueError` for a pen or a symbol it has never seen -- and named nothing.
    """
    assert styleNameOf(pg.mkPen((1, 2, 3), style=Qt.PenStyle.DotLine)) == \
        'Dot Line'
    assert styleNameOf(pg.mkPen((1, 2, 3), style=Qt.PenStyle.CustomDashLine)) \
        == next(iter(GlobalQtStyles.stylesDict))
    assert symbolNameOf('o') == 'O'
    assert symbolNameOf('no such symbol') == 'None'
    assert symbolNameOf(None) == 'None'


# -- the text section ------------------------------------------------------

@pytest.mark.ui
def test_the_axes_offered_are_the_ones_drawing_a_label(qapp):
    """Two rows on a plugin panel, not four.

    Measured: a `PlotItem` has four axes, but on the panel the plugin draws, the
    top and the right answer an empty `labelText` and a hidden label. The old
    tab built all four whatever the panel was, and one of its methods
    (`updateAxisBottomLabel`) raised `AttributeError` for a widget it never
    built.
    """
    table, box, plotItem = pluginPanel()
    dialog = QVizPlotStyleUI(styleSource=box)

    assert [side for side in AXIS_SIDES
            if plotItem.getAxis(side).labelText] == ['bottom', 'left']
    assert [editor.text() for editor in dialog.axisEditors] == \
        ['the bottom label', 'the left label']
    assert len(dialog.axisEditors) == 2


@pytest.mark.ui
def test_an_axis_label_is_written_the_way_pyqtgraph_reads_it(qapp):
    """The style lands as CSS on the label's own HTML.

    `AxisItem.setLabel` turns every keyword into a `<span style=...>` option and
    replaces `labelStyle` with them; a fresh axis carries a colour and nothing
    else, measured.
    """
    table, box, plotItem = pluginPanel()
    left = plotItem.getAxis('left')
    assert left.labelStyle == FRESH_AXIS_STYLE

    dialog = QVizPlotStyleUI(styleSource=box)
    editor = [row for row in dialog.axisEditors
              if row.text() == 'the left label'][0]
    editor.lineEdit.setText('renamed left')
    editor.sizeBox.setValue(26)
    editor.boldButton.toggle()

    assert left.labelText == 'renamed left'
    assert left.labelStyle['font-size'] == '26px'
    assert left.labelStyle['font-weight'] == 'bold'
    assert left.labelStyle['color'] == FRESH_AXIS_STYLE['color'], \
        'the style it started with is not thrown away'
    assert 'font-size:26px' in left.label.toHtml().replace(' ', '')


@pytest.mark.ui
def test_a_title_knows_its_size_and_hides_nothing_on_opening(qapp):
    """The knobs start as the label really looks, not as a stored default.

    Measured on a fresh panel: the title opts answer `{'color': None, 'justify':
    'center', 'size': '11pt'}` and an axis style answers only a colour, so
    neither the bold nor the italic button starts pressed -- and the size box
    reads 15 where the style says nothing, which is the size the replaced
    dialogue wrote into that style too.
    """
    table, box, plotItem = pluginPanel()
    dialog = QVizPlotStyleUI(styleSource=box)

    assert fontSizeOf(FRESH_AXIS_STYLE) == 15
    assert fontSizeOf({'font-size': '26px'}) == 26
    assert fontSizeOf({'size': '11pt'}) == 11
    assert dialog.titleEditor.sizeBox.value() == 11, \
        'the box reads the size the title is drawn at'
    assert dialog.titleEditor.boldButton.isChecked() is False
    assert dialog.titleEditor.italicButton.isChecked() is False


@pytest.mark.ui
def test_the_dialogue_is_named_for_the_plot_it_stands_on(qapp):
    """The panel's own title, not a number.

    The old window title read `viewBox.id`, an attribute the plugin set and
    nothing else in the package read; it is gone with it.
    """
    table, box, plotItem = pluginPanel()
    dialog = QVizPlotStyleUI(styleSource=box)

    assert dialog.windowTitle() == 'Configure Plot - probe panel'
    assert not hasattr(box, 'id')


# -- the margins section ---------------------------------------------------

@pytest.mark.ui
def test_the_margins_are_written_where_the_panels_live(qapp):
    """`ci.layout`, and the panels really move.

    Measured: a fresh window reads (9.0, 9.0, 9.0, 9.0), and a left margin of
    120 moved its panel from x = 9.0 to x = 120.0. The name the replaced code
    probed for, `centralLayout`, is a C++ object pyqtgraph deleted when it
    replaced its central widget: reading it answers `RuntimeError: Internal C++
    object (QGraphicsGridLayout) already deleted`.
    """
    table = ownership.keep(QVizTablePlotView(None, None, 1, 'profiles_1d', -1))
    table.resize(900, 600)
    table.show()
    qapp.processEvents()
    _, box, _ = pluginPanel(table=table)
    app = qapp
    app.processEvents()

    dialog = QVizPlotStyleUI(styleSource=box)
    layout = dialog.marginsLayout
    assert layout is table.ci.layout
    assert layout.getContentsMargins() == tuple(float(m) for m in DEFAULT_MARGINS)

    with pytest.raises(RuntimeError):
        table.centralLayout.count()

    positions = [round(panel.pos().x(), 1) for panel in table.ci.items
                 if isinstance(panel, pg.PlotItem)]
    dialog.marginBoxes['Left'].setValue(120)
    app.processEvents()
    moved = [round(panel.pos().x(), 1) for panel in table.ci.items
             if isinstance(panel, pg.PlotItem)]

    assert layout.getContentsMargins() == (120.0, 9.0, 9.0, 9.0)
    assert moved > positions, 'the panels did not move: %r -> %r' % (positions,
                                                                    moved)


@pytest.mark.ui
def test_the_margins_section_offers_the_way_back_it_documents(qapp):
    """`Restore previous` and `Restore default`, asked of the live layout."""
    table, box, _ = pluginPanel()
    dialog = QVizPlotStyleUI(styleSource=box)

    dialog.marginBoxes['Top'].setValue(80)
    assert dialog.marginsLayout.getContentsMargins()[1] == 80.0
    dialog.previousButton.click()
    assert dialog.marginsLayout.getContentsMargins() == \
        tuple(float(m) for m in DEFAULT_MARGINS)

    dialog.marginBoxes['Right'].setValue(33)
    dialog.defaultButton.click()
    assert dialog.marginsLayout.getContentsMargins() == \
        tuple(float(m) for m in DEFAULT_MARGINS)
    assert [dialog.marginBoxes[side].value()
            for side in ('Left', 'Top', 'Right', 'Bottom')] == list(DEFAULT_MARGINS)


# -- Cancel means Cancel ---------------------------------------------------

@pytest.mark.ui
def test_cancel_writes_back_everything_the_window_changed(qapp):
    """Pinned against the measured nothing: the margin stayed at 40.

    Every change is applied live, as the manual describes the dialogue, so
    undoing is a thing the window has to do itself. The title is the one that
    cannot be restored by handing back the stored opts: `setText(**kwargs)`
    updates what it is given and leaves the rest, and a fresh title's opts carry
    no `bold` at all -- measured -- so a bold set through the window stayed bold
    until the two knobs were forced back.
    """
    table = ownership.keep(QVizTablePlotView(None, None, 1, 'profiles_1d', -1))
    table.show()
    qapp.processEvents()
    _, box, plotItem = pluginPanel(table=table)
    curve = plotItem.plot([1, 2, 3], pen=pg.mkPen((0, 0, 128)), name='only')
    left = plotItem.getAxis('left')

    dialog = QVizPlotStyleUI(styleSource=box)
    row = rowOf(dialog, curve)
    row.colorButton.setColor((7, 7, 7))
    row.colorButton.sigColorChanging.emit(row.colorButton)
    row.widthBox.setValue(12.0)
    dialog.titleEditor.lineEdit.setText('renamed panel')
    dialog.titleEditor.boldButton.toggle()
    dialog.axisEditors[1].lineEdit.setText('renamed left')
    dialog.marginBoxes['Left'].setValue(40)
    qapp.processEvents()

    assert penRGB(curve) == (7, 7, 7)
    assert plotItem.titleLabel.text == 'renamed panel'
    assert plotItem.titleLabel.opts.get('bold') is True
    assert left.labelText == 'renamed left'
    assert dialog.marginsLayout.getContentsMargins()[0] == 40.0

    dialog.reject()
    qapp.processEvents()

    assert penRGB(curve) == (0, 0, 128)
    assert penOf(curve).width() != 12.0
    assert plotItem.titleLabel.text == 'probe panel'
    assert plotItem.titleLabel.opts.get('bold') is False, 'the bold came back'
    assert plotItem.titleLabel.opts['size'] == '11pt'
    assert left.labelText == 'the left label'
    assert left.labelStyle == FRESH_AXIS_STYLE
    assert dialog.marginsLayout.getContentsMargins() == \
        tuple(float(m) for m in DEFAULT_MARGINS)
    assert dialog.isVisible() is False


@pytest.mark.ui
def test_ok_leaves_the_changes_where_they_are(qapp):
    """The other button is not an undo.

    The manual's three figures describe the dialogue as changing the plot; the
    difference between its two buttons is whether what changed stays.
    """
    table, box, plotItem = pluginPanel()
    curve = plotItem.plot([1, 2, 3], pen=pg.mkPen((0, 0, 128)), name='only')
    dialog = QVizPlotStyleUI(styleSource=box)

    row = rowOf(dialog, curve)
    row.colorButton.setColor((7, 7, 7))
    row.colorButton.sigColorChanging.emit(row.colorButton)
    dialog.accept()

    assert penRGB(curve) == (7, 7, 7)
    assert dialog.isVisible() is False


# -- the guard: the named walk may not come back --------------------------

def test_no_module_of_the_package_reaches_the_named_dialogue():
    """The module is gone, and nothing imports it.

    **1 342** lines, one caller, **0** tests. What replaced it is asked, not
    guessed at, so the name branches have nothing to come back to.
    """
    assert not os.path.exists(os.path.join(REPO, 'imasviz', 'VizGUI', 'VizPlot',
                                           'QVizPlotConfigUI.py'))

    importing = []
    for dirpath, _, fileNames in os.walk(os.path.join(REPO, 'imasviz')):
        for name in fileNames:
            if not name.endswith('.py'):
                continue
            source = os.path.join(dirpath, name)
            with open(source) as handle:
                for line in handle:
                    if 'QVizPlotConfigUI' in line.strip() and \
                            line.strip().startswith(('from ', 'import ')):
                        importing.append(os.path.relpath(source, REPO))
                        break
    assert importing == [], 'still importing it: %s' % ', '.join(importing)


def test_the_dialogue_never_asks_what_a_window_is_called():
    """The four branches, refused in the code -- not in the prose about them.

    The replaced constructor took `viewBox.qWidgetParent.objectName()` and looked
    for `TablePlotView`, `StackedPlotView` or `QVizPlugin`, then fell back to
    `qWidgetParent.pgPlotWidget.centralWidget.legend`. Measured on the only
    caller: the name answers 'QVizPlugin', and `hasattr(qWidgetParent,
    'pgPlotWidget')` answers False -- the fallback was dead for every frame the
    package draws.

    The check reads the module's syntax tree, because its docstring has to name
    what it refuses: the old dialogue asked for a legend, and this file explains
    why there is no section for one.
    """
    import ast

    source = os.path.join(REPO, 'imasviz', 'VizGUI', 'VizPlot',
                          'QVizPlotStyleUI.py')
    with open(source) as handle:
        tree = ast.parse(handle.read())

    asked = {node.attr for node in ast.walk(tree) if isinstance(node,
                                                                 ast.Attribute)}
    asked |= {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    forbidden = {'objectName', 'qWidgetParent', 'pgPlotWidget', 'centralWidget',
                 'centralLayout', 'legend', 'legendItem', 'gridLayout',
                 'TablePlotView', 'StackedPlotView', 'QVizPlugin'}
    assert not (asked & forbidden), 'the module still asks %r' \
                                    % sorted(asked & forbidden)
