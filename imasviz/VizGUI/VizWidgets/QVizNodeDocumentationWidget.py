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
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
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
        self.lNodeLabelTitle.setFont(GlobalFonts.TITLE_MEDIUM)
        # Set label text as selectable by mouse
        self.lNodeLabelTitle.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # - Set node label text
        self.lNodeLabelText = QLabel()
        self.lNodeLabelText.setText('/')
        self.lNodeLabelText.setAlignment(Qt.AlignLeft)
        self.lNodeLabelText.setWordWrap(True)
        self.lNodeLabelText.setMinimumHeight(25)
        self.lNodeLabelText.setMinimumWidth(340)
        self.lNodeLabelText.setFont(GlobalFonts.TEXT_MEDIUM)
        # Set label text as selectable by mouse
        self.lNodeLabelText.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # - Set node doc title
        self.lNodeDocTitle = QLabel()
        self.lNodeDocTitle.setText('Documentation: ')
        self.lNodeDocTitle.setAlignment(Qt.AlignLeft)
        self.lNodeDocTitle.setWordWrap(True)
        self.lNodeDocTitle.setMinimumHeight(25)
        self.lNodeDocTitle.setMinimumWidth(340)
        self.lNodeDocTitle.setFont(GlobalFonts.TITLE_MEDIUM)
        # Set label text as selectable by mouse
        self.lNodeDocTitle.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # - Set node title text
        self.lNodeDocText = QLabel()
        self.lNodeDocText.setText('/')
        self.lNodeDocText.setAlignment(Qt.AlignLeft)
        self.lNodeDocText.setWordWrap(True)
        self.lNodeDocText.setMinimumHeight(25)
        self.lNodeDocText.setMinimumWidth(340)
        self.lNodeDocText.setFont(GlobalFonts.TEXT_MEDIUM)
        # Set label text as selectable by mouse
        self.lNodeDocText.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # - Set node array size title
        self.lNodeArraySizeTitle = QLabel()
        self.lNodeArraySizeTitle.setText('Array size: ')
        self.lNodeArraySizeTitle.setAlignment(Qt.AlignLeft)
        self.lNodeArraySizeTitle.setWordWrap(True)
        self.lNodeArraySizeTitle.setMinimumHeight(25)
        self.lNodeArraySizeTitle.setMinimumWidth(340)
        self.lNodeArraySizeTitle.setFont(GlobalFonts.TITLE_MEDIUM)
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
        self.lNodeArraySizeText.setFont(GlobalFonts.TEXT_MEDIUM)
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
        self.lNodeArrayMinTitle.setFont(GlobalFonts.TITLE_MEDIUM)
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
        self.lNodeArrayMinText.setFont(GlobalFonts.TEXT_MEDIUM)
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
        self.lNodeArrayMaxTitle.setFont(GlobalFonts.TITLE_MEDIUM)
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
        self.lNodeArrayMaxText.setFont(GlobalFonts.TEXT_MEDIUM)
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
        self.lNodeArrayZerosTitle.setFont(GlobalFonts.TITLE_MEDIUM)
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
        self.lNodeArrayZerosText.setFont(GlobalFonts.TEXT_MEDIUM)
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
        self.lNodeArrayNansTitle.setFont(GlobalFonts.TITLE_MEDIUM)
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
        self.lNodeArrayNansText.setFont(GlobalFonts.TEXT_MEDIUM)
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
        self.lNodeArrayInfsTitle.setFont(GlobalFonts.TITLE_MEDIUM)
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
        self.lNodeArrayInfsText.setFont(GlobalFonts.TEXT_MEDIUM)
        # Set label text as selectable by mouse
        self.lNodeArrayInfsText.setTextInteractionFlags(
            Qt.TextSelectableByMouse)


        # - Set node contents title
        self.lNodeContentsTitle = QLabel()
        self.lNodeContentsTitle.setText('Content: ')
        self.lNodeContentsTitle.setAlignment(Qt.AlignLeft)
        self.lNodeContentsTitle.setWordWrap(True)
        self.lNodeContentsTitle.setMinimumHeight(25)
        self.lNodeContentsTitle.setMinimumWidth(340)
        self.lNodeContentsTitle.setFont(GlobalFonts.TITLE_MEDIUM)
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
        self.lNodeContentsText.setFont(GlobalFonts.TEXT_MEDIUM)
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

        # Hide displayed fields
        self.hideAllFields()

        # - Set node label
        node_label = None # Assigning default label
        if item.getDataName() is not None:
            node_label = str(item.getDataName())
        elif item.getName() is not None:
            node_label = str(item.getName())

        if node_label is None:
            return

        # - Set node documentation#
        node_doc = str(item.getDocumentation())


        # Set dictionary for node attributes
        node_contents_dict = self.initialize_dict(node_label, node_doc)

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

                    self.showFieldsForArrays()

                    self.lNodeArraySizeTitle.setText('Array size: ')
                    # Get string version of the array of values
                    n = 200
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

                # elif item.is0D():
                #     node_contents_dict['contents'] = str(node_array_contents)
                #     self.lNodeArraySizeTitle.setText(item.getDataType() + ' scalar')
                #     self.lNodeArraySizeText.setText('/')

                elif item.is2DOrLarger():

                    self.showFieldsForArrays()

                    self.lNodeArraySizeTitle.setText(item.getDataType() + ' array')
                    self.lNodeArraySizeTitle.setText('Array shape: ')
                    self.lNodeArraySizeText.setText(str(node_array_contents.shape))

            elif item.is0D():
                if node_label is not None:
                    self.showFieldsForScalars()
                    # - Set node contents
                    node_contents_dict = {}
                    node_contents_dict['name'] = node_label
                    node_contents_dict['documentation'] = node_doc
                    node_contents_dict['contents'] = item.getData()['0D_content']
                else:
                    self.showFieldsForContents()
                    node_contents_dict = {}
                    node_contents_dict['name'] = node_label
                    node_contents_dict['contents'] = item.getData()['0D_content']

            else:
                self.showMinimalDisplay()
                node_contents_dict = {}
                node_contents_dict['name'] = node_label
                node_contents_dict['documentation'] = node_doc

        else:
            self.showFieldsForIDSRoot()
            node_contents_dict = {}
            node_contents_dict['name'] = node_label
            node_contents_dict['documentation'] = node_doc

        if 'name' in node_contents_dict:
            self.lNodeLabelText.setText(node_contents_dict['name'])
        else:
            self.lNodeLabelText.setText('')

        if 'documentation' in node_contents_dict:
            self.lNodeDocText.setText(node_contents_dict['documentation'])
        else:
            self.lNodeDocText.setText('')

        if 'contents' in node_contents_dict:
            self.lNodeContentsText.setText(str(node_contents_dict['contents']))
        else:
            self.lNodeContentsText.setText('')

        if 'minimum' in node_contents_dict:
            self.lNodeArrayMinText.setText(str(node_contents_dict['minimum']))
        else:
            self.lNodeArrayMinText.setText('')

        if 'maximum' in node_contents_dict:
            self.lNodeArrayMaxText.setText(str(node_contents_dict['maximum']))
        else:
            self.lNodeArrayMaxText.setText('')

        if 'zeros' in node_contents_dict:
            self.lNodeArrayZerosText.setText(str(node_contents_dict['zeros']))
        else:
            self.lNodeArrayZerosText.setText('')

        if 'nans' in node_contents_dict:
            self.lNodeArrayNansText.setText(str(node_contents_dict['nans']))
        else:
            self.lNodeArrayNansText.setText('')

        if 'infs' in node_contents_dict:
            self.lNodeArrayInfsText.setText(str(node_contents_dict['infs']))
        else:
            self.lNodeArrayInfsText.setText('')


    def initialize_dict(self, node_label=None, node_doc=None):
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
        return node_contents_dict

    def hideAllFields(self):
        self.lNodeLabelTitle.setVisible(False)
        self.lNodeLabelText.setVisible(False)
        self.lNodeDocTitle.setVisible(False)
        self.lNodeDocText.setVisible(False)
        self.lNodeArraySizeTitle.setVisible(False)
        self.lNodeArraySizeText.setVisible(False)
        self.lNodeArrayMinTitle.setVisible(False)
        self.lNodeArrayMinText.setVisible(False)
        self.lNodeArrayMaxTitle.setVisible(False)
        self.lNodeArrayMaxText.setVisible(False)
        self.lNodeArrayZerosTitle.setVisible(False)
        self.lNodeArrayZerosText.setVisible(False)
        self.lNodeArrayNansTitle.setVisible(False)
        self.lNodeArrayNansText.setVisible(False)
        self.lNodeArrayInfsTitle.setVisible(False)
        self.lNodeArrayInfsText.setVisible(False)
        self.lNodeContentsTitle.setVisible(False)
        self.lNodeContentsText.setVisible(False)

    def showFieldsForArrays(self):
        self.showAllFields()

    def showFieldsForIDSRoot(self):
        self.showMinimalDisplay()

    def showMinimalDisplay(self):
        self.lNodeLabelTitle.setVisible(True)
        self.lNodeLabelText.setVisible(True)
        self.lNodeDocTitle.setVisible(True)
        self.lNodeDocText.setVisible(True)

    def showFieldsForScalars(self):
        self.lNodeLabelTitle.setVisible(True)
        self.lNodeLabelText.setVisible(True)
        self.lNodeDocTitle.setVisible(True)
        self.lNodeDocText.setVisible(True)
        self.lNodeContentsTitle.setVisible(True)
        self.lNodeContentsText.setVisible(True)

    def showFieldsForContents(self):
        self.lNodeLabelTitle.setVisible(True)
        self.lNodeLabelText.setVisible(True)
        self.lNodeContentsTitle.setVisible(True)
        self.lNodeContentsText.setVisible(True)


    def showAllFields(self):
        self.lNodeLabelTitle.setVisible(True)
        self.lNodeLabelText.setVisible(True)
        self.lNodeDocTitle.setVisible(True)
        self.lNodeDocText.setVisible(True)
        self.lNodeArraySizeTitle.setVisible(True)
        self.lNodeArraySizeText.setVisible(True)
        self.lNodeArrayMinTitle.setVisible(True)
        self.lNodeArrayMinText.setVisible(True)
        self.lNodeArrayMaxTitle.setVisible(True)
        self.lNodeArrayMaxText.setVisible(True)
        self.lNodeArrayZerosTitle.setVisible(True)
        self.lNodeArrayZerosText.setVisible(True)
        self.lNodeArrayNansTitle.setVisible(True)
        self.lNodeArrayNansText.setVisible(True)
        self.lNodeArrayInfsTitle.setVisible(True)
        self.lNodeArrayInfsText.setVisible(True)
        self.lNodeContentsTitle.setVisible(True)
        self.lNodeContentsText.setVisible(True)