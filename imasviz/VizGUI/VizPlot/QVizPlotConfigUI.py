#  Name   : QVizPlotConfigUI
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
    QDialogButtonBox, QDialog, QVBoxLayout, QScrollArea, QLabel, QLineEdit, \
    QDoubleSpinBox
from PyQt5.QtCore import Qt, QRect, pyqtSlot
from functools import partial

class QVizPlotConfigUI(QDialog):
    """Tabbed widget allowing plot customization.
    """
    def __init__(self, viewBox, parent=None, size=(500,400)):
        super(QVizPlotConfigUI, self).__init__(parent)

        # Dialog settings
        self.setObjectName("QVizPlotConfigUI")
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

        # Set header
        scrollLayout.addWidget(QLabel('#'),         0, 0, 1, 1)
        scrollLayout.addWidget(QLabel('Label'),     0, 1, 1, 1)
        scrollLayout.addWidget(QLabel('Color'),     0, 2, 1, 1)
        scrollLayout.addWidget(QLabel('Style'),     0, 3, 1, 1)
        scrollLayout.addWidget(QLabel('Thickness'), 0, 4, 1, 1)
        scrollLayout.addWidget(QLabel('Symbol'),    0, 5, 1, 1)

        # Add options for each plotDataItem
        i = 0
        for pdItem in self.listPlotDataItems:
            # Add ID label
            scrollLayout.addWidget(QLabel(str(i)),  i+1, 0, 1, 1)

            # ------------------------------------------------------------------
            # Configuring legend label
            # - Add editable text box containing item label (string)
            labelEdit = QLineEdit(pdItem.opts['name'])
            # - Add item ID to labelEdit
            labelEdit.itemID = i
            # - Add labelEdit to layout
            scrollLayout.addWidget(labelEdit, i+1, 1, 1, 1)
            # - Add action triggered by modification of the text box
            labelEdit.textChanged.connect(partial(
                self.updatePDItemLabel,
                pdItem=pdItem,
                lineEdit=labelEdit))
            # ------------------------------------------------------------------
            # Configuring plot line color
            colorButton = pg.ColorButton()
            # - Set current plot line color (takes QColor)
            colorButton.setColor(pdItem.opts['pen'].color())
            # - Add colorButton to layout
            scrollLayout.addWidget(colorButton, i+1, 2, 1, 1)
            # - Update plot color
            #   Note: Better to work with only one signal, either
            #   sigColorChanging or sigColorChanged
            # -- While selecting color
            colorButton.sigColorChanging.connect(partial(
                self.updatePDItemColor,
                pdItem=pdItem,
                colorButton=colorButton))
            # -- When done selecting color
            # colorButton.sigColorChanged.connect(partial(
            #     self.updatePDItemColor,
            #     pdItem=pdItem,
            #     colorButton=colorButton))
            # ------------------------------------------------------------------
            # Configuring plot line style
            # TODO
            # ------------------------------------------------------------------
            # Configuring plot line width
            widthSpinBox = QDoubleSpinBox(value=pdItem.opts['pen'].width(),
                                          maximum=50.0,
                                          minimum=0.0,
                                          singleStep=0.5)
            # - Add spinBox to layout
            scrollLayout.addWidget(widthSpinBox, i+1, 4, 1, 1)

            widthSpinBox.valueChanged.connect(partial(
                self.updatePDItemWidth,
                pdItem=pdItem,
                spinBox=widthSpinBox))

            i += 1

        # Add all contents to scrollArea widget
        scrollLayout.setContentsMargins(0,0,0,0)
        scrollContent.setLayout(scrollLayout)
        scrollArea.setWidget(scrollContent)

        return scrollArea

    @pyqtSlot(pg.graphicsItems.PlotDataItem.PlotDataItem, QLineEdit)
    def updatePDItemLabel(self, pdItem, lineEdit):
        """Update plotDataItem label and plotWidget legend.
        Note: instant update (no apply required).

        Arguments:
            pdItem   (pg.plotDataItem) : PlotDataItem to update.
            lineEdit (QLineEdit)       : QLineEdit where the changes to the
                                         text occur.
        """

        # Set new label
        newLabel = lineEdit.text()
        # Update the plotDataItem name variable
        pdItem.opts['name'] = newLabel

        # Update plotWidget legend
        # Note: the changes are instant (no apply required)
        # - Get legendItem
        legendItem = self.viewBox.qWidgetParent.pgPlotWidget.centralWidget.legend
        # - Get legend labelItem
        legendLabelItem = legendItem.items[lineEdit.itemID][1]
        # - Update label text
        legendLabelItem.setText(newLabel)

        # titleLabel = self.viewBox.qWidgetParent.pgPlotWidget.centralWidget.titleLabel
        # viewBox = self.viewBox.qWidgetParent.pgPlotWidget.centralWidget.vb

    @pyqtSlot(pg.graphicsItems.PlotDataItem.PlotDataItem, pg.ColorButton)
    def updatePDItemColor(self, pdItem, colorButton):
        """Update plotDataItem pen color.
        Note: instant update (no apply required).

        Arguments:
            pdItem       (pg.plotDataItem) : PlotDataItem to update.
            colorButton  (pg.ColorButton)  : ColorButton with which the new
                                             color is set.
        """
        # Change pen color
        pdItem.opts['pen'].setColor(colorButton.color())
        pdItem.updateItems()

    # TODO
    # def updatePlotStyle()

    @pyqtSlot(pg.graphicsItems.PlotDataItem.PlotDataItem, QDoubleSpinBox)
    def updatePDItemWidth(self, pdItem, spinBox):
        """Update plotDataItem pen width.
        Note: instant update (no apply required).

        Arguments:
            pdItem  (pg.plotDataItem) : PlotDataItem to update.
            spinBox (QDoubleSpinBox)  : SpinBox with which the new width is set.
        """

        # Change item pen width
        pdItem.opts['pen'].setWidth(spinBox.value())
        pdItem.updateItems()







