# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The figures that are open, and what the *Windows* menu can do to them.

The *Windows* menu works off the api's bookkeeping, which is a dict keyed by a
type prefix: the menu walks ``FigureTypes.MENU_ORDER``, so a frame registered
under any other prefix is invisible -- it cannot be hidden, cannot be deleted,
and stays in the bookkeeping when its window is closed. That is how the figures
drawn through the tensor read went unnoticed before their prefix joined the list.

So what is pinned here is that the menu covers every kind of figure the commands
actually draw, that deleting one kind leaves the others alone, and what closing a
window costs the key it was addressed by -- which since T52 is not the same thing
as deleting it.

The frames themselves are stand-ins: this is about the registry and the menu built
from it, not about what a frame draws. The two real frame classes are covered by
their own tests, and the close box in all three of its shapes by ``test_86``.
"""

import pytest
from PySide6.QtWidgets import QMenu, QMdiArea, QWidget

from imasviz.VizUtils import FigureTypes
from imasviz.VizUtils.QVizGlobalValues import QVizPreferences
from imasviz.Viz_API import Viz_API
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizWindowMenu import \
    QVizWindowMenu


@pytest.fixture
def view(qapp):
    """One shot view and the api it reports its figures to, with an MDI area."""
    from PySide6.QtCore import QObject

    class FakeSource(QObject):
        def __init__(self, uri):
            super().__init__()
            self.uri = uri

    class FakeView(QObject):
        def __init__(self):
            super().__init__()
            self.uri = 'imas:hdf5?case=1'
            self.dataSource = FakeSource(self.uri)
            self.selectedItem = None

    view = FakeView()
    view.imas_viz_api = Viz_API(parent=QMdiArea())
    view.imas_viz_api.DTVlist = [view]
    return view


@pytest.fixture(autouse=True)
def closeBoxKeepsTheWindow(monkeypatch):
    """The default of the application, so a test that changes it says so."""
    monkeypatch.setattr(QVizPreferences, 'Close_button_deletes', 0)


def openFigures(view, **keyByType):
    """Register one stand-in frame per figure type, as a command would."""
    for key, frameClass in keyByType.items():
        view.imas_viz_api.figureframes[key] = frameClass()
    return view


def subMenuNamed(menu, title):
    for action in menu.actions():
        if action.menu() is not None and action.text() == title:
            return action.menu()
    return None


def actionNamed(menu, title):
    for action in menu.actions():
        if action.text() == title:
            return action
    return None


def titles(menu):
    return [action.text() for action in menu.actions()
            if not action.isSeparator()]


def allLine(menu, firstKey, allTitle=QVizWindowMenu.ALL):
    """The *All* line of the group that `firstKey` opens in the *Delete* menu.

    The groups are separated, not nested, and a group opens with the line of its
    first window, so the key says which group is meant.
    """
    groups, current = {}, None
    for action in menu.actions():
        if action.isSeparator():
            current = None
        elif current is None:
            current = action.text()
            groups[current] = []
        if action.text() == allTitle:
            groups[current].append(action)
    if firstKey not in groups or not groups[firstKey]:
        raise AssertionError('no %r line for the group of %r in %r'
                             % (allTitle, firstKey, titles(menu)))
    return groups[firstKey][0]


def windowsMenu(view):
    """The *Windows* menu, as a menu bar builds it."""
    menu = QMenu()
    QVizWindowMenu(menu, view.imas_viz_api).show()
    return menu


def test_a_figure_drawn_through_the_tensor_read_can_be_deleted(qapp, view):
    # The command that reads along the axes keeps its own key namespace, on
    # purpose -- the legacy "add to this figure" entries cannot fill it. Being
    # invisible to the plotting menu is one thing; being unreachable to Delete is
    # another: the user has no way left to close the window.
    openFigures(view, **{'SlicesPlot1': QWidget})
    delete = subMenuNamed(windowsMenu(view), QVizWindowMenu.DELETE)

    assert delete is not None and delete.isEnabled()
    assert titles(delete) == ['SlicesPlot1', QVizWindowMenu.ALL]


@pytest.mark.parametrize('figureType,label', [
    (FigureTypes.TABLEPLOTTYPE, 'TablePlotView'),
    (FigureTypes.STACKEDPLOTTYPE, 'StackedPlotView'),
])
def test_every_legacy_figure_type_is_still_offered(qapp, view, figureType,
                                                   label):
    # The label is what the user reads and the group a line is drawn in, so the
    # kinds the menu knows are part of the interface: a rewrite that drops one
    # drops a way to close a window.
    key = figureType + '1'
    frame = QWidget()
    view.imas_viz_api.figureframes[key] = frame
    menu = windowsMenu(view)

    line = actionNamed(menu, key)
    assert line is not None and line.isCheckable()
    # The check reports the screen, not the registry: this stand-in was never put
    # on it, so its line is unchecked -- and the same line is checked as soon as
    # the window is shown, because the menu is redrawn on every opening.
    assert line.isChecked() is False
    view.imas_viz_api.showHideWindow(frame)
    assert actionNamed(windowsMenu(view), key).isChecked() is True
    # The kind is the record's group, which is what the *Delete* sub-menu groups
    # by and what the tooltip of the line says.
    record = view.imas_viz_api.openWindows()[0]
    assert record.kindLabel == label
    assert titles(subMenuNamed(menu, QVizWindowMenu.DELETE)) == [key,
                                                                 QVizWindowMenu.ALL]


def test_the_legacy_figure_kind_is_not_offered_any_more(qapp, view):
    # 'Figure:' was the prefix of the legacy curve window, and that window is
    # gone. Its kind is out of MENU_ORDER, so the menu walks no prefix that a
    # leftover key could match: a frame still registered under 'Figure:' stays
    # in the bookkeeping and is named by no line -- nothing hands that key out
    # again, and nothing pretends it can close one. The one line the menu does
    # draw is the named empty state, not the key it was registered under.
    assert 'Figure:' not in [figureType for _label, _icon, figureType
                             in FigureTypes.MENU_ORDER]
    assert not hasattr(FigureTypes, 'FIGURETYPE')
    openFigures(view, **{'Figure:1': QWidget})
    assert view.imas_viz_api.GetFiguresCount(figureType='Figure:') == 1
    menu = windowsMenu(view)

    assert [a.text() for a in menu.actions()] == [QVizWindowMenu.NO_WINDOW]
    assert menu.isEnabled() is True
    assert menu.actions()[0].isEnabled() is False


def test_deleting_all_the_stacked_figures_leaves_the_tables_alone(qapp, view):
    # The two kinds are one type prefix apart, and the menu was written by
    # copying a block per kind: the StackedPlotView entry ended up wired to the
    # table prefix, so "Delete all the stacked figures" deleted the tables.
    openFigures(view, **{FigureTypes.TABLEPLOTTYPE + '1': QWidget,
                         FigureTypes.STACKEDPLOTTYPE + '1': QWidget})
    delete = subMenuNamed(windowsMenu(view), QVizWindowMenu.DELETE)

    allLine(delete, FigureTypes.STACKEDPLOTTYPE + '1').trigger()

    assert view.imas_viz_api.GetFiguresKeys(FigureTypes.TABLEPLOTTYPE) == \
           [FigureTypes.TABLEPLOTTYPE + '1']
    assert view.imas_viz_api.GetFiguresKeys(FigureTypes.STACKEDPLOTTYPE) == []


def test_closing_a_figure_with_its_box_keeps_the_key_that_deletes_it_gives_back(
        qapp, view):
    """Two gestures, two answers -- and the preference says which is which.

    The next key of a type is one past the highest still open, so a frame left in
    the bookkeeping after its window was closed costs a key for the rest of the
    run; and a frame taken out of the bookkeeping while its window is still on
    screen costs a window nobody can reach. Measured before the rule: a closed
    figure left ``figureframes`` empty, its subwindow hidden in the area, and the
    next curve was handed ``SlicesPlot1`` again.

    So the box hides -- the window keeps its key and the menu keeps naming it,
    unchecked -- and the key comes back with the *Delete* line, or with the box
    when ``Close_button_deletes`` says the box means it.
    """
    frame = QWidget()
    view.imas_viz_api.figureframes['SlicesPlot1'] = frame
    view.imas_viz_api.addPlotWidgetToMDI(frame)
    window = frame.parent()

    window.close()
    assert view.imas_viz_api.GetFiguresKeys('SlicesPlot') == ['SlicesPlot1']
    assert window.isHidden()

    # The *Delete* line is the one that ends a window.
    delete = subMenuNamed(windowsMenu(view), QVizWindowMenu.DELETE)
    actionNamed(delete, 'SlicesPlot1').trigger()
    assert view.imas_viz_api.GetFiguresKeys('SlicesPlot') == []

    # And the box does the same when the user asked for that behaviour.
    QVizPreferences.Close_button_deletes = 1
    other = QWidget()
    view.imas_viz_api.figureframes['SlicesPlot2'] = other
    view.imas_viz_api.addPlotWidgetToMDI(other)
    other.parent().close()
    assert view.imas_viz_api.GetFiguresKeys('SlicesPlot') == []
