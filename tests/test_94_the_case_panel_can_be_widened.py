# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The case panel sits beside the MDI area on a splitter, and its width is a hand's, not a ratio's.

The panel of the URI list used to be stuck to a fixed 1:7 grid, whatever the
length of the URIs it held -- and a URI is a path. The layout was replaced by
a horizontal splitter built by one function of the module (the same way the
session's switch is one function, so a test does not have to build a machine
to reach the thing it is testing): these tests pin that the panel is to the
left of the MDI, that it starts at the old ratio, and that it can be widened
-- the gesture of the drag of the handle -- and put back.

The layout is reached through ``startAndMdiSplitter`` with two stand-in
widgets, not by building the whole main window -- which would build the
session of a machine that is not the one under test. The one fact that can
only be told by production -- that the window actually uses the splitter --
is read out of the source, the way these suites have always read out what a
refusal must not be loosened to.
"""

import ast
import importlib

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMdiArea, QWidget

from imasviz.VizGUI.QtVIZ_GUI import startAndMdiSplitter


def test_the_panel_is_laid_to_the_left_of_the_mdi(qapp):
    """The panel is the first child of a horizontal splitter, the MDI the second.

    The panel is the thing on the left the user widens, and it is left by
    definition: the case is named before it is looked at. The orientation and
    the order are the contract; the widths are the next test's.
    """
    panel, mdi = QWidget(), QMdiArea()
    splitter = startAndMdiSplitter(None, panel, mdi)
    assert splitter.orientation() == Qt.Horizontal
    assert splitter.widget(0) is panel
    assert splitter.widget(1) is mdi
    assert panel.parentWidget() is splitter
    assert mdi.parentWidget() is splitter


def test_the_panel_starts_at_the_old_ratio_and_can_be_widened(qapp):
    """A run that never touches the border sees the layout it had -- and one that does can.

    The split begins at the old 1:7, so the panel is the smaller of the two
    halves -- and then the drag the handle of the splitter allows is the only
    width that matters: the panel takes what it is given, and gives it back,
    which is the gesture a user makes when a URI is too long for the column.
    """
    panel, mdi = QWidget(), QMdiArea()
    splitter = startAndMdiSplitter(None, panel, mdi)
    splitter.resize(800, 600)
    splitter.show()
    qapp.processEvents()

    atRatio = panel.width()
    assert atRatio < mdi.width()

    splitter.setSizes([700, 100])
    qapp.processEvents()
    widened = panel.width()
    assert widened > atRatio

    splitter.setSizes([100, 700])
    qapp.processEvents()
    assert panel.width() < widened

    splitter.close()


def test_the_main_window_builds_its_central_from_the_splitter():
    """The window's init calls the splitter, not the fixed grid.

    The one fact a geometry test cannot reach: that the production window
    settles its central widget from ``startAndMdiSplitter``. Reading it out
    of the ``__init__`` body is how a regression back to a grid that cannot be
    widened shows up at the wrong line rather than as a panel that answers no
    drag.
    """
    module = importlib.import_module('imasviz.VizGUI.QtVIZ_GUI')
    with open(module.__file__) as source:
        tree = ast.parse(source.read())
    calls = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'QVizMainWindow':
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                    calls = [c.func.id for c in ast.walk(item)
                             if isinstance(c, ast.Call)
                             and isinstance(c.func, ast.Name)]
    assert calls is not None, 'QVizMainWindow.__init__ not found in the source'
    assert 'startAndMdiSplitter' in calls
