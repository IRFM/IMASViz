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

import numpy as np
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QWidget, QLabel, QVBoxLayout, QScrollArea
from PyQt5.QtWidgets import QFormLayout
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations


from imasviz.VizUtils.QVizGlobalValues import GlobalColors, GlobalFonts


class QVizNodeDocumentationWidget(QWidget):
    """Set node documentation widget, containing information about node label
    and description.
    """
    def __init__(self, parent=None):
        super(QVizNodeDocumentationWidget, self).__init__(parent=parent)

        # Set setting for numpy values to display whole arrays (otherwise only
        # few values get shown
        np.set_printoptions(threshold=sys.maxsize)
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

        # - Set node data stats

        # - Set node minimum array title
        self.lNodeArrayMinTitle = QLabel()
        self.lNodeArrayMinTitle.setText('Min: ')
        self.lNodeArrayMinTitle.setAlignment(Qt.AlignLeft)
        self.lNodeArrayMinTitle.setWordWrap(True)
        self.lNodeArrayMinTitle.setMinimumHeight(25)
        self.lNodeArrayMinTitle.setMinimumWidth(340)
        self.lNodeArrayMinTitle.setFont(GlobalFonts.TITLE_BIG)
        # Set label text as selectable by mouse
        self.lNodeArrayMinTitle.setTextInteractionFlags(
            Qt.TextSelectableByMouse)

        # - Set node minimum array text
        self.lNodeArrayMinText = QLabel()
        self.lNodeArrayMinText.setText('/')
        self.lNodeArrayMinText.setAlignment(Qt.AlignLeft)
        self.lNodeArrayMinText.setWordWrap(True)
        self.lNodeArrayMinText.setMinimumHeight(25)
        self.lNodeArrayMinText.setMinimumWidth(340)
        self.lNodeArrayMinText.setFont(GlobalFonts.TEXT_BIG)
        # Set label text as selectable by mouse
        self.lNodeArrayMinText.setTextInteractionFlags(
            Qt.TextSelectableByMouse)

        # - Set node maximum array title
        self.lNodeArrayMaxTitle = QLabel()
        self.lNodeArrayMaxTitle.setText('Max: ')
        self.lNodeArrayMaxTitle.setAlignment(Qt.AlignLeft)
        self.lNodeArrayMaxTitle.setWordWrap(True)
        self.lNodeArrayMaxTitle.setMinimumHeight(25)
        self.lNodeArrayMaxTitle.setMinimumWidth(340)
        self.lNodeArrayMaxTitle.setFont(GlobalFonts.TITLE_BIG)
        # Set label text as selectable by mouse
        self.lNodeArrayMaxTitle.setTextInteractionFlags(
            Qt.TextSelectableByMouse)

        # - Set node maximum array text
        self.lNodeArrayMaxText = QLabel()
        self.lNodeArrayMaxText.setText('/')
        self.lNodeArrayMaxText.setAlignment(Qt.AlignLeft)
        self.lNodeArrayMaxText.setWordWrap(True)
        self.lNodeArrayMaxText.setMinimumHeight(25)
        self.lNodeArrayMaxText.setMinimumWidth(340)
        self.lNodeArrayMaxText.setFont(GlobalFonts.TEXT_BIG)
        # Set label text as selectable by mouse
        self.lNodeArrayMaxText.setTextInteractionFlags(
            Qt.TextSelectableByMouse)

        # - Set node 'number of zeros' title
        self.lNodeArrayZerosTitle = QLabel()
        self.lNodeArrayZerosTitle.setText('Number of zeros: ')
        self.lNodeArrayZerosTitle.setAlignment(Qt.AlignLeft)
        self.lNodeArrayZerosTitle.setWordWrap(True)
        self.lNodeArrayZerosTitle.setMinimumHeight(25)
        self.lNodeArrayZerosTitle.setMinimumWidth(340)
        self.lNodeArrayZerosTitle.setFont(GlobalFonts.TITLE_BIG)
        # Set label text as selectable by mouse
        self.lNodeArrayZerosTitle.setTextInteractionFlags(
            Qt.TextSelectableByMouse)

        # - Set node maximum array text
        self.lNodeArrayZerosText = QLabel()
        self.lNodeArrayZerosText.setText('/')
        self.lNodeArrayZerosText.setAlignment(Qt.AlignLeft)
        self.lNodeArrayZerosText.setWordWrap(True)
        self.lNodeArrayZerosText.setMinimumHeight(25)
        self.lNodeArrayZerosText.setMinimumWidth(340)
        self.lNodeArrayZerosText.setFont(GlobalFonts.TEXT_BIG)
        # Set label text as selectable by mouse
        self.lNodeArrayZerosText.setTextInteractionFlags(
            Qt.TextSelectableByMouse)

        # - Set node 'number of Nan' title
        self.lNodeArrayNansTitle = QLabel()
        self.lNodeArrayNansTitle.setText('Invalid entries (nan): ')
        self.lNodeArrayNansTitle.setAlignment(Qt.AlignLeft)
        self.lNodeArrayNansTitle.setWordWrap(True)
        self.lNodeArrayNansTitle.setMinimumHeight(25)
        self.lNodeArrayNansTitle.setMinimumWidth(340)
        self.lNodeArrayNansTitle.setFont(GlobalFonts.TITLE_BIG)
        # Set label text as selectable by mouse
        self.lNodeArrayNansTitle.setTextInteractionFlags(
            Qt.TextSelectableByMouse)

        # - Set node maximum array text
        self.lNodeArrayNansText = QLabel()
        self.lNodeArrayNansText.setText('/')
        self.lNodeArrayNansText.setAlignment(Qt.AlignLeft)
        self.lNodeArrayNansText.setWordWrap(True)
        self.lNodeArrayNansText.setMinimumHeight(25)
        self.lNodeArrayNansText.setMinimumWidth(340)
        self.lNodeArrayNansText.setFont(GlobalFonts.TEXT_BIG)
        # Set label text as selectable by mouse
        self.lNodeArrayNansText.setTextInteractionFlags(
            Qt.TextSelectableByMouse)

        # - Set node 'number of Nan' title
        self.lNodeArrayInfsTitle = QLabel()
        self.lNodeArrayInfsTitle.setText('Invalid entries (inf): ')
        self.lNodeArrayInfsTitle.setAlignment(Qt.AlignLeft)
        self.lNodeArrayInfsTitle.setWordWrap(True)
        self.lNodeArrayInfsTitle.setMinimumHeight(25)
        self.lNodeArrayInfsTitle.setMinimumWidth(340)
        self.lNodeArrayInfsTitle.setFont(GlobalFonts.TITLE_BIG)
        # Set label text as selectable by mouse
        self.lNodeArrayInfsTitle.setTextInteractionFlags(
            Qt.TextSelectableByMouse)

        # - Set node maximum array text
        self.lNodeArrayInfsText = QLabel()
        self.lNodeArrayInfsText.setText('/')
        self.lNodeArrayInfsText.setAlignment(Qt.AlignLeft)
        self.lNodeArrayInfsText.setWordWrap(True)
        self.lNodeArrayInfsText.setMinimumHeight(25)
        self.lNodeArrayInfsText.setMinimumWidth(340)
        self.lNodeArrayInfsText.setFont(GlobalFonts.TEXT_BIG)
        # Set label text as selectable by mouse
        self.lNodeArrayInfsText.setTextInteractionFlags(
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
        scrollLayout.setWidget(4, QFormLayout.LabelRole,self.lNodeArraySizeTitle)
        scrollLayout.setWidget(5, QFormLayout.LabelRole, self.lNodeArraySizeText)
        scrollLayout.setWidget(6, QFormLayout.LabelRole, self.lNodeArrayMinTitle)
        scrollLayout.setWidget(7, QFormLayout.LabelRole, self.lNodeArrayMinText)
        scrollLayout.setWidget(8, QFormLayout.LabelRole, self.lNodeArrayMaxTitle)
        scrollLayout.setWidget(9, QFormLayout.LabelRole, self.lNodeArrayMaxText)
        scrollLayout.setWidget(10, QFormLayout.LabelRole, self.lNodeArrayZerosTitle)
        scrollLayout.setWidget(11, QFormLayout.LabelRole, self.lNodeArrayZerosText)
        scrollLayout.setWidget(12, QFormLayout.LabelRole, self.lNodeArrayNansTitle)
        scrollLayout.setWidget(13, QFormLayout.LabelRole, self.lNodeArrayNansText)
        scrollLayout.setWidget(14, QFormLayout.LabelRole, self.lNodeArrayInfsTitle)
        scrollLayout.setWidget(15, QFormLayout.LabelRole, self.lNodeArrayInfsText)
        scrollLayout.setWidget(16, QFormLayout.LabelRole, self.lNodeContentsTitle)
        scrollLayout.setWidget(17, QFormLayout.LabelRole, self.lNodeContentsText)

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

    def update(self, item, dataTreeView):
        """Update the text of the docked node documentation widget.

        Arguments:
            item: node from the tree (DTV)
        """

        # UPDATE NODE DOCUMENTATION WIDGET
        # - Set node label
        node_label = "..."  # Assigning default label
        if item.getDataName() is not None:
            node_label = str(item.getDataName())
        elif item.getName() is not None:
            node_label = str(item.getName())
        # - Set node documentation#
        node_doc = str(item.getDocumentation())

        # Set dictionary for node attributes
        node_contents_dict = {}
        node_contents_dict['name'] = node_label
        node_contents_dict['documentation'] = node_doc
        node_contents_dict['contents'] = '/'
        node_contents_dict['size'] = '/'
        node_contents_dict['minimum'] = '/'
        node_contents_dict['maximum'] = '/'
        node_contents_dict['zeros'] = '/'
        node_contents_dict['nans'] = '/'
        node_contents_dict['infs'] = '/'

        node_array_contents = ''
        # Don't obtain contents for full IDS root nodes
        if not item.isIDSRoot():

            if item.isDynamicData():
                # - Set node contents
                expression = 'dataTreeView.dataSource.ids[' + str(item.getOccurrence()) + '].' + str(item.getPath())
                expression = QVizGlobalOperations.makePythonPath(expression)
                # Get the array of values
                node_array_contents = eval(expression)

                if item.is1D():
                    self.lNodeArraySizeTitle.setText('Array size: ')
                    # Get string version of the array of values
                    n = 1000
                    try:
                        node_contents_dict['minimum'] = str(min(node_array_contents))
                        node_contents_dict['maximum'] = str(max(node_array_contents))
                        node_contents_dict['zeros'] = str(len(np.where(node_array_contents == 0)))
                        node_contents_dict['nans'] = str(np.count_nonzero(np.isnan(node_array_contents)))
                        node_contents_dict['infs'] = str(np.count_nonzero(np.isinf(node_array_contents)))
                    except:
                        pass
                    if len(node_array_contents) > n * 2:
                        node_contents_dict['contents'] = 'The array size is too ' \
                                                         'large for display. Showing first ' + str(n) \
                                                         + ' values: \n\n' \
                                                         + str(node_array_contents[:n]) + '\n...\n' \
                                                         + str(node_array_contents[-n:])
                    else:
                        node_contents_dict['contents'] = str(node_array_contents)
                    # Formatting the string
                    # Note: makes the node documentation slider a lot slower for
                    # large arrays!
                    # Numbered array:
                    # node_contents_dict['contents'] =  '\n'.join('{}: {}'.format(
                    #     *k) for k in enumerate(node_array_contents))
                    # Get size of the array in as string
                    node_contents_dict['size'] = str(len(node_array_contents))
                    self.lNodeArraySizeText.setText(node_contents_dict['size'])



                elif item.is0D():
                    node_contents_dict['contents'] = str(node_array_contents)
                    self.lNodeArraySizeTitle.setText(item.getDataType() + ' scalar')
                    self.lNodeArraySizeText.setText('/')

                elif item.is2DOrLarger():
                    self.lNodeArraySizeTitle.setText(item.getDataType() + ' array')
                    self.lNodeArraySizeTitle.setText('Array shape: ')
                    self.lNodeArraySizeText.setText(str(node_array_contents.shape))

        self.lNodeLabelText.setText(node_contents_dict['name'])
        self.lNodeDocText.setText(node_contents_dict['documentation'])
        self.lNodeContentsText.setText(node_contents_dict['contents'])

        if 'minimum' in node_contents_dict:
            self.lNodeArrayMinText.setText(node_contents_dict['minimum'])

        if 'maximum' in node_contents_dict:
            self.lNodeArrayMaxText.setText(node_contents_dict['maximum'])

        if 'zeros' in node_contents_dict:
            self.lNodeArrayZerosText.setText(node_contents_dict['zeros'])

        if 'nans' in node_contents_dict:
            self.lNodeArrayNansText.setText(node_contents_dict['nans'])

        if 'infs' in node_contents_dict:
            self.lNodeArrayInfsText.setText(node_contents_dict['infs'])

