#!/usr/bin/env python3

"""

A SOLPS getIDS plugin for Qt designer.

"""

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtDesigner import QPyDesignerCustomWidgetPlugin

from solpswidget import GetSOLPSWidget

class solpsplugin(QPyDesignerCustomWidgetPlugin):
    """Plugin for put_edge_ids functionality.
    """
    def __init__(self, parent=None):
        super(solpsplugin, self).__init__(parent)

    def createWidget(self, parent):
        return GetSOLPSWidget(parent)

    def name(self):
        return "GetSOLPSWidget"

    def group(self):
        return "SOLPS"

    def icon(self):
        return QIcon(_logo_pixmap)

    def toolTip(self):
        return "Push button for plotting IDS data."

    def whatsThis(self):
        return ""

    def isContainer(self):
        return False

    def domXml(self):
        return '<widget class="GetSOLPSWidget" name="solpswidget">\n</widget>'

    def includeFile(self):
        return "solpswidget"

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


