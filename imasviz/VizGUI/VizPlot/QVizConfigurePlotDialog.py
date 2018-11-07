#  Name   : QVizConfigurePlotDialog
#
#          Dialog containing tabs with options for direct plot customization
#          (line colors etc.).
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

import pyqtgraph as pg
from PyQt5.QtGui import QTabWidget, QWidget, QPushButton, QGridLayout, \
    QDialogButtonBox, QDialog, QVBoxLayout, QScrollArea, QLabel, QLineEdit
from PyQt5.QtCore import Qt, QRect, pyqtSlot
from functools import partial

class QVizConfigurePlotDialog(QDialog):
    """Tabbed widget allowing plot customization.
    """
    def __init__(self, viewBox, parent=None, size=(500,400)):
        super(QVizConfigurePlotDialog, self).__init__(parent)

        # Dialog settings
        self.setObjectName("QVizConfigurePlotDialog")
        self.setWindowTitle("Configure Plot")
        self.resize(size[0], size[1])

        # Set viewBox variable
        self.viewBox = viewBox

        # Set main layout
        self.setMainLayout()

    def setTabWidget(self):
        """Set TabWidget and its tabbed widgets.
        """

        # Set tab widget
        tabWidget = QTabWidget(self)
        # Add tabs
        tabWidget.addTab(TabColorAndLineProperties(parent=self),
                         "Color and Line Properties")
        return tabWidget

    def setButtons(self):
        """Set Cancel and OK buttons.
        """

        # Set Cancel and Ok buttons
        buttonBox = QDialogButtonBox(self)
        buttonBox.setGeometry(QRect(50, 240, 341, 32))
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel|
                                     QDialogButtonBox.Ok)
        buttonBox.setObjectName("buttonBox")
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        return buttonBox

    def setMainLayout(self):
        """Set layout.
        """

        # Set layout
        layout = QVBoxLayout(self)

        # Set tabbed widget
        self.tabWidget = self.setTabWidget()

        # Set basic buttons
        self.buttonBox = self.setButtons()

        # Add tabs and other widgets to dialog layout
        layout.addWidget(self.tabWidget)
        layout.addWidget(self.buttonBox)

        # Set dialog layout
        self.setLayout(layout)

class TabColorAndLineProperties(QWidget):
    """Widget allowing plot color and line customization.
    """
    def __init__(self, parent=None, size=(500,400)):
        super(TabColorAndLineProperties, self).__init__(parent)

        # Widget settings
        self.setObjectName("TabColorAndLineProperties")
        self.setWindowTitle("Color and Line Properties")
        self.resize(size[0], size[1])

        self.parent = parent
        # Set viewBox variable
        self.viewBox = self.parent.viewBox

        # List of plotDataItems within viewBox
        self.listPlotDataItems = self.viewBox.addedItems

        # Set up the QWidget contents
        self.setContents()

    def setContents(self):
        """ Set widget contents.
        """
        # Set layout
        self.gridLayout = QGridLayout(self)
        self.gridLayout.setObjectName("gridLayout")

        # Set scroll area containing a list of plotDataItems and their
        # customization options
        self.plotListOptions = self.setPlotPropertiesList()
        self.gridLayout.addWidget(self.plotListOptions, 0, 0, 1, 1)

        # Set layout marigin (left, top, right, bottom)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.gridLayout)

        # self.gridLayout.update()

    def setPlotPropertiesList(self):
        """Set scroll area listing plots and their customization options.
        """

        # Set scrollable area
        scrollArea = QScrollArea(self)
        scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scrollArea.setWidgetResizable(True)
        scrollArea.setEnabled(True)
        scrollContent = QWidget(scrollArea)

        # Set layout for scrollable area
        scrollLayout = QGridLayout(scrollContent)

        # Empty lists of QLineEdit
        self.lineEditList = []

        # Set header
        scrollLayout.addWidget(QLabel('#'),         0, 0, 1, 1)
        scrollLayout.addWidget(QLabel('Label'),     0, 1, 1, 1)
        scrollLayout.addWidget(QLabel('Color'),     0, 2, 1, 1)
        scrollLayout.addWidget(QLabel('Style'),     0, 3, 1, 1)
        scrollLayout.addWidget(QLabel('Thickness'), 0, 4, 1, 1)
        scrollLayout.addWidget(QLabel('Symbol'),    0, 5, 1, 1)

        # Add options for each plotDataItem
        for i in range(len(self.listPlotDataItems)):
            # Add ID
            scrollLayout.addWidget(QLabel(str(i)),  i+1, 0, 1, 1)
            # Add editable text box containing item label (string)
            lineEdit = QLineEdit(self.listPlotDataItems[i].opts['name'])
            self.lineEditList.append(lineEdit)
            scrollLayout.addWidget(self.lineEditList[-1], i+1, 1, 1, 1)
            # Add action triggered by modification of the text box
            self.lineEditList[-1].textChanged.connect(
                partial(self.updatePlotLabel,
                        plot=self.listPlotDataItems[-1],
                        lineEdit=self.lineEditList[-1]))

        # Add all contents to scrollArea widget
        scrollLayout.setContentsMargins(0,0,0,0)
        scrollContent.setLayout(scrollLayout)
        scrollArea.setWidget(scrollContent)

        return scrollArea

    @pyqtSlot(pg.graphicsItems.PlotDataItem.PlotDataItem, QLineEdit)
    def updatePlotLabel(self, plot, lineEdit):
        """Update plot label and plotWidget legend.
        Note: instant update (no apply required).

        Arguments:
            plot (pg.plotDataItem) : PlotDataItem.
            lineEdit (QLineEdit)   : QLineEdit where the changes to the text
                                     occur.
        """

        # Set new label
        newLabel = lineEdit.text()
        # Update the plotDataItem name variable
        plot.opts['name'] = newLabel

        # Update plotWidget legend
        # Note: the changes are instant (no apply required)
        # - Get legendItem
        legendItem = self.viewBox.qWidgetParent.pgPlotWidget.centralWidget.legend
        # - Get legend labelItem
        legendLabelItem = legendItem.items[0][1]
        # - Update label text
        legendLabelItem.setText(newLabel)

        # titleLabel = self.viewBox.qWidgetParent.pgPlotWidget.centralWidget.titleLabel
        # viewBox = self.viewBox.qWidgetParent.pgPlotWidget.centralWidget.vb



