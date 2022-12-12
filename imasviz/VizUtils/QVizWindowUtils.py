#  Name   : windowUtils
#
#          General routines for use with PyQt QWindow, QWidget etc. objects.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr
#
#
# ****************************************************
#     Copyright(c) 2022 - L. Fleury, D. Penko
# ****************************************************

from PySide6.QtWidgets import QApplication


def getWindowSize(window):
    """ Get Size of the QT window. Returns width, height.

    Arguments:
        window (QWindow) : PyQt window object.
    """

    width = window.width()
    height = window.height()

    return width, height


def getWindowPosition(window):
    """ Get position of the QT window. Returns pos_x, pos_y.
    Note: Unused.

    Arguments:
        window (QWindow) : PyQt window object.
    """

    pos_x = window.pos().x()
    pos_y = window.pos().y()

    return pos_x, pos_y


def getScreenGeometry():
    """Return screen resolution (width and height).
    """
    screenWidth, screenHeight = QApplication.instance().primaryScreen().size().toTuple()
    return screenWidth, screenHeight
