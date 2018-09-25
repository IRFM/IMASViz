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

from PyQt5.QtGui import QWidget, QLabel, QVBoxLayout, QGridLayout
from PyQt5.QtCore import Qt

class QVizNodeDocumentationWidget(QWidget):

    def __init__(self, parent=None, documentation='', size=(500,400),
                 title='QVizNodeDocumantationWidget'):
        super(QVizNodeDocumentationWidget, self).__init__(parent=parent)

        l1 = QLabel()
        l2 = QLabel()
        l3 = QLabel()
        l4 = QLabel()

        l1.setText(documentation[0])
        l2.setText(documentation[1])
        l3.setText(documentation[2])
        l4.setText(documentation[3])

        l1.setAlignment(Qt.AlignLeft)
        l2.setAlignment(Qt.AlignLeft)
        l3.setAlignment(Qt.AlignLeft)
        l4.setAlignment(Qt.AlignLeft)

        vbox = QVBoxLayout()
        vbox.addWidget(l1)
        vbox.addStretch()
        vbox.addWidget(l2)
        vbox.addStretch()
        vbox.addWidget(l3)
        vbox.addStretch()
        vbox.addWidget(l4)

        # QVizNodeDocumentationWidget settings
        self.setObjectName("QVizNodeDocumentationWidget")
        self.setWindowTitle("Node documentation")
        # self.resize(250, 150)
        self.move(300, 300)
        self.setLayout(vbox)
