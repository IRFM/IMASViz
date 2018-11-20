#  Name   : QVizCOnfigurationlistsWindow
#
#          Container to handle configuration lists (list of signals,
#          TablePlotView configuration etc.)
#          Note: The wxPython predecessor of this Python file is
#          ConfigurationListsFrame.py
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F. Ludovic, L. xinyi, D. Penko
#****************************************************

import os
from functools import partial

from PyQt5.QtCore import Qt, pyqtSlot, QObject
from PyQt5.QtWidgets import (QListWidget, QDialog, QTabWidget, QVBoxLayout,
                             QPushButton, QWidget, QSizePolicy, QLabel)
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations

from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignals import QVizSelectSignals
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals import QVizUnselectAllSignals
from imasviz.VizUtils.QVizGlobalValues import GlobalFonts
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlotView import QVizTablePlotView


class QVizConfigurationListsWindow(QDialog):
    """The configuration frame, containing tabs dealing with different
       configuration files.
    """

    def __init__(self, parent=None):
        super(QVizConfigurationListsWindow, self).__init__(parent)
        self.DTVFrame = parent
        self.setWindowTitle("Apply Configurations")
        self.tabWidget = None
        self.listView = None
        self.initInterface()

    def initInterface(self):
        """Initialize tabs.
        """
        self.tabWidget = QTabWidget()
        self.tabPlotConf = PlotConfigurationListsTab(parent=self)
        self.tabSignalListConf = ListOfSignalPathsListsTab(parent=self)

        self.tabWidget.addTab(self.tabPlotConf, 'Available Plot Configurations')
        self.tabWidget.addTab(self.tabSignalListConf, 'Available List of IDS paths')

        layout = QVBoxLayout()

        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabWidget)
        self.setLayout(layout)

    def updateList(self, listType='pcfg'):
        """Update list containing either plot configurations ('pcfg') or list
        of signal paths ('lsp').

        Arguments:
            listType (str) : String specifying which list to update
                             (either 'pcfg' (default)or 'lsp').
        """

        # Updating list of plot configurations
        if listType == 'pcfg':
            self.tabPlotConf.updateList()
        # Updating list of signal paths configuration
        elif listType == 'lsp':
            self.tabSignalListConf.updateList()


class CommonConfigurationRoutines(QObject):
    """Common configuration routines.
    """

    def __init__(self, parent=None):
        """
        Arguments:
            parent (QWidget) : QWidget object, representing one of the tabs in
                               the Configuration Lists Window.
        """
        super(CommonConfigurationRoutines, self).__init__()
        self.parent = parent

    @pyqtSlot()
    def applySignalSelection(self):
        """Apply signal selection from the config file - select signals (
        list of IDS paths) only.
        """
        # Get in-list position of the selection (config file name)
        selectedItems = self.parent.listWidget.selectedItems()

        if len(selectedItems) > 0:
            # Set the first selected item from the list
            # Note: Only one item can be selected at a time, so a list of one item
            # is provided
            selectedItem = selectedItems[0]

            # Get system path to the selected configuration file
            selectedFile = \
                QVizGlobalOperations.getConfigurationFilesDirectory() + \
                "/" + selectedItem.text()
            # Extract signal paths from the config file and add them to a list of
            # paths
            pathsList = QVizGlobalOperations.getSignalsPathsFromConfigurationFile(
                configFile=selectedFile)
            # First unselect all signals
            QVizUnselectAllSignals(dataTreeView=self.parent.DTVFrame.dataTreeView).execute()
            # Select the signals, defined by a path in a list of paths, in the
            # given wxDataTreeView (DTV) window
            QVizSelectSignals(dataTreeView=self.parent.DTVFrame.dataTreeView,
                              pathsList=pathsList).execute()
        else:
            pass

    @pyqtSlot(str)
    def removeConfiguration(self, configType):
        """Remove configuration file from the list.

        Arguments:
            configTyle (str) : Configuration file type/extension
                               ('pcfg' or 'lsp').
        """
        # Get the selection list (config file name)
        selectedItems = self.parent.listWidget.selectedItems()

        if len(selectedItems) > 0:
            # Set the first selected item from the list
            # Note: Only one item can be selected at a time, so a list of one item
            # is provided
            selectedItem = selectedItems[0]
            # Get system path to the selected configuration file
            selectedFile = \
                QVizGlobalOperations.getConfigurationFilesDirectory() + \
                '/' + selectedItem.text()
            # Get Yes/No answer (returns True/False)
            answer = \
                QVizGlobalOperations.YesNo(question='The configuation '
                                           + selectedFile
                                           + ' will be deleted. Are you sure?')
        else:
            answer = False
        if answer:  # If True
            print('Removing configuration: ' + selectedFile)
            try:
                # Remove the config file from the system directory, containing
                # containing all config files
                os.remove(selectedFile)
                # Remove the config file from the list
                self.parent.listWidget.removeItemWidget(selectedItem)
                # Refresh the list
                self.parent.configurationFilesList = \
                    QVizGlobalOperations.getConfFilesList(configType=configType)
                # Update the list (simple update() doesn't work)
                self.parent.updateList()
            except OSError:
                print("Unable to remove file: " + selectedFile)

    @staticmethod
    def setNoteLayout(DTVFrame):
        """Set layout containing the note.
        """
        layout_note = QVBoxLayout()
        layout_note.setSpacing(0)
        layout_note.setContentsMargins(10, 0, 10, 0)
        # - Set label
        label1 = QLabel()
        label1.setText('Note:')
        label1.setAlignment(Qt.AlignLeft)
        label1.setWordWrap(True)
        label1.setFixedHeight(25)
        label1.setFont(GlobalFonts.TITLE_MEDIUM)

        label2 = QLabel()
        label2.setText('The configuration will be applied ONLY to the single '
                       'currently opened IMAS database source:')
        label2.setAlignment(Qt.AlignLeft)
        label2.setWordWrap(True)
        label2.setFixedHeight(40)
        label2.setMaximumWidth(340)
        label2.setFont(GlobalFonts.TEXT_MEDIUM)

        label3 = QLabel()
        label3.setText(DTVFrame.windowTitle())
        label3.setAlignment(Qt.AlignLeft)
        label3.setWordWrap(True)
        label3.setFixedHeight(25)
        label3.setFont(GlobalFonts.TITLE_MEDIUM)

        layout_note.addWidget(label1)
        layout_note.addWidget(label2)
        layout_note.addWidget(label3)

        return layout_note


class PlotConfigurationListsTab(QWidget):
    """The configuration tab panel, listing the available plot configuration
       files and its features.
    """

    def __init__(self, parent=None):
        super(PlotConfigurationListsTab, self).__init__(parent)
        commonConf = CommonConfigurationRoutines(parent=self)
        self.DTVFrame = parent.DTVFrame
        self.dataTreeView = self.DTVFrame.dataTreeView

        # Set layout containing the list widget
        layout_list = QVBoxLayout()
        self.listWidget = self.createList()
        layout_list.addWidget(self.listWidget)

        # Set layout containing the buttons
        layout_buttons = QVBoxLayout()
        layout_buttons.setSpacing(5)
        layout_buttons.setContentsMargins(15, 0, 15, 0)
        # - Set buttons
        self.button1 = QPushButton('Apply selection and plot selected data')
        self.button1.clicked.connect(self.applyTablePlotViewConfiguration)
        self.button2 = QPushButton('Apply selection only')
        self.button2.clicked.connect(commonConf.applySignalSelection)
        self.button3 = QPushButton('Remove configuration')
        self.button3.clicked.connect(
            partial(commonConf.removeConfiguration, configType='pcfg'))

        # - Add buttons to the layout
        layout_buttons.addWidget(self.button1)
        layout_buttons.addWidget(self.button2)
        layout_buttons.addWidget(self.button3)

        # Set layout containing note
        layout_note = CommonConfigurationRoutines(parent=self) \
            .setNoteLayout(DTVFrame=parent.DTVFrame)

        # Set main layout and add the two 'sub' layouts:
        # list layout and buttons layout
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.addLayout(layout_list, 1)
        layout.addLayout(layout_buttons, 1)
        layout.addLayout(layout_note, 1)

        # Set widget layout
        self.setLayout(layout)

    def createList(self):
        """Create list of configuration files.
        """
        # Get sorted list of configuration files
        configurationFilesList = \
            sorted(QVizGlobalOperations.getConfFilesList(configType='pcfg'))

        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                       QSizePolicy.Expanding))
        # Set list widget
        listWidget = QListWidget(self)
        listWidget.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                             QSizePolicy.Expanding))

        # Add list of configuration files to list widget
        listWidget.addItems(configurationFilesList)

        return listWidget

    def updateList(self):
        """Update list of configuration files.
        """

        # Clear the widget list
        self.listWidget.clear()
        # Get sorted list of configuration files
        configurationFilesList = \
            sorted(QVizGlobalOperations.getConfFilesList(configType='pcfg'))

        # Add list of configuration files to list widget
        self.listWidget.addItems(configurationFilesList)

    def applyTablePlotViewConfiguration(self):
        """Apply signal selection from the config file - apply it directly
           to TablePlotView feature.
        """
        # TODO: the selection part could be made into a function as
        # removeConfiguration() and applySignalConfiguration() use this part of
        # code

        # Get the selection list (config file name)
        selectedItems = self.listWidget.selectedItems()

        if len(selectedItems) > 0:
            # Set the first selected item from the list
            # Note: Only one item can be selected at a time, so a list of one item
            # is provided
            selectedItem = selectedItems[0]
            # Get system path to the selected configuration file
            selectedFile = \
                QVizGlobalOperations.getConfigurationFilesDirectory() + \
                '/' + selectedItem.text()

            # Get next figurekey (label) for the TablePlotView
            figureKey = self.dataTreeView.imas_viz_api.getNextKeyForMultiplePlots()
            # Set up and show the TablePlotView using the config file
            QVizTablePlotView(self.dataTreeView,
                          figureKey=figureKey,
                          update=1,
                          configFile=selectedFile)
        else:
            pass


class ListOfSignalPathsListsTab(QWidget):
    """The configuration tab panel, listing the available lists of signal paths
       files and its features.
    """

    def __init__(self, parent=None):
        super(ListOfSignalPathsListsTab, self).__init__(parent)
        commonConf = CommonConfigurationRoutines(parent=self)
        self.DTVFrame = parent.DTVFrame

        # Set first layout containing the list widget
        layout_list = QVBoxLayout()
        # - Set list widget
        self.listWidget = self.createList()
        # - Add the list widget to the layout
        layout_list.addWidget(self.listWidget)

        # Set second layout containing the buttons
        layout_buttons = QVBoxLayout()
        layout_buttons.setSpacing(5)
        layout_buttons.setContentsMargins(15, 0, 15, 28)
        # - Set buttons
        self.button1 = QPushButton('Apply list of IDS paths to current IMAS '
                                   'database')
        self.button1.clicked.connect(commonConf.applySignalSelection)
        self.button2 = QPushButton('Remove configuration')
        self.button2.clicked.connect(
            partial(commonConf.removeConfiguration, configType='lsp'))

        # - Add buttons to the layout
        layout_buttons.addWidget(self.button1)
        layout_buttons.addWidget(self.button2)

        # Set layout containing note
        layout_note = commonConf.setNoteLayout(DTVFrame=parent.DTVFrame)

        # Set main layout and add the two 'sub' layouts:
        # list layout and buttons layout
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.addLayout(layout_list, 1)
        layout.addLayout(layout_buttons, 1)
        layout.addLayout(layout_note, 1)

        # Set widget layout
        self.setLayout(layout)

    def createList(self):
        """Create list of configuration files.
        """

        # Get sorted list of configuration files
        configurationFilesList = \
            sorted(QVizGlobalOperations.getConfFilesList(configType='lsp'))

        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                       QSizePolicy.Expanding))
        # Set list widget
        listWidget = QListWidget(self)
        listWidget.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                             QSizePolicy.Expanding))
        # Add list of configuration files to list widget
        listWidget.addItems(configurationFilesList)

        return listWidget

    def updateList(self):
        """Update list of configuration files.
        """

        # Clear the widget list
        self.listWidget.clear()
        # Get sorted list of configuration files
        configurationFilesList = \
            sorted(QVizGlobalOperations.getConfFilesList(configType='lsp'))

        # Add list of configuration files to list widget
        self.listWidget.addItems(configurationFilesList)
