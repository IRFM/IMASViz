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
    QDoubleSpinBox, QComboBox, QSpinBox, QHBoxLayout, QSizePolicy, QSpacerItem, \
    QApplication, QPen, QPainter, QGraphicsGridLayout, QGraphicsWidget, QGraphicsScene, QGraphicsView
from PyQt5.QtCore import Qt, QRect, pyqtSlot
from functools import partial
from imasviz.VizUtils.QVizGlobalValues import GlobalQtStyles, GlobalPgSymbols, \
    GlobalIcons
# from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPlotWidget import QVizPlotWidget
from pyqtgraph.graphicsItems.LegendItem import ItemSample


class QVizPlotConfigUI(QDialog):
    """Tabbed widget allowing plot customization.
    """

    def __init__(self, viewBox, parent=None, size=(1000, 400)):
        super(QVizPlotConfigUI, self).__init__(parent)

        # Dialog settings
        self.setObjectName("QVizPlotConfigUI")
        self.setWindowTitle("Configure Plot")
        self.resize(size[0], size[1])

        # Set viewBox variable
        self.viewBox = viewBox

        # Get legend item. Contains legend labels, graphics etc.
        self.legendItem = self.viewBox.qWidgetParent.pgPlotWidget.centralWidget.legend

        # Set main layout
        self.setMainLayout()

    def setTabWidget(self):
        """Set TabWidget and its tabbed widgets.
        """

        # Set tab widget
        tabWidget = QTabWidget(self)
        # Add tabs
        # - Color and line properties
        self.tabLP = TabLineProperties(parent=self)
        tabWidget.addTab(self.tabLP, "Line Properties")

        self.tabTP = TabTextProperties(parent=self)
        tabWidget.addTab(self.tabTP, "Text properties")

        # - Plot design properties
        self.tabPDP = TabPlotDesignProperties(parent=self)
        tabWidget.addTab(self.tabPDP, "Plot Design Properties")
        return tabWidget

    def setButtons(self):
        """Set Cancel and OK buttons.
        """

        # Set Cancel and Ok buttons
        buttonBox = QDialogButtonBox(self)
        buttonBox.setGeometry(QRect(50, 240, 341, 32))
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel |
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

class SampleCopyFromLegend(QWidget):
    """ Create a widget containing the legend label marker ("sample").
    'sample' is the line marker shown in the plot legend
    Qt objects can't exist on two different locations, they also can't
    be copied. Due to that a new sample object must be created and the
    properties of the original sample passed to the new one
    """

    def __init__(self, legendItem, itemAtID, parent=None):
        super(SampleCopyFromLegend, self).__init__(parent)

        self.legendItem = legendItem
        self.itemAtID = itemAtID
        self.setCopy()

    def setCopy(self):
        # Set graphics scene
        self.scene = QGraphicsScene()
        # Set scene size
        self.scene.setSceneRect(0,0,0,0)
        # Set view
        self.view = QGraphicsView(self)

        sample_original = self.legendItem.layout.itemAt(self.itemAtID,0)
        sample_new = ItemSample(sample_original.item)
        self.scene.addItem(sample_new)
        self.view.setScene(self.scene)
        self.view.setMaximumSize(25,25)

    def getCopy(self):
        return self

class TabLineProperties(QWidget):
    """Widget allowing plot color and line customization.
    """

    def __init__(self, parent=None, size=(500, 400)):
        super(TabLineProperties, self).__init__(parent)

        # Widget settings
        self.setObjectName("TabLineProperties")
        self.setWindowTitle("Color and Line Properties")
        # self.resize(size[0], size[1])

        self.parent = parent
        # Set viewBox variable
        self.viewBox = self.parent.viewBox

        self.legendItem = self.parent.legendItem

        # List of plotDataItems within viewBox
        self.listPlotDataItems = self.viewBox.addedItems

        # self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

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
        # - Set list of header items
        listHeaderLabels = ['Line',
                            'Color',
                            'Style',
                            'Thickness',
                            'Symbol',
                            'Symbol Size',
                            'Symbol Color',
                            'Symbol Outline Color']
        # - Set header item for each column (i)
        for i in range(len(listHeaderLabels)):
            scrollLayout.addWidget(QLabel(listHeaderLabels[i]), 0, i, 1, 1)

        # Add options for each plotDataItem
        i = 0 # layout line
        for pdItem in self.listPlotDataItems:
            j = 0 # layout column

            # Add line marker from the legend to the plot configuration to
            # provide better way of identifying the plot to customize
            newSampleWidget = SampleCopyFromLegend(parent=self,
                                                   legendItem=self.legendItem,
                                                   itemAtID=i).getCopy()

            # - Add sample marker to layout
            scrollLayout.addWidget(newSampleWidget, i +1, j, 1, 1)
            j += 1 # go to next column

            # ------------------------------------------------------------------
            # Configuring plot pen color
            penColorButton = pg.ColorButton()
            # - Set current plot pen color (takes QColor)
            penColorButton.setColor(pdItem.opts['pen'].color())
            # - Add penColorButton to layout
            scrollLayout.addWidget(penColorButton, i + 1, j, 1, 1)
            # - Update plot pen color on value change
            #   Note: Better to work with only one signal, either
            #   sigColorChanging or sigColorChanged
            # -- While selecting color
            penColorButton.sigColorChanging.connect(partial(
                self.updatePDItemColor,
                pdItem=pdItem,
                colorButton=penColorButton))
            # -- When done selecting color
            # penColorButton.sigColorChanged.connect(partial(
            #     self.updatePDItemColor,
            #     pdItem=pdItem,
            #     colorButton=penColorButton))
            j += 1 # go to next column
            # ------------------------------------------------------------------
            # Configuring plot pen style
            styleComboBox = QComboBox()

            # - Set list of line styles using keys from globalQtStyles
            #   dictionary
            stylesList = list(GlobalQtStyles.stylesDict.keys())

            # - Add list of styles to comboBox
            styleComboBox.addItems(stylesList)

            # - Update plot pen style on value change
            styleComboBox.currentIndexChanged.connect(partial(
                self.updatePDItemStyle,
                pdItem=pdItem,
                comboBox=styleComboBox))

            # - Add comboBox to layout
            scrollLayout.addWidget(styleComboBox, i + 1, j, 1, 1)
            j += 1 # go to next column
            # ------------------------------------------------------------------
            # Configuring plot pen width
            widthSpinBox = QDoubleSpinBox(value=pdItem.opts['pen'].width(),
                                          maximum=50.0,
                                          minimum=0.0,
                                          singleStep=0.5)
            # - Add spinBox to layout
            scrollLayout.addWidget(widthSpinBox, i + 1, j, 1, 1)

            # - Update plot pen width/thickness on value change
            widthSpinBox.valueChanged.connect(partial(
                self.updatePDItemWidth,
                pdItem=pdItem,
                spinBox=widthSpinBox))
            j += 1 # go to next column
            # ------------------------------------------------------------------
            # Configuring symbol type
            symbolComboBox = QComboBox()

            # - Set list of symbol types using keys from globalQtStyles
            #   dictionary
            symbolsList = list(GlobalPgSymbols.symbolsDict.keys())

            # - Add list of styles to comboBox
            symbolComboBox.addItems(symbolsList)

            # - Set current symbol type to be shown
            currentQtStyle = \
                list(GlobalPgSymbols.symbolsDict.keys())[
                    list(GlobalPgSymbols.symbolsDict.values()).
                    index(pdItem.opts['symbol'])]
            symbolComboBox.setCurrentText(currentQtStyle)

            # - Update plot pen style on value change
            symbolComboBox.currentIndexChanged.connect(partial(
                self.updatePDItemSymbol,
                pdItem=pdItem,
                comboBox=symbolComboBox))

            # - Add comboBox to layout
            scrollLayout.addWidget(symbolComboBox, i + 1, j, 1, 1)
            j += 1 # go to next column
            # ------------------------------------------------------------------
            # Configuring symbol size. Take current symbol size as a value
            symbolSizeSpinBox = QDoubleSpinBox(value=pdItem.opts['symbolSize'],
                                               maximum=100.0,
                                               minimum=0.0,
                                               singleStep=0.5)
            # - Add spinBox to layout
            scrollLayout.addWidget(symbolSizeSpinBox, i + 1, j, 1, 1)

            # - Update plot pen width/thickness on value change
            symbolSizeSpinBox.valueChanged.connect(partial(
                self.updatePDItemSymbolSize,
                pdItem=pdItem,
                spinBox=symbolSizeSpinBox))
            j += 1 # go to next column
            # ------------------------------------------------------------------
            # Configuring symbol fill color
            symbolColorButton = pg.ColorButton()
            # - Set current symbol fill color (takes QColor)
            symbolColorButton.setColor(pdItem.opts['symbolBrush'])
            # - Add symbolColorButton to layout
            scrollLayout.addWidget(symbolColorButton, i + 1, j, 1, 1)
            # - Update plot pen color on value change
            #   Note: Better to work with only one signal, either
            #   sigColorChanging or sigColorChanged
            # -- While selecting color
            symbolColorButton.sigColorChanging.connect(partial(
                self.updatePDItemSymbolColor,
                pdItem=pdItem,
                colorButton=symbolColorButton))
            # -- When done selecting color
            # symbolColorButton.sigColorChanged.connect(partial(
            #     self.updatePDItemSymbolColor,
            #     pdItem=pdItem,
            #     colorButton=symbolColorButton))
            j += 1 # go to next column
            # ------------------------------------------------------------------
            # Configuring symbol outline color
            symbolOColorButton = pg.ColorButton()
            # - Set current symbol outline color (takes QColor)
            symbolOColorButton.setColor(pdItem.opts['symbolPen'])
            # - Add symbolOColorButton to layout
            scrollLayout.addWidget(symbolOColorButton, i + 1, j, 1, 1)
            # - Update plot pen color on value change
            #   Note: Better to work with only one signal, either
            #   sigColorChanging or sigColorChanged
            # -- While selecting color
            symbolOColorButton.sigColorChanging.connect(partial(
                self.updatePDItemSymbolOutlineColor,
                pdItem=pdItem,
                colorButton=symbolOColorButton))
            # -- When done selecting color
            # symbolOColorButton.sigColorChanged.connect(partial(
            #     self.updatePDItemSymbolOutlineColor,
            #     pdItem=pdItem,
            #     colorButton=symbolOColorButton))

            i += 1

            # TODO: axis configuration. Use (pg.DataItem):
            # axis = pgPlotItem.getAxis('bottom')
            # axis.setLabel("text", "unit")
            # axis.label.setPlainText("text")
            # axis.label  # QGraphicsTextItem
            # axis.labelText = "text"
            # axis.labelUnitPrefix = "units prefix"  # str
            # axis.labelUnits = "units"  # str
            # axis.range  # (float,float)
            # axis.scale = 3.0  # float
            # axis.style  # dict
            # axis.textHeight = 20  # int
            # axis.textWidth  # int

        # Set scrollArea contents margin to keep the contents lined to the top
        # even if not full scrollArea would be filled
        topMargin = 270 - (i - 1)*30
        if topMargin < 0:
            topMargin = 0
        scrollLayout.setContentsMargins(0, 0, 0, topMargin)
        # Add all contents to scrollArea widget
        scrollContent.setLayout(scrollLayout)
        scrollArea.setWidget(scrollContent)

        return scrollArea

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

    @pyqtSlot(pg.graphicsItems.PlotDataItem.PlotDataItem, QComboBox)
    def updatePDItemStyle(self, pdItem, comboBox):
        """Update plotDataItem pen style.
        Note: instant update (no apply required).

        Arguments:
            pdItem   (pg.plotDataItem) : PlotDataItem to update.
            comboBox (QComboBox)       : ComboBox with which the new style is
                                         set.
        """
        # Change item pen style
        pdItem.opts['pen'].setStyle(GlobalQtStyles.stylesDict[comboBox.currentText()])
        pdItem.updateItems()

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

    @pyqtSlot(pg.graphicsItems.PlotDataItem.PlotDataItem, QComboBox)
    def updatePDItemSymbol(self, pdItem, comboBox):
        """Update plotDataItem pen width.
        Note: instant update (no apply required).

        Arguments:
            pdItem  (pg.plotDataItem) : PlotDataItem to update.
            comboBox (QComboBox)      : QComboBox with which the symbol type
                                        is set.
        """

        # Change item symbol type
        pdItem.opts['symbol'] = GlobalPgSymbols.symbolsDict[comboBox.currentText()]
        pdItem.updateItems()

    @pyqtSlot(pg.graphicsItems.PlotDataItem.PlotDataItem, QDoubleSpinBox)
    def updatePDItemSymbolSize(self, pdItem, spinBox):
        """Update plotDataItem symbol size.
        Note: instant update (no apply required).

        Arguments:
            pdItem  (pg.plotDataItem) : PlotDataItem to update.
            spinBox (QDoubleSpinBox)  : SpinBox with which the new size is set.
        """

        # Change item symbol size
        pdItem.opts['symbolSize'] = spinBox.value()
        pdItem.updateItems()

    @pyqtSlot(pg.graphicsItems.PlotDataItem.PlotDataItem, pg.ColorButton)
    def updatePDItemSymbolColor(self, pdItem, colorButton):
        """Update plotDataItem symbol color.
        Note: instant update (no apply required).

        Arguments:
            pdItem       (pg.plotDataItem) : PlotDataItem to update.
            colorButton  (pg.ColorButton)  : ColorButton with which the new
                                             color is set.
        """
        # Change symbol color
        pdItem.opts['symbolBrush'] = colorButton.color().getRgb()
        pdItem.updateItems()
        pass

    @pyqtSlot(pg.graphicsItems.PlotDataItem.PlotDataItem, pg.ColorButton)
    def updatePDItemSymbolOutlineColor(self, pdItem, colorButton):
        """Update plotDataItem symbol outline color.
        Note: instant update (no apply required).

        Arguments:
            pdItem       (pg.plotDataItem) : PlotDataItem to update.
            colorButton  (pg.ColorButton)  : ColorButton with which the new
                                             color is set.
        """
        # Change symbol outline color
        pdItem.opts['symbolPen'] = colorButton.color().getRgb()
        pdItem.updateItems()


class TabTextProperties(QWidget):
    """Widget allowing plot color and line customization.
    """

    def __init__(self, parent=None, size=(500, 400)):
        super(TabTextProperties, self).__init__(parent)

        # Widget settings
        self.setObjectName("TabTextProperties")
        self.setWindowTitle("Text Properties")
        # self.resize(size[0], size[1])

        self.parent = parent
        # Set viewBox variable
        self.viewBox = self.parent.viewBox

        self.legendItem = self.parent.legendItem

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
        # - Set list of header items
        listHeaderLabels = ['Line',
                            'Legend Label',
                            'Bold',
                            'Italic']
        # - Set header item for each column (i)
        for i in range(len(listHeaderLabels)):
            scrollLayout.addWidget(QLabel(listHeaderLabels[i]), 0, i, 1, 1)

        # Add options for each plotDataItem
        i = 0 # layout line
        for pdItem in self.listPlotDataItems:
            j = 0 # layout column

            # Add line marker from the legend to the plot configuration to
            # provide better way of identifying the plot to customize
            newSampleWidget = SampleCopyFromLegend(parent=self,
                                                   legendItem=self.legendItem,
                                                   itemAtID=i).getCopy()

            # - Add sample marker to layout
            scrollLayout.addWidget(newSampleWidget, i +1, j, 1, 1)
            j += 1 # go to next column
            # ------------------------------------------------------------------
            # Configuring legend label
            # - Add editable text box containing item label (string)
            labelEdit = QLineEdit(pdItem.opts['name'])
            # - Add item ID to labelEdit
            labelEdit.itemID = i
            # - Add labelEdit to layout
            scrollLayout.addWidget(labelEdit, i + 1, j, 1, 1)
            # - Add action triggered by modification of the text box
            labelEdit.textChanged.connect(partial(
                self.updatePDItemLabel,
                pdItem=pdItem,
                lineEdit=labelEdit))
            j += 1 # go to next column
            # ------------------------------------------------------------------
            # Configuring legend thickness (boldness)
            boldButton = QPushButton('', self)
            # Set icon
            icon = GlobalIcons.getCustomQIcon(QApplication, 'bold')
            boldButton.setIcon(icon)
            # - Add boldButton to layout
            scrollLayout.addWidget(boldButton, i + 1, j, 1, 1)
            # - Add action triggered by pressing the button
            boldButton.pressed.connect(partial(
                self.setLegendBold,
                legendItemID = i))

            # boldButton.released.connect()
            j += 1 # go to next column
            # ------------------------------------------------------------------
            # Configuring legend italic text style
            italicButton = QPushButton('', self)
            # Set icon
            icon = GlobalIcons.getCustomQIcon(QApplication, 'italic')
            italicButton.setIcon(icon)
            # - Add italicButton to layout
            scrollLayout.addWidget(italicButton, i + 1, j, 1, 1)
            # - Add action triggered by pressing the button
            italicButton.pressed.connect(partial(
                self.setLegendItalic,
                legendItemID = i))

            i += 1

        # Set scrollArea contents margin to keep the contents lined to the top
        # even if not full scrollArea would be filled
        topMargin = 270 - (i - 1)*30
        if topMargin < 0:
            topMargin = 0
        scrollLayout.setContentsMargins(0, 0, 0, topMargin)
        # Add all contents to scrollArea widget
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
        # - Get legend labelItem
        legendLabelItem = self.legendItem.items[lineEdit.itemID][1]
        # - Update label text
        legendLabelItem.setText(newLabel)

    @pyqtSlot(int)
    def setLegendBold(self, legendItemID):

        # - Get legend labelItem
        legendLabelItem = self.legendItem.items[legendItemID][1]

        key = 'bold'
        if key in legendLabelItem.opts:
            if legendLabelItem.opts['bold'] == True:
                self.setLegendItemBoldOFF(legendItemID=legendItemID)
            elif legendLabelItem.opts['bold'] == False:
                self.setLegendItemBoldON(legendItemID=legendItemID)
        else:
            self.setLegendItemBoldON(legendItemID=legendItemID)


    @pyqtSlot(int)
    def setLegendItemBoldON(self, legendItemID):
        """Set plotDataItem legend label (in plotWidget) to bold.
        Note: instant update (no apply required).

        Arguments:
            legendItemID (int)         : ID of corresponding legend item,
                                         identifying the relevant legend item
                                         from a list of legend items.
        """

        # - Get legend labelItem
        legendLabelItem = self.legendItem.items[legendItemID][1]
        # Set style
        legendLabelStyle = {'bold': True}
        # legendLabelStyle = {'color': '#000', 'size': '12pt', 'bold': True, 'italic': False}

        # Setting text style
        # Note: setAttr('bold', True) and setProperty('bold', True) have no
        #       effect.
        legendLabelItem.setText(text=legendLabelItem.text, **legendLabelStyle)

    @pyqtSlot(int)
    def setLegendItemBoldOFF(self, legendItemID):
        """Set plotDataItem legend label (in plotWidget) to flat (not bold).
        Note: instant update (no apply required).

        Arguments:
            legendItemID (int)         : ID of corresponding legend item,
                                         identifying the relevant legend item
                                         from a list of legend items.
        """

        # - Get legend labelItem
        legendLabelItem = self.legendItem.items[legendItemID][1]
        # Set style
        legendLabelStyle = {'bold': False}

        # Setting text style
        # Note: setAttr('bold', False) and setProperty('bold', False) have no
        #       effect.
        legendLabelItem.setText(text=legendLabelItem.text, **legendLabelStyle)

    @pyqtSlot(int)
    def setLegendItalic(self, legendItemID):

        # - Get legend labelItem
        legendLabelItem = self.legendItem.items[legendItemID][1]

        key = 'italic'
        if key in legendLabelItem.opts:
            if legendLabelItem.opts['italic'] == True:
                self.setLegendItemItalicOFF(legendItemID=legendItemID)
            elif legendLabelItem.opts['italic'] == False:
                self.setLegendItemItalicON(legendItemID=legendItemID)
        else:
            self.setLegendItemItalicON(legendItemID=legendItemID)


    @pyqtSlot(int)
    def setLegendItemItalicON(self, legendItemID):
        """Set plotDataItem legend label (in plotWidget) to italic.
        Note: instant update (no apply required).

        Arguments:
            legendItemID (int)         : ID of corresponding legend item,
                                         identifying the relevant legend item
                                         from a list of legend items.
        """

        # - Get legend labelItem
        legendLabelItem = self.legendItem.items[legendItemID][1]
        # Set style
        legendLabelStyle = {'italic': True}
        # legendLabelStyle = {'color': '#000', 'size': '12pt', 'bold': True, 'italic': False}

        # Setting text style
        legendLabelItem.setText(text=legendLabelItem.text, **legendLabelStyle)

    @pyqtSlot(int)
    def setLegendItemItalicOFF(self, legendItemID):
        """Set plotDataItem legend label (in plotWidget) to "not italic".
        Note: instant update (no apply required).

        Arguments:
            legendItemID (int)         : ID of corresponding legend item,
                                         identifying the relevant legend item
                                         from a list of legend items.
        """

        # - Get legend labelItem
        legendLabelItem = self.legendItem.items[legendItemID][1]
        # Set style
        legendLabelStyle = {'italic': False}


        # Setting text style
        # Note: setAttr('bold', False) and setProperty('bold', False) have no
        #       effect.
        legendLabelItem.setText(text=legendLabelItem.text, **legendLabelStyle)

class TabPlotDesignProperties(QWidget):
    """Widget allowing plot color and line customization.
    """

    def __init__(self, parent=None, size=(500, 400)):
        super(TabPlotDesignProperties, self).__init__(parent)

        # Widget settings
        self.setObjectName("TabPlotDesignProperties")
        self.setWindowTitle("Plot Design Properties")
        # self.resize(size[0], size[1])

        # self.setSizePolicy(QSizePolicy.Expanding,
        #                             QSizePolicy.Expanding)

        self.parent = parent
        # Set viewBox variable
        self.viewBox = self.parent.viewBox

        # Set up the QWidget contents
        self.setContents()

    def setContents(self):
        """ Set widget contents.
        """

        # Set layout
        self.gridLayout = QGridLayout(self)
        self.gridLayout.setObjectName("gridLayout")

        # Set widget for setting custom margin
        self.newMarginWidget = self.setNewMargin()
        self.gridLayout.addWidget(self.newMarginWidget, 0, 0, 1, 1)

        # Set spacer (to not have widgets in the middle of the window)
        self.spacerItem = QSpacerItem(20, 40, QSizePolicy.Minimum,
                                      QSizePolicy.Expanding)
        self.gridLayout.addItem(self.spacerItem, 1, 0, 1, 1)

    def setNewMargin(self):
        """ Set widget for setting custom margin.
        """

        # Get QVizPlotWidget
        plotWidget = self.viewBox.qWidgetParent

        # Check which layout it has
        # - gridLayout for QVizPlotWidget and QVizPreviewWidget
        # - centralLayout for TPV and SPV
        if hasattr(plotWidget, 'gridLayout'):
            self.parentLayout = plotWidget.gridLayout
        elif hasattr(plotWidget, 'centralLayout'):
            # For TPV and SPV
            self.parentLayout = plotWidget.centralWidget.layout
        else:
            return QWidget()

        # Get current margins
        currentMargin = self.parentLayout.getContentsMargins()

        self.previousMargins = currentMargin
        self.defaultMargins = (10, 10, 10, 10)

        # TODO: include changing the in-plot margin
        # pgPlotWidget = self.viewBox.qWidgetParent.pgPlotWidget
        # pgPlotWidget.centralWidget.setContentsMargins(50,50,50,50)
        # currentMargin = pgPlotWidget.centralWidget.layout.getContentsMargins()
        # plotWidget = pgPlotWidget

        # Set spinboxes for each margin side
        self.marginSpinBox_left = QSpinBox(value=currentMargin[0],
                                      maximum=250,
                                      minimum=0,
                                      singleStep=1)

        self.marginSpinBox_top = QSpinBox(value=currentMargin[1],
                                     maximum=250,
                                     minimum=0,
                                     singleStep=1)

        self.marginSpinBox_right = QSpinBox(value=currentMargin[2],
                                       maximum=250,
                                       minimum=0,
                                       singleStep=1)

        self.marginSpinBox_bottom = QSpinBox(value=currentMargin[3],
                                        maximum=250,
                                        minimum=0,
                                        singleStep=1)

        # On spinbox value change, run update routine
        self.marginSpinBox_left.valueChanged.connect(
            self.updatePlotWidgetContentsMargins)

        self.marginSpinBox_top.valueChanged.connect(
            self.updatePlotWidgetContentsMargins)

        self.marginSpinBox_right.valueChanged.connect(
            self.updatePlotWidgetContentsMargins)

        self.marginSpinBox_bottom.valueChanged.connect(
            self.updatePlotWidgetContentsMargins)

        # Set buttons
        margins2previous_button = QPushButton('Restore previous', self)
        margins2previous_button.clicked.connect(self.setPreviousMargins)
        margins2default_button = QPushButton('Restore default', self)
        margins2default_button.clicked.connect(self.setDefaultMargins)

        marginWidget = QWidget(self)
        gridLayout = QGridLayout(marginWidget)
        gridLayout.setObjectName('gridLayout')

        # Set header
        # - Set list of header items
        listHeaderLabels = ['Margins',
                            'Left',
                            'Top',
                            'Right',
                            'Bottom']
        # - Set header item for each column (i)
        for i in range(len(listHeaderLabels)):
            gridLayout.addWidget(QLabel(listHeaderLabels[i]), 0, i, 1, 1)

        # Add widgets to layout
        gridLayout.addWidget(self.marginSpinBox_left, 1, 1, 1, 1)
        gridLayout.addWidget(self.marginSpinBox_top, 1, 2, 1, 1)
        gridLayout.addWidget(self.marginSpinBox_right, 1, 3, 1, 1)
        gridLayout.addWidget(self.marginSpinBox_bottom, 1, 4, 1, 1)
        gridLayout.addWidget(margins2previous_button, 1, 5, 1, 1)
        gridLayout.addWidget(margins2default_button, 1, 6, 1, 1)

        return marginWidget

    @pyqtSlot()
    def updatePlotWidgetContentsMargins(self):
        """Update plot widget contents margins.
        Note: instant update (no apply required).
        """

        # Update contents margin
        self.parentLayout.setContentsMargins(
            self.marginSpinBox_left.value(),
            self.marginSpinBox_top.value(),
            self.marginSpinBox_right.value(),
            self.marginSpinBox_bottom.value())

    @pyqtSlot()
    def setPreviousMargins(self):
        """Set plot widget contents margin back to previous.
        """

        # Update contents margin
        m = self.previousMargins
        self.parentLayout.setContentsMargins(m[0], m[1], m[2], m[3])

        # Update spinbox values
        self.updateMarginsSpinboxValues(m[0], m[1], m[2], m[3])

    @pyqtSlot()
    def setDefaultMargins(self):
        """Set plot widget contents margin back to default values.
        """

        # Update contents margin
        m = self.defaultMargins
        self.parentLayout.setContentsMargins(m[0], m[1], m[2], m[3])

        # Update spinbox values
        self.updateMarginsSpinboxValues(m[0], m[1], m[2], m[3])

    def updateMarginsSpinboxValues(self, v1, v2, v3, v4):
        """Update margins spinbox values.
        """

        self.marginSpinBox_left.setValue(v1)
        self.marginSpinBox_top.setValue(v2)
        self.marginSpinBox_right.setValue(v3)
        self.marginSpinBox_bottom.setValue(v4)