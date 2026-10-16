# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Image plot widget, driven with synthetic data (no case, no data dictionary).

QvizPlotImageWidget accepts vizTreeNode=None: plot() only calls
viewBox.addVizTreeNode() when a node is supplied, which is what makes the widget
testable in isolation.
"""

import pytest

from imasviz.VizGUI.VizPlot.VizPlotFrames.QvizPlotImageWidget import QvizPlotImageWidget

from support.fakes import make_2d_array_handle


@pytest.fixture
def image_widget(qtbot):
    widget = QvizPlotImageWidget(vizTreeNode=None, plotSliceFromROI=False,
                                 showImageTitle=False)
    qtbot.addWidget(widget)
    return widget


def test_the_widget_is_constructed_without_a_tree_node(image_widget):
    assert image_widget.dataArrayHandle is None
    assert image_widget.plotImageItem is None


def test_plot_keeps_the_array_it_was_given(image_widget):
    handle = make_2d_array_handle()
    image_widget.plot(handle)
    assert image_widget.dataArrayHandle is handle


def test_plot_creates_exactly_one_plotted_item(image_widget):
    image_widget.plot(make_2d_array_handle())
    assert image_widget.plotImageItem is not None
    assert len(image_widget.plotImageItem.listDataItems()) == 1


@pytest.mark.ui
def test_slices_are_only_built_when_requested(qtbot):
    withSlices = QvizPlotImageWidget(vizTreeNode=None, plotSliceFromROI=True,
                                     showImageTitle=False)
    qtbot.addWidget(withSlices)
    withoutSlices = QvizPlotImageWidget(vizTreeNode=None, plotSliceFromROI=False,
                                        showImageTitle=False)
    qtbot.addWidget(withoutSlices)

    handle = make_2d_array_handle()
    withSlices.plot(handle)
    withoutSlices.plot(handle)

    assert withSlices.slicesXPlotItem is not None
    assert withSlices.slicesYPlotItem is not None
    assert withoutSlices.slicesXPlotItem is None
    assert withoutSlices.slicesYPlotItem is None


@pytest.mark.ui
def test_plotting_twice_replaces_the_previous_array(qtbot):
    widget = QvizPlotImageWidget(vizTreeNode=None, plotSliceFromROI=False,
                                 showImageTitle=False)
    qtbot.addWidget(widget)

    first = make_2d_array_handle(name='first', y_size=50)
    second = make_2d_array_handle(name='second', y_size=80)
    widget.plot(first)
    widget.plot(second)

    assert widget.dataArrayHandle is second
    assert widget.dataArrayHandle.arrayValues.shape[1] == 80
