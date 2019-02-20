#!/usr/bin/env python3

"""

A SOLPS getIDS plugin for Qt designer.

"""

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtDesigner import QPyDesignerCustomWidgetPlugin

from plotEPGGD import plotEPGGD

class plotEPGGDplugin(QPyDesignerCustomWidgetPlugin):
    """Plugin for put_edge_ids functionality.
    """
    def __init__(self, parent=None):
        super(plotEPGGDplugin, self).__init__(parent)

    def createWidget(self, parent):
        return plotEPGGD(parent=parent, ids=None)

    def name(self):
        return "plotEPGGD"

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
        return '<widget class="plotEPGGD" name="plotEPGGD">\n</widget>'

    def includeFile(self):
        return "plotEPGGD"

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


