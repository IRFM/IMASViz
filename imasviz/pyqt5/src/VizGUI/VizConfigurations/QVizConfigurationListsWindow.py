#  Name   : QVizCOnfigurationlistsWindow
#
#          Container to handle configuration lists (list of signals,
#          MultiPlot configuration etc.)
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

from PyQt5.QtWidgets import (QListWidget, QDialog, QTabWidget, QVBoxLayout,
                             QPushButton, QWidget, QSizePolicy, QLabel)
from PyQt5.QtCore import Qt
from imasviz.util.GlobalValues import GlobalFonts

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
        self.tabSignnalListConf = ListOfSignalPathsListsTab(parent=self)

        self.tabWidget.addTab(self.tabPlotConf, 'Available Plot Configurations')
        self.tabWidget.addTab(self.tabSignnalListConf, 'Available List of IDS paths')

        layout = QVBoxLayout()

        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabWidget)
        self.setLayout(layout)

class CommonConfigurationRoutines():
    """Common configuration routines.
    """

    def __init__(self, parent=None):
        """
        Arguments:
            parent (QWidget) : QWidget object, representing one of the tabs in the
                               Configuration Lists Window.
        """
        self.parent = parent

    def applySignalSelection(self):
        pass
        # TODO

    def removeConfiguration(self):
        pass
        # TODO

    @staticmethod
    def setNoteLayout(DTVFrame):
        """Set layout containing the note.
        """
        layout_note = QVBoxLayout()
        layout_note.setSpacing(0)
        layout_note.setContentsMargins(10,0,10,0)
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

        # Set layout containing the list widget
        layout_list = QVBoxLayout()
        listWidget = self.addListTab()
        layout_list.addWidget(listWidget)

        # Set layout containing the buttons
        layout_buttons = QVBoxLayout()
        layout_buttons.setSpacing(5)
        layout_buttons.setContentsMargins(15, 0, 15, 0)
        # - Set buttons
        button1 = QPushButton('Apply to current IMAS database')
        button2 = QPushButton('Apply only list of IDS paths to current IMAS '
                              'database')
        button3 = QPushButton('Remove configuration')
        # - Add buttons to the layout
        layout_buttons.addWidget(button1)
        layout_buttons.addWidget(button2)
        layout_buttons.addWidget(button3)

        # Set layout containing note
        layout_note = CommonConfigurationRoutines(parent=self) \
            .setNoteLayout(DTVFrame = parent.DTVFrame)

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

    def addListTab(self):
        items = [str(i) for i in range(5)]
        # tab = QWidget()
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                       QSizePolicy.Expanding))
        # self.addTab(tab, 'Test')
        l = QListWidget(self)
        l.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                    QSizePolicy.Expanding))
        l.addItems(items)

        return l

class ListOfSignalPathsListsTab(QWidget):
    """The configuration tab panel, listing the available lists of signal paths
       files and its features.
    """
    def __init__(self, parent=None):
        super(ListOfSignalPathsListsTab, self).__init__(parent)

        # Set first layout containing the list widget
        layout_list = QVBoxLayout()
        # - Set list widget
        l = self.addListTab()
        # - Add the list widget to the layout
        layout_list.addWidget(l)

        # Set second layout containing the buttons
        layout_buttons = QVBoxLayout()
        layout_buttons.setSpacing(5)
        layout_buttons.setContentsMargins(15, 0, 15, 28)
        # - Set buttons
        button1 = QPushButton('Apply list of IDS paths to current IMAS '
                              'database')
        button2 = QPushButton('Remove configuration')
        # - Add buttons to the layout
        layout_buttons.addWidget(button1)
        layout_buttons.addWidget(button2)

        # Set layout containing note
        layout_note = CommonConfigurationRoutines(parent=self) \
            .setNoteLayout(DTVFrame = parent.DTVFrame)

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

    def addListTab(self):
        items = [str(i) for i in range(12)]
        # tab = QWidget()
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                      QSizePolicy.Expanding))
        # self.addTab(tab, 'Test')
        l = QListWidget(self)
        l.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                      QSizePolicy.Expanding))
        l.addItems(items)

        return l
