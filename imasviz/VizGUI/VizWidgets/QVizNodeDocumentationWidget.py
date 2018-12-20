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

import numpy


from PyQt5.QtCore import Qt
from PyQt5.QtGui import QWidget, QLabel, QVBoxLayout, QScrollArea
from PyQt5.QtWidgets import QFormLayout

from imasviz.VizUtils.QVizGlobalValues import GlobalColors, GlobalFonts


class QVizNodeDocumentationWidget(QWidget):
    """Set node documentation widget, containing information about node label
    and description.
    """
    def __init__(self, parent=None):
        super(QVizNodeDocumentationWidget, self).__init__(parent=parent)

        # Set setting for numpy values to display whole arrays (otherwise only
        # few values get shown
        numpy.set_printoptions(threshold=numpy.nan)
        self.create()

    def create(self, documentation=['Node: ','...','Documentation: ','...',
                                    'Contents', '...'],
               title='QVizNodeDocumantationWidget'):
        """Create new node documentation widget.

        Arguments:
            documentation (4*str array) : An array containing 4 documentation
                                          strings: First title, first entry,
                                          second title, second entry.
            title (str)                 : Widget title.
        """

        # Set documentation
        # - Set text 1
        self.l1 = QLabel()
        self.l1.setText(documentation[0])
        self.l1.setAlignment(Qt.AlignLeft)
        self.l1.setWordWrap(True)
        self.l1.setMinimumHeight(25)
        self.l1.setMinimumWidth(340)
        self.l1.setFont(GlobalFonts.TITLE_BIG)
        # Set label text as selectable by mouse
        self.l1.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # - Set text 2
        self.l2 = QLabel()
        self.l2.setText(documentation[1])
        self.l2.setAlignment(Qt.AlignLeft)
        self.l2.setWordWrap(True)
        self.l2.setMinimumHeight(25)
        self.l2.setMinimumWidth(340)
        self.l2.setFont(GlobalFonts.TEXT_BIG)
        # Set label text as selectable by mouse
        self.l2.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # - Set text 3
        self.l3 = QLabel()
        self.l3.setText(documentation[2])
        self.l3.setAlignment(Qt.AlignLeft)
        self.l3.setWordWrap(True)
        self.l3.setMinimumHeight(25)
        self.l3.setMinimumWidth(340)
        self.l3.setFont(GlobalFonts.TITLE_BIG)
        # Set label text as selectable by mouse
        self.l3.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # - Set text 4
        self.l4 = QLabel()
        self.l4.setText(documentation[3])
        self.l4.setAlignment(Qt.AlignLeft)
        self.l4.setWordWrap(True)
        self.l4.setMinimumHeight(25)
        self.l4.setMinimumWidth(340)
        self.l4.setFont(GlobalFonts.TEXT_BIG)
        # Set label text as selectable by mouse
        self.l4.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # - Set text 5
        self.l5 = QLabel()
        self.l5.setText(documentation[4])
        self.l5.setAlignment(Qt.AlignLeft)
        self.l5.setWordWrap(True)
        self.l5.setMinimumHeight(25)
        self.l5.setMinimumWidth(340)
        self.l5.setFont(GlobalFonts.TITLE_BIG)
        # Set label text as selectable by mouse
        self.l5.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # - Set text 6
        self.l6 = QLabel()
        self.l6.setText(documentation[5])
        self.l6.setAlignment(Qt.AlignLeft)
        self.l6.setWordWrap(True)
        self.l6.setMinimumHeight(25)
        self.l6.setMinimumWidth(340)
        self.l6.setFont(GlobalFonts.TEXT_BIG)
        # Set label text as selectable by mouse
        self.l6.setTextInteractionFlags(Qt.TextSelectableByMouse)

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
        scrollLayout.setWidget(4, QFormLayout.LabelRole, self.l5)
        scrollLayout.setWidget(5, QFormLayout.LabelRole, self.l6)
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
            documentation (6*str array) : An array containing 6 documentation
                                          strings: First title, first entry,
                                          second title, second entry.
        """

        # TODO: switch to dictionary instead of a common array

        self.l1.setText(documentation[0])
        self.l2.setText(documentation[1])
        self.l3.setText(documentation[2])
        self.l4.setText(documentation[3])
        self.l5.setText(documentation[4])
        self.l6.setText(documentation[5])