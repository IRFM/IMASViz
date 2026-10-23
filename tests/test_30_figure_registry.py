# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The figures that are open, and what the menus can do to them.

Show/Hide and Delete are how a user gets rid of a window. They work off the api's
bookkeeping, which is a dict keyed by a type prefix: the menus walk five hardcoded
prefixes, so a frame registered under any other prefix is invisible -- it cannot be
hidden, cannot be deleted, and stays in the bookkeeping when its window is closed,
which is how the figures drawn through the tensor read went unnoticed.

So what is pinned here is that the menus cover every kind of figure the commands
actually draw, that deleting one kind leaves the others alone, and that closing a
window gives its key back.

The frames themselves are stand-ins: this is about the registry and the menu built
from it, not about what a frame draws. The two real frame classes are covered by
their own tests.
"""

import pytest
from PySide6.QtWidgets import QMenu, QMdiArea, QWidget

from imasviz.VizUtils import FigureTypes
from imasviz.Viz_API import Viz_API
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling


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


def figureMenus(view, menu):
    """The Show/Hide and Delete menus, as the context menu builds them."""
    handling = QVizSignalHandling(dataTreeView=view)
    handling.menusShowHideAndDelete(menu)
    return menu


def test_a_figure_drawn_through_the_tensor_read_can_be_deleted(qapp, view):
    # The command that reads along the axes keeps its own key namespace, on
    # purpose -- the legacy "add to this figure" entries cannot fill it. Being
    # invisible to the plotting menu is one thing; being unreachable to Delete is
    # another: the user has no way left to close the window.
    openFigures(view, **{'SlicesPlot1': QWidget})
    menu = QMenu()
    figureMenus(view, menu)

    delete = subMenuNamed(menu, 'Delete')
    assert delete is not None
    for title in subMenuTitles(delete):
        if 'Slices' in title:
            break
    else:
        pytest.fail('no Delete submenu names the slice figures: %r'
                    % (subMenuTitles(delete),))


def subMenuTitles(menu):
    return [action.text() for action in menu.actions() if action.menu()]


@pytest.mark.parametrize('figureType,label', [
    (FigureTypes.TABLEPLOTTYPE, 'TablePlotView'),
    (FigureTypes.STACKEDPLOTTYPE, 'StackedPlotView'),
])
def test_every_legacy_figure_type_is_still_offered(qapp, view, figureType, label):
    # The label is what the user reads, so the types the menus know are part of
    # the interface: a rewrite that drops one drops a way to close a window.
    openFigures(view, **{figureType + '1': QWidget})
    menu = QMenu()
    figureMenus(view, menu)

    showHide = subMenuNamed(menu, 'Show/Hide')
    assert showHide is not None and showHide.isEnabled()
    assert subMenuNamed(showHide, label) is not None, subMenuTitles(showHide)
    assert actionNamed(subMenuNamed(showHide, label), figureType + '1') is not None


def test_the_legacy_figure_kind_is_not_offered_any_more(qapp, view):
    # 'Figure:' was the prefix of the legacy curve window, and that window is
    # gone. Its kind is out of MENU_ORDER, so the two menus walk no prefix that
    # a leftover key could match: a frame still registered under 'Figure:' stays
    # in the bookkeeping and is named by no line -- nothing hands that key out
    # again, and nothing pretends it can close one.
    assert 'Figure:' not in [figureType for _label, _icon, figureType
                             in FigureTypes.MENU_ORDER]
    assert not hasattr(FigureTypes, 'FIGURETYPE')
    openFigures(view, **{'Figure:1': QWidget})
    assert view.imas_viz_api.GetFiguresCount(figureType='Figure:') == 1
    menu = QMenu()
    figureMenus(view, menu)

    showHide = subMenuNamed(menu, 'Show/Hide')
    assert showHide is not None and not showHide.isEnabled()
    assert subMenuTitles(showHide) == []


def test_deleting_all_the_stacked_figures_leaves_the_tables_alone(qapp, view):
    # The two kinds are one type prefix apart, and the menu was written by
    # copying a block per kind: the StackedPlotView entry ended up wired to the
    # table prefix, so "Delete all the stacked figures" deleted the tables.
    openFigures(view, **{FigureTypes.TABLEPLOTTYPE + '1': QWidget,
                         FigureTypes.STACKEDPLOTTYPE + '1': QWidget})
    menu = QMenu()
    figureMenus(view, menu)

    delete = subMenuNamed(menu, 'Delete')
    stacked = subMenuNamed(delete, 'StackedPlotView')
    assert stacked is not None, subMenuTitles(delete)
    actionNamed(stacked, 'All').trigger()

    assert view.imas_viz_api.GetFiguresKeys(FigureTypes.TABLEPLOTTYPE) == \
           [FigureTypes.TABLEPLOTTYPE + '1']
    assert view.imas_viz_api.GetFiguresKeys(FigureTypes.STACKEDPLOTTYPE) == []


def test_closing_a_figure_window_gives_its_key_back(qapp, view):
    # The next key of a type is its count plus one, so a frame left in the
    # bookkeeping after its window was closed costs a key forever: the numbers on
    # the window titles only ever grow, and the menus keep offering a figure that
    # is no longer there.
    frame = QWidget()
    view.imas_viz_api.figureframes['SlicesPlot1'] = frame
    view.imas_viz_api.addPlotWidgetToMDI(frame)

    frame.parent().close()

    assert view.imas_viz_api.GetFiguresKeys('SlicesPlot') == []
