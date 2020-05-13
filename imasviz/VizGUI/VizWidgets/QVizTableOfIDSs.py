#  Name   : QVizTableOfIDSs
#
#          A table to hold list of IDSs with clickable rows.
#
#          Usage example:
#
#        IDSTableView = QTableView(self)
#        IDSTableView.setModel(TableModel(self))
#        IDSTableView.setSelectionBehavior(QTableView.SelectRows)
#        IDSTableView.clicked.connect(self.tableViewClicked)
#        ...
#        layout.addWidget(IDSTableView)
#
#    def tableViewClicked(self, clickedIndex):
#        row = clickedIndex.row()
#        model = clickedIndex.model()
#        print("row: ", row)
#        print("model: ", model)
#
#  Author :
#         Ludovic Fleury, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# *****************************************************************************
#     Copyright(c) 2016- L. Fleury, D. Penko
# *****************************************************************************

from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant


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
    from PyQt5.QtWidgets import QApplication, QTableView, QMainWindow
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
