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
import sys


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
        numpy.set_printoptions(threshold=sys.maxsize)
        self.create()

    def create(self, title='QVizNodeDocumantationWidget'):
        """Create new node documentation widget.

        Arguments:
            documentation (4*str array) : An array containing 4 documentation
                                          strings: First title, first entry,
                                          second title, second entry.
            title (str)                 : Widget title.
        """

        # Set documentation
        # - Set node label title
        self.lNodeLabelTitle = QLabel()
        self.lNodeLabelTitle.setText('Node: ')
        self.lNodeLabelTitle.setAlignment(Qt.AlignLeft)
        self.lNodeLabelTitle.setWordWrap(True)
        self.lNodeLabelTitle.setMinimumHeight(25)
        self.lNodeLabelTitle.setMinimumWidth(340)
        self.lNodeLabelTitle.setFont(GlobalFonts.TITLE_BIG)
        # Set label text as selectable by mouse
        self.lNodeLabelTitle.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # - Set node label text
        self.lNodeLabelText = QLabel()
        self.lNodeLabelText.setText('/')
        self.lNodeLabelText.setAlignment(Qt.AlignLeft)
        self.lNodeLabelText.setWordWrap(True)
        self.lNodeLabelText.setMinimumHeight(25)
        self.lNodeLabelText.setMinimumWidth(340)
        self.lNodeLabelText.setFont(GlobalFonts.TEXT_BIG)
        # Set label text as selectable by mouse
        self.lNodeLabelText.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # - Set node doc title
        self.lNodeDocTitle = QLabel()
        self.lNodeDocTitle.setText('Documentation: ')
        self.lNodeDocTitle.setAlignment(Qt.AlignLeft)
        self.lNodeDocTitle.setWordWrap(True)
        self.lNodeDocTitle.setMinimumHeight(25)
        self.lNodeDocTitle.setMinimumWidth(340)
        self.lNodeDocTitle.setFont(GlobalFonts.TITLE_BIG)
        # Set label text as selectable by mouse
        self.lNodeDocTitle.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # - Set node title text
        self.lNodeDocText = QLabel()
        self.lNodeDocText.setText('/')
        self.lNodeDocText.setAlignment(Qt.AlignLeft)
        self.lNodeDocText.setWordWrap(True)
        self.lNodeDocText.setMinimumHeight(25)
        self.lNodeDocText.setMinimumWidth(340)
        self.lNodeDocText.setFont(GlobalFonts.TEXT_BIG)
        # Set label text as selectable by mouse
        self.lNodeDocText.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # - Set node array size title
        self.lNodeArraySizeTitle = QLabel()
        self.lNodeArraySizeTitle.setText('Array size: ')
        self.lNodeArraySizeTitle.setAlignment(Qt.AlignLeft)
        self.lNodeArraySizeTitle.setWordWrap(True)
        self.lNodeArraySizeTitle.setMinimumHeight(25)
        self.lNodeArraySizeTitle.setMinimumWidth(340)
        self.lNodeArraySizeTitle.setFont(GlobalFonts.TITLE_BIG)
        # Set label text as selectable by mouse
        self.lNodeArraySizeTitle.setTextInteractionFlags(
            Qt.TextSelectableByMouse)

        # - Set node array size text
        self.lNodeArraySizeText = QLabel()
        self.lNodeArraySizeText.setText('/')
        self.lNodeArraySizeText.setAlignment(Qt.AlignLeft)
        self.lNodeArraySizeText.setWordWrap(True)
        self.lNodeArraySizeText.setMinimumHeight(25)
        self.lNodeArraySizeText.setMinimumWidth(340)
        self.lNodeArraySizeText.setFont(GlobalFonts.TEXT_BIG)
        # Set label text as selectable by mouse
        self.lNodeArraySizeText.setTextInteractionFlags(
            Qt.TextSelectableByMouse)

        # - Set node contents title
        self.lNodeContentsTitle = QLabel()
        self.lNodeContentsTitle.setText('Contents: ')
        self.lNodeContentsTitle.setAlignment(Qt.AlignLeft)
        self.lNodeContentsTitle.setWordWrap(True)
        self.lNodeContentsTitle.setMinimumHeight(25)
        self.lNodeContentsTitle.setMinimumWidth(340)
        self.lNodeContentsTitle.setFont(GlobalFonts.TITLE_BIG)
        # Set label text as selectable by mouse
        self.lNodeContentsTitle.setTextInteractionFlags(
            Qt.TextSelectableByMouse)

        # - Set node contents text
        self.lNodeContentsText = QLabel()
        self.lNodeContentsText.setText('/')
        self.lNodeContentsText.setAlignment(Qt.AlignLeft)
        self.lNodeContentsText.setWordWrap(True)
        self.lNodeContentsText.setMinimumHeight(25)
        self.lNodeContentsText.setMinimumWidth(340)
        self.lNodeContentsText.setFont(GlobalFonts.TEXT_BIG)
        # Set label text as selectable by mouse
        self.lNodeContentsText.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # Set scrollable area
        scrollArea = QScrollArea(self)
        scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        #scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scrollArea.setWidgetResizable(True)
        scrollArea.setEnabled(True)
        scrollContent = QWidget(scrollArea)

        # Set layout for scrollable area
        scrollLayout = QFormLayout(scrollContent)
        scrollLayout.setWidget(0, QFormLayout.LabelRole, self.lNodeLabelTitle)
        scrollLayout.setWidget(1, QFormLayout.LabelRole, self.lNodeLabelText)
        scrollLayout.setWidget(2, QFormLayout.LabelRole, self.lNodeDocTitle)
        scrollLayout.setWidget(3, QFormLayout.LabelRole, self.lNodeDocText)
        scrollLayout.setWidget(4, QFormLayout.LabelRole,
                               self.lNodeArraySizeTitle)
        scrollLayout.setWidget(5, QFormLayout.LabelRole, self.lNodeArraySizeText)
        scrollLayout.setWidget(6, QFormLayout.LabelRole,
                               self.lNodeContentsTitle)
        scrollLayout.setWidget(7, QFormLayout.LabelRole, self.lNodeContentsText)
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

    def update(self, node_contents_dict, sizeCaption='Array size: '):
        """Update the text of the docked node documentation widget.

        Arguments:
            node_contents_dict (dict) : Dictionary holding node attributes
                                        (e.g. (also keys) name, documentation,
                                        size, contents)
        """
        if 'sizeCaption' not in node_contents_dict:
            self.lNodeArraySizeTitle.setText('Array size: ')
        else:
            self.lNodeArraySizeTitle.setText(node_contents_dict['sizeCaption'])
        self.lNodeLabelText.setText(node_contents_dict['name'])
        self.lNodeDocText.setText(node_contents_dict['documentation'])
        if 'size' not in node_contents_dict:
            self.lNodeArraySizeText.setText(node_contents_dict[''])
        else:
            self.lNodeArraySizeText.setText(node_contents_dict['size'])
        self.lNodeContentsText.setText(node_contents_dict['contents'])

