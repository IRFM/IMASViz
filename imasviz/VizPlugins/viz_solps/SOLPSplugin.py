# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""

A SOLPS 'Plot edge_profiles GGD' widget for Qt designer.

"""

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtDesigner import QPyDesignerCustomWidgetPlugin

from SOLPSwidget import SOLPSwidget

class SOLPSplugin(QPyDesignerCustomWidgetPlugin):
    """Plugin for SOLPSwidget functionality.
    """
    def __init__(self, parent=None):
        super(SOLPSplugin, self).__init__(parent)


    def createWidget(self, parent):
        return SOLPSwidget(parent=parent, ids=None)

    def name(self):
        return "SOLPSwidget"

    def group(self):
        return "IMASViz"

    def icon(self):
        return QIcon(_logo_pixmap)

    def toolTip(self):
        return "Plot edge_profiles IDS GGD."

    def whatsThis(self):
        return ""

    def isContainer(self):
        return False

    def domXml(self):
        return '<widget class="SOLPSwidget" name="SOLPSwidget">\n</widget>'

    def includeFile(self):
        return "SOLPSwidget"

# Define the image used for the icon.
_logo_16x16_xpm = [
    "16 16 3 1 ",
    "  c black",
    ". c #0000E3",
    "X c None",
    "XXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXX",
    " XX X  XX  XX  X",
    " XX    XX  XX XX",
    " XX  X X   XXX  ",
    " XX XX X XX X  X",
    "XXXXXXXXXXXXXXXX",
    "................",
    "XXXXXXXXXXXXXXXX",
    "XXX XX X X   XXX",
    "XXX X XX XX XXXX",
    "XXXX  XX X XXXXX",
    "XXXX  XX X   XXX",
    "XXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXX"]

_logo_pixmap = QPixmap(_logo_16x16_xpm)


