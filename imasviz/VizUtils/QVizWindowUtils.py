# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

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
