# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The database browser's table model.

The assertions here also lock the Qt6 migration: QAbstractItemModel methods must
hand back plain Python values, not QVariant.

This file used to pin a second thing, a grid of plot panels whose only caller
was a demo script -- the layout widget. It went with the legacy figure widget it
was built around (T22c), and its grid assertions went with it: nothing in the
application ever asked for those rows and columns.
"""

import pytest
from PySide6.QtCore import Qt

from imasviz.VizGUI.VizWidgets.QVizTableOfIDSs import TableModel


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
