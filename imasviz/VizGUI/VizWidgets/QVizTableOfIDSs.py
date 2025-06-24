# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

from PySide6.QtCore import Qt, QAbstractTableModel, QVariant


class TableModel(QAbstractTableModel):
    def __init__(self, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        # self.insertColumns(10, 2)
        # self.insertRows(10, 2)
        self.headerItems = ['Database', 'Shot', 'Run']
        self.items = ['test', '1', '1']

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def rowCount(self, parent):
        return 1

    def columnCount(self, parent):
        return len(self.items)

    def data(self, index, role):
        if not index.isValid():
            return QVariant()
        elif role != Qt.DisplayRole:
            return QVariant()

        column = index.column()
        if column < len(self.items):
            return QVariant(self.items[column])
        else:
            return QVariant()

    def headerData(self, column, orientation, role=Qt.DisplayRole):
        # if role != Qt.DisplayRole:
        #     return QVariant()
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.headerItems[column])


if __name__ == '__main__':

    # Test example
    from PySide6.QtWidgets import QApplication, QTableView, QMainWindow
    import sys
    app = QApplication(sys.argv)
    mainWin = QMainWindow()

    IDSTableView = QTableView(mainWin)
    IDSTableView.setModel(TableModel(mainWin))
    IDSTableView.setSelectionBehavior(QTableView.SelectRows)

    def tableViewClicked(clickedIndex):
        row = clickedIndex.row()
        model = clickedIndex.model()
        print("row: ", row)
        print("model: ", model)

    IDSTableView.clicked.connect(tableViewClicked)

    mainWin.setCentralWidget(IDSTableView)
    mainWin.show()
    sys.exit(app.exec_())
