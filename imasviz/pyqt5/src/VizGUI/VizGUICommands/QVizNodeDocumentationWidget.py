#  Name   : QVizPlotWidget
#
#          Provides node documentation widget template.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

from PyQt5.QtGui import QWidget, QLabel, QVBoxLayout, QGridLayout, QFont, \
                        QDockWidget, QScrollArea
from PyQt5.QtCore import Qt, QSize, QRect
from imasviz.util.GlobalValues import GlobalColors, GlobalFonts

class QVizNodeDocumentationWidget(QWidget):
    """Set node documentation widget, containing information about node label
    and description.
    """
    def __init__(self, parent=None):
        super(QVizNodeDocumentationWidget, self).__init__(parent=parent)

        pass

        # self.create(dataTreeView, documentation, title)

    def create(self, dataTreeView,
               documentation=['Node: ','-','Documentation: ','-'],
               title='QVizNodeDocumantationWidget'):
        """Create new node documentation widget.

        Arguments:
            dataTreeView (QTreeWidget)  : DataTreeView object of the QTreeWidget.
            documantation (4*str array) : An array containing 4 documentation
                                          strings: First title, first entry,
                                          second title, second entry.
            title (str)                 : Widget title.
        """

        self.dataTreeView = dataTreeView

        # Get reference width, height and position (of the dataTreeWindowFrame)
        ref_width, ref_height, ref_pos_x, ref_pos_y = \
            self.getWindowGeometry(dataTreeView.parent)

        # Set widget size
        size = (ref_width, 300)

        # Set widget position
        pos = (ref_pos_x, ref_pos_y+ref_height)

        # Set documentation
        # - Set text
        self.l1 = QLabel()
        self.l2 = QLabel()
        self.l3 = QLabel()
        self.l4 = QLabel()
        self.l1.setText(documentation[0])
        self.l2.setText(documentation[1])
        self.l3.setText(documentation[2])
        self.l4.setText(documentation[3])
        self.l1.setAlignment(Qt.AlignLeft)
        self.l2.setAlignment(Qt.AlignLeft)
        self.l3.setAlignment(Qt.AlignLeft)
        self.l4.setAlignment(Qt.AlignLeft)
        self.l1.setWordWrap(True)
        self.l2.setWordWrap(True)
        self.l3.setWordWrap(True)
        self.l4.setWordWrap(True)
        # - Set fonts
        self.l1.setFont(GlobalFonts.TITLE)
        self.l2.setFont(GlobalFonts.TEXT)
        self.l3.setFont(GlobalFonts.TITLE)
        self.l4.setFont(GlobalFonts.TEXT)

        # Set scrollable area
        scrollArea = QScrollArea(self)
        scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        #scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scrollArea.setWidgetResizable(True)
        scrollArea.setEnabled(True)
        scrollContent = QWidget(scrollArea)

        # Set layout for scrollable area
        scrollLayout = QVBoxLayout(scrollContent)
        scrollLayout.addWidget(self.l1)
        scrollLayout.addWidget(self.l2)
        scrollLayout.addWidget(self.l3)
        scrollLayout.addWidget(self.l4)
        scrollContent.setLayout(scrollLayout)
        scrollArea.setWidget(scrollContent)

        # Set the layout (scrollable area)
        vBox = QVBoxLayout(self)
        vBox.addWidget(scrollArea)

        # QVizNodeDocumentationWidget settings
        self.setObjectName("QVizNodeDocumentationWidget")
        self.setWindowTitle("Node documentation")
        # - Set layout
        self.setLayout(vBox)
        # - Set panel background colour
        p = self.palette()
        p.setBrush(self.backgroundRole(), GlobalColors.LIGHT_CYAN)
        self.setPalette(p)
        self.setAutoFillBackground(True)
        # - Adjust size
        self.adjustSize()

    def update(self, documentation):
        """Update the text of the existing node documentation widget.

        Arguments:
            documantation (4*str array) : An array containing 4 documentation
                                          strings: First title, first entry,
                                          second title, second entry.
        """
        self.l1.setText(documentation[0])
        self.l2.setText(documentation[1])
        self.l3.setText(documentation[2])
        self.l4.setText(documentation[3])

    @staticmethod
    def getWindowGeometry(window):
        """ Get geometry (size, position ) of the QT window. Returns width,
        height, pos_x, pos_y.

        Arguments:
            window (QWindow) : PyQt window object.
        """

        width = window.width()
        height = window.height()
        pos_x = window.pos().x()
        pos_y = window.pos().y()

        return width, height, pos_x, pos_y

