# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Layout widget and the IDS table model.

The table model assertions also lock the Qt6 migration: QAbstractItemModel
methods must hand back plain Python values, not QVariant.
"""

import pytest
from PySide6.QtCore import Qt

from imasviz.VizGUI.VizPlot.VizPlotFrames.QvizPlotLayoutWidget import QvizPlotLayoutWidget
from imasviz.VizGUI.VizWidgets.QVizTableOfIDSs import TableModel


@pytest.fixture
def layout_widget(qtbot):
    widget = QvizPlotLayoutWidget(dataTreeView=None, rows=2, columns=3,
                                  title='a layout')
    qtbot.addWidget(widget)
    return widget


def test_the_grid_dimensions_are_kept(layout_widget):
    assert layout_widget.rows == 2
    assert layout_widget.columns == 3
    assert layout_widget.row == 0
    assert layout_widget.column == 0
    assert layout_widget.num_plots == 0


def test_the_widget_identity_matches_the_code_that_looks_it_up(layout_widget):
    assert layout_widget.objectName() == "QVizPlotLayoutWidget"
    assert layout_widget.windowTitle() == 'a layout'


def test_a_grid_layout_is_installed(layout_widget):
    assert layout_widget.layout() is layout_widget.gridLayout


def test_table_shape():
    model = TableModel()
    assert model.rowCount(None) == 1
    assert model.columnCount(None) == 3


def test_table_cells_are_plain_python_not_qvariant():
    model = TableModel()
    value = model.data(model.index(0, 0), Qt.DisplayRole)
    assert isinstance(value, str)
    assert value == 'test'


def test_invalid_indexes_yield_none():
    model = TableModel()
    assert model.data(model.index(9, 9), Qt.DisplayRole) is None


def test_header_labels():
    model = TableModel()
    labels = [model.headerData(column, Qt.Horizontal, Qt.DisplayRole)
              for column in range(model.columnCount(None))]
    assert labels == ['Database', 'Shot', 'Run']
