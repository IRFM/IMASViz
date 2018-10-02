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

from PyQt5.QtGui import QWidget, QLabel, QVBoxLayout, QGridLayout, QFont, QDockWidget
from PyQt5.QtCore import Qt, QSize
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

        self.l1.setFont(GlobalFonts.TITLE)
        self.l2.setFont(GlobalFonts.TEXT)
        self.l3.setFont(GlobalFonts.TITLE)
        self.l4.setFont(GlobalFonts.TEXT)

        vbox = QVBoxLayout()
        vbox.addWidget(self.l1)
        vbox.addStretch()
        vbox.addWidget(self.l2)
        vbox.addStretch()
        vbox.addWidget(self.l3)
        vbox.addStretch()
        vbox.addWidget(self.l4)

        # QVizNodeDocumentationWidget settings
        self.setObjectName("QVizNodeDocumentationWidget")
        self.setWindowTitle("Node documentation")
        # - Set layout
        self.setLayout(vbox)
        # - Set size in relation to DTV
        # self.resize(size[0], size[1])
        # self.setFixedWidth(size[0])
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

