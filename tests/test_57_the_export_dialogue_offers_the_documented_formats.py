# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What the export dialogue of a figure offers, and what one figure can cost another.

The manual documents one gesture and four formats (`other_GUI_features.rst`
"Export plot", repeated in `plotting_1d_arrays.rst` "Export feature"): right click
inside the plot window, choose *Export...*, and the plot goes out as an image, an
SVG, a **matplotlib window**, or CSV/HDF5 of its data. pyqtgraph carries that
gesture itself -- `GraphicsScene` adds the `Export...` action at construction and
the dialogue fills its format list from `Exporter.Exporters` each time it is built
(`exportDialog.py:104`).

Until now the repository did not leave that list alone. It carried a copy of
pyqtgraph's matplotlib exporter (`QVizMatplotlibExporter`, 190 lines, written
against pyqtgraph **0.10.0**), and a patch in the Profiles plugin's view box that
took the stock entry out of the list and put the copy in its place. Three measured
facts about that pair, on the stack this repository pins (pyqtgraph 0.13.7):

* **the copy was never registered**: nothing in the package imports
  `QVizMatplotlibExporter`, so the `register()` at the end of its file never ran,
  so the name the patch looked for -- `Matplotlib Window (v2)` -- was never in the
  list, so the patch only ever *subtracted*;
* **the subtraction is not local to the plot that asked for it**: `Exporters` is a
  class attribute, so the dialogue of every figure in the process lost the
  documented format. Measured on one curve figure: **5** formats in the dialogue
  before a `CustomizedViewBox` is built -- `CSV of original plot data`,
  `HDF5 Export: plot (x,y)`, `Image File (PNG, TIF, JPG, ...)`,
  `Matplotlib Window`, `Scalable Vector Graphics (SVG)` -- **4** after, with
  `Matplotlib Window` the one missing;
* **the two defects the copy was written for are gone**: on 0.13.7 the stock
  exporter multiplies the data by the axis' `autoSIPrefixScale`, so a quantity of
  1,5e6 and 2,4e6 arrives labelled `gap (x1e+06)` carrying **1,5** and **2,4** --
  label and values agree; and closing every matplotlib window fired
  `aboutToQuit` **0** times, because the window is a top-level window held in
  `MatplotlibExporter.windows` while the main window stays on screen.

So the class and its patch went, and what is pinned here is the documented
surface: the entry, the five formats, and the matplotlib one drawing the curves of
a figure this application built. The last test is the guard: no module of the
package is allowed to touch that registry, because one line in one view box takes
a documented format away from every figure of the session.
"""

import os

import pytest

import pyqtgraph
from pyqtgraph.exporters import Exporter

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizPlugins.viz_Profiles.viz_profiles.CustomizedViewBox \
    import CustomizedViewBox

from support.fakes import FakeAxesNode
from support.ownership import keep
from support.plotting import plotCommand

# The four formats the manual lists, in the words the pinned pyqtgraph uses for
# them. Measured on PyQtGraph/0.13.7-foss-2023b.
DOCUMENTED = ['CSV of original plot data', 'HDF5 Export: plot (x,y)',
              'Image File (PNG, TIF, JPG, ...)', 'Matplotlib Window',
              'Scalable Vector Graphics (SVG)']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def quantity(name, values):
    """One quantity held by a dynamic array: time is its only axis."""
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0., 1.]
    ids.profiles_1d = []
    for index, value in enumerate(values):
        element = type(str('Element'), (), {})()
        element.time = None
        setattr(element, name, value)
        ids.profiles_1d.append(element)
    return FakeAxesNode(ids, 'foo', 'foo.profiles_1d[itime]', 'FLT_0D',
                        name=name, itimeIndex=0, coordinates=(),
                        lengths={'i': '2'})


def curveFigure(*nodes):
    """A curve figure this application built, and the pyqtgraph item inside it."""
    figures = plotCommand(*nodes).execute()
    assert [type(frame) for frame in figures] == [QVizCurvePlot]
    frame = keep(figures[0])
    return frame, frame.pgPlotWidget.getPlotItem()


def dialogueFormats(item):
    """The formats the Export dialogue offers that figure, in list order.

    `showExportDialog` reads `contextMenuItem`, which only the context-menu event
    sets; that event is the documented gesture, so the test sets what it sets.
    """
    scene = item.scene()
    scene.contextMenuItem = item
    scene.showExportDialog()
    formatsList = scene.exportDialog.ui.formatList
    return [formatsList.item(row).text()
            for row in range(formatsList.count())]


@pytest.mark.ui
def test_a_figure_offers_the_export_entry_the_manual_describes(qtbot):
    frame, item = curveFigure(quantity('gap', [100., 200.]))

    actions = [action.text() for action in item.scene().contextMenu]
    assert actions == ['Export...'], actions


@pytest.mark.ui
def test_the_dialogue_offers_the_formats_the_manual_lists(qtbot):
    frame, item = curveFigure(quantity('gap', [100., 200.]))

    assert dialogueFormats(item) == DOCUMENTED


@pytest.mark.ui
def test_a_plugin_view_box_takes_no_format_away_from_another_figure(qtbot):
    """The reason the patch was worth deleting rather than fixing.

    The Profiles plugin used to run its patch from this view box's constructor, so
    a plugin window existing at all was enough. `Exporters` is a class attribute
    of `Exporter`, so the format was gone from every dialogue of the process --
    including the one opened here, on a figure the plugin never touched.
    """
    frame, item = curveFigure(quantity('gap', [100., 200.]))
    holder = pyqtgraph.PlotWidget()
    qtbot.addWidget(holder)

    viewBox = CustomizedViewBox(qWidgetParent=holder, imas_viz_api=None)
    keep(viewBox)
    assert viewBox.qWidgetParent is holder

    assert dialogueFormats(item) == DOCUMENTED


@pytest.mark.ui
def test_the_matplotlib_format_draws_every_curve_of_the_figure(qtbot):
    """The documented entry, through the exporter the dialogue itself names."""
    frame, item = curveFigure(quantity('gap', [100., 200.]),
                              quantity('rho_tor', [3.1, 3.4]))
    assert frame.curveCount() == 2

    exporterClass = [cls for cls in Exporter.Exporters
                     if cls.Name == 'Matplotlib Window']
    assert len(exporterClass) == 1, [cls.Name for cls in Exporter.Exporters]

    before = len(exporterClass[0].windows)
    exporterClass[0](item).export()
    assert len(exporterClass[0].windows) == before + 1
    axes = exporterClass[0].windows[-1].getFigure().axes
    assert len(axes) == 1
    assert len(axes[0].lines) == 2


@pytest.mark.ui
def test_a_quantity_written_in_scientific_notation_arrives_consistent(qtbot):
    """The defect the deleted copy cited, measured on the exporter it replaced.

    Measured: pyqtgraph spells the prefix into the axis label (`gap (x1e+06)`,
    `autoSIPrefixScale` 1e-06) and the stock exporter multiplies the data by that
    scale, so matplotlib reads 1,5 and 2,4 under a label naming 1e+06 -- label and
    values agree, which is what the 0.10.0-era copy was written to obtain.
    """
    frame, item = curveFigure(quantity('gap', [1.5e6, 2.4e6]))

    exporterClass = [cls for cls in Exporter.Exporters
                     if cls.Name == 'Matplotlib Window'][0]
    before = len(exporterClass.windows)
    exporterClass(item).export()
    axes = exporterClass.windows[-1].getFigure().axes

    assert axes[0].get_ylabel() == 'gap (x1e+06)'
    assert list(axes[0].lines[0].get_ydata()) == [1.5, 2.4]
    assert axes[0].get_xlabel() == 'time (s)'


def test_no_module_of_the_package_rewrites_the_exporter_registry():
    """One line in one view box took a documented format from every figure.

    Checked on the sources rather than on a dialogue: it costs nothing, it needs
    no window, and it refuses the patch whether or not a copy of an exporter is
    there to point at.
    """
    reached = []
    for dirpath, _, fileNames in os.walk(os.path.join(REPO, 'imasviz')):
        for name in fileNames:
            if not name.endswith('.py'):
                continue
            source = os.path.join(dirpath, name)
            with open(source) as handle:
                if 'Exporter.Exporters' in handle.read():
                    reached.append(os.path.relpath(source, REPO))
    assert reached == [], 'reaching the registry: %s' % ', '.join(reached)
