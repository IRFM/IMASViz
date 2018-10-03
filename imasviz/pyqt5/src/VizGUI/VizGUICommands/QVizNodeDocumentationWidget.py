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
from PyQt5.QtWidgets import QFormLayout
from imasviz.util.GlobalValues import GlobalColors, GlobalFonts

class QVizNodeDocumentationWidget(QWidget):
    """Set node documentation widget, containing information about node label
    and description.
    """
    def __init__(self, parent=None):
        super(QVizNodeDocumentationWidget, self).__init__(parent=parent)

        self.create()

    def create(self, documentation=['Node: ','...','Documentation: ','...'],
               title='QVizNodeDocumantationWidget'):
        """Create new node documentation widget.

        Arguments:
            documentation (4*str array) : An array containing 4 documentation
                                          strings: First title, first entry,
                                          second title, second entry.
            title (str)                 : Widget title.
        """

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
        self.l1.setMinimumHeight(25)
        self.l2.setMinimumHeight(25)
        self.l3.setMinimumHeight(25)
        self.l4.setMinimumHeight(25)
        self.l1.setMinimumWidth(340)
        self.l2.setMinimumWidth(340)
        self.l3.setMinimumWidth(340)
        self.l4.setMinimumWidth(340)

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
        scrollLayout = QFormLayout(scrollContent)
        scrollLayout.setWidget(0, QFormLayout.LabelRole, self.l1)
        scrollLayout.setWidget(1, QFormLayout.LabelRole, self.l2)
        scrollLayout.setWidget(2, QFormLayout.LabelRole, self.l3)
        scrollLayout.setWidget(3, QFormLayout.LabelRole, self.l4)
        scrollContent.setLayout(scrollLayout)
        scrollArea.setWidget(scrollContent)

        # Set the layout (scrollable area)
        vBox = QVBoxLayout(self)
        vBox.addWidget(scrollArea)
        # - Remove scrollable area margin
        vBox.setContentsMargins(0, 0, 0, 0)

        # QVizNodeDocumentationWidget settings
        self.setObjectName("QVizNodeDocumentationWidget")
        self.setWindowTitle("Node Documentation")
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
        """Update the text of the docked node documentation widget.

        Arguments:
            documentation (4*str array) : An array containing 4 documentation
                                          strings: First title, first entry,
                                          second title, second entry.
        """

        self.l1.setText(documentation[0])
        self.l2.setText(documentation[1])
        self.l3.setText(documentation[2])
        self.l4.setText(documentation[3])