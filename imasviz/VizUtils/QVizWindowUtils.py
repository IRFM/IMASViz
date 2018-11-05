#  Name   : windowUtils
#
#          General routines for use with PyQt QWindow, QWidget etc. objects.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, D. Penko
#****************************************************

from PyQt5.QtWidgets import QApplication

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
    screenGeometry=QApplication.instance().desktop().screenGeometry()
    screenWidth = screenGeometry.width()
    screenHeight = screenGeometry.height()
    return screenWidth, screenHeight