#!/usr/bin/env python3

"""

A SOLPS getIDS plugin for Qt designer.

"""

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtDesigner import QPyDesignerCustomWidgetPlugin

from getIDS import GetIDS

class getIDSplugin(QPyDesignerCustomWidgetPlugin):
    """Plugin for put_edge_ids functionality.
    """
    def __init__(self, parent=None):
        super(getIDSplugin, self).__init__(parent)

    def createWidget(self, parent):
        return GetIDS(parent)

    def name(self):
        return "GetIDS"

    def group(self):
        return "IMASViz"

    def icon(self):
        return QIcon(_logo_pixmap)

    def toolTip(self):
        return "Push button for getting IDS."

    def whatsThis(self):
        return ""

    def isContainer(self):
        return False

    def domXml(self):
        return '<widget class="GetIDS" name="getIDS">\n</widget>'

    def includeFile(self):
        return "getIDS"

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


