# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Axis labels, axis units and plot title on QVizPlotWidget.

Three display defects are pinned here: the title given to plot() was erased
right after being set, the axis labels were only applied to the first curve of a
figure (so mixing signals on different coordinates kept the first X label), and
the units slot of pyqtgraph was never fed, which left the unit glued inside the
label text or missing altogether.
"""

import numpy as np
import pytest

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPlotWidget import QVizPlotWidget

X = np.linspace(0., 1., 10)
Y = np.sin(X)


@pytest.fixture
def plotWidget(qtbot):
    widget = QVizPlotWidget(dataTreeView=None, title='a figure')
    qtbot.addWidget(widget)
    return widget


def axis(widget, side):
    return widget.pgPlotWidget.getAxis(side)


def test_the_first_curve_sets_both_axis_labels(plotWidget):
    plotWidget.plot(x=X, y=Y, xlabel='psi', ylabel='Ti')
    assert axis(plotWidget, 'bottom').labelText == 'psi'
    assert axis(plotWidget, 'left').labelText == 'Ti'


def test_a_second_curve_updates_the_axis_labels_when_the_coordinate_changes(plotWidget):
    plotWidget.plot(x=X, y=Y, xlabel='psi', ylabel='Ti')
    plotWidget.plot(x=X, y=Y, xlabel='z_eff', ylabel='Ti')
    # Both curves are on the same figure: the axis now carries the last drawn
    # coordinate, which is the one actually displayed.
    assert axis(plotWidget, 'bottom').labelText == 'z_eff'


def test_the_axis_labels_are_left_alone_when_the_coordinate_is_unchanged(plotWidget):
    plotWidget.plot(x=X, y=Y, xlabel='psi', ylabel='Ti')
    plotWidget.plot(x=X, y=Y, xlabel='psi', ylabel='Ti')
    assert axis(plotWidget, 'bottom').labelText == 'psi'


def test_the_title_given_to_plot_is_displayed(plotWidget):
    plotWidget.plot(x=X, y=Y, xlabel='psi', ylabel='Ti', title='Ti vs psi')
    # PlotWidget does not forward titleLabel, unlike the PlotItem it wraps.
    assert plotWidget.pgPlotWidget.plotItem.titleLabel.text == 'Ti vs psi'


def test_axis_units_reach_the_pyqtgraph_units_slot(plotWidget):
    plotWidget.plot(x=X, y=Y, xlabel='psi', ylabel='Ti',
                    xunits='Wb', yunits='keV')
    assert axis(plotWidget, 'bottom').labelUnits == 'Wb'
    assert axis(plotWidget, 'left').labelUnits == 'keV'


def test_units_are_not_glued_into_the_label_text(plotWidget):
    # The unit used to be concatenated as 'time[s]'; pyqtgraph renders it itself
    # in parentheses once the units slot is fed.
    plotWidget.plot(x=X, y=Y, xlabel='time', ylabel='Ti', xunits='s')
    assert axis(plotWidget, 'bottom').labelText == 'time'
    assert '[s]' not in axis(plotWidget, 'bottom').label.toPlainText()
