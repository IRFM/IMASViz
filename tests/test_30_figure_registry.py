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
as deleting it. The registry answers one question besides the menu's: which window
a given plugin entry already drew, asked of the stamp that entry left on the frame
(``openWindowOfPluginEntry``), because the key says the kind and nothing else says
the entry.

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


def stampedFrame(uri, plugin, entry, occurrence, time=None, idsName='equilibrium'):
    """A stand-in frame carrying the stamp one plugin entry leaves on it."""
    from imasviz.VizPlugins.VizPlugin import QVizPluginWindow
    frame = QWidget()
    frame.pluginWindow = QVizPluginWindow(uri=uri, plugin=plugin, entry=entry,
                                          ids=idsName,
                                          occurrence=occurrence, time=time)
    return frame


def test_the_stamp_answers_which_entry_drew_which_window(qapp, view):
    """The stamp is the only place saying *which* entry drew a window.

    The key says the kind and the registry says the case; neither says the entry.
    So the only way a second call of one entry can be drawn into the window that
    stands instead of opening a second over it is to ask the stamp the entry left
    when it drew that window -- which is what `openWindowOfPluginEntry` does, and
    what it refuses for anything the entry did not draw.
    """
    api = view.imas_viz_api
    api.figureframes['EquiSurfaces:1'] = stampedFrame(view.uri, 'equilibriumsurfaces',
                                                      0, 0)

    assert api.openWindowOfPluginEntry(view.uri, 'equilibriumsurfaces', 0,
                                       0) == 'EquiSurfaces:1'
    # Another entry of the same plugin is another window, and so is another
    # occurrence of the same entry, or the same entry of another case.
    assert api.openWindowOfPluginEntry(view.uri, 'equilibriumsurfaces', 1,
                                       0) is None
    assert api.openWindowOfPluginEntry(view.uri, 'equilibriumsurfaces', 0,
                                       1) is None
    assert api.openWindowOfPluginEntry('imas:hdf5?case=2', 'equilibriumsurfaces',
                                       0, 0) is None
    # A window no plugin drew is not a window to draw into, whatever its key.
    api.figureframes['Plot1'] = QWidget()
    assert api.openWindowOfPluginEntry(view.uri, 'VizProfiles_plugin', 0,
                                       0) is None


def test_one_entry_asked_on_several_ids_answers_the_window_of_the_one_asked(qapp,
                                                                            view):
    """The Profiles line is one entry, offered on every branch of the case.

    Two panels of one case then carry the same plugin, the same entry and the
    same occurrence: only the branch the entry ran on tells them apart. So the
    ask has to name it, or a call after the `equilibrium` panel would be
    answered with the `magnetics` window -- the same gesture drawn into the
    wrong window, which no count of windows would notice.
    """
    api = view.imas_viz_api
    for key, idsName in (('PlotView:1', 'equilibrium'),
                         ('PlotView:2', 'magnetics')):
        api.figureframes[key] = stampedFrame(view.uri, 'VizProfiles_plugin', 0,
                                             0, idsName=idsName)

    assert api.openWindowOfPluginEntry(view.uri, 'VizProfiles_plugin', 0, 0,
                                       ids_name='equilibrium') == 'PlotView:1'
    assert api.openWindowOfPluginEntry(view.uri, 'VizProfiles_plugin', 0, 0,
                                       ids_name='magnetics') == 'PlotView:2'
    assert api.openWindowOfPluginEntry(view.uri, 'VizProfiles_plugin', 0, 0,
                                       ids_name='wall') is None


def test_a_window_the_close_box_only_hid_is_still_the_one_that_stands(qapp, view):
    """Hiding is not closing: the key, the stamp and the window all stay.

    A window closed with its own box is hidden and keeps its key, so a second
    call of its entry has to find it -- and put it back on the screen -- rather
    than open a second one the *Windows* menu lists beside a ghost.
    """
    api = view.imas_viz_api
    frame = stampedFrame(view.uri, 'equilibriumsurfaces', 0, 0)
    api.figureframes['EquiSurfaces:1'] = frame
    api.addPlotWidgetToMDI(frame)
    window = api.mdiWindowOf(frame)
    api.setWindowVisible(frame, False)
    assert window.isHidden()

    key = api.openWindowOfPluginEntry(view.uri, 'equilibriumsurfaces', 0, 0)
    assert key == 'EquiSurfaces:1'
    api.setWindowVisible(api.figureframes[key], True)
    assert not window.isHidden()


def test_the_instant_an_entry_answered_names_the_window_it_drew(qapp, view):
    """An entry that draws one window per instant answers one window per ask.

    Asked for 40 s, the window drawn at 40 s; asked for 44 s, a window of its
    own. Asked with no instant at all, any window of that entry answers, because
    the entries that ask no instant stamp `time=None` and have one window only.
    """
    api = view.imas_viz_api
    for key, time in (('EquiSurfaces:1', 40.0), ('EquiSurfaces:2', 44.0)):
        api.figureframes[key] = stampedFrame(view.uri, 'equilibriumsurfaces', 1,
                                             0, time=time)

    assert api.openWindowOfPluginEntry(view.uri, 'equilibriumsurfaces', 1, 0,
                                       40.0) == 'EquiSurfaces:1'
    assert api.openWindowOfPluginEntry(view.uri, 'equilibriumsurfaces', 1, 0,
                                       44.0) == 'EquiSurfaces:2'
    assert api.openWindowOfPluginEntry(view.uri, 'equilibriumsurfaces', 1, 0,
                                       48.0) is None
    assert api.openWindowOfPluginEntry(view.uri, 'equilibriumsurfaces', 1,
                                       0) in ('EquiSurfaces:1', 'EquiSurfaces:2')


def test_a_figure_drawn_through_the_tensor_read_can_be_deleted(qapp, view):
    # The command that reads along the axes keeps its own key namespace, on
    # purpose -- the legacy "add to this figure" entries cannot fill it. Being
    # invisible to the plotting menu is one thing; being unreachable to Delete is
    # another: the user has no way left to close the window.
    openFigures(view, **{'Plot1': QWidget})
    delete = subMenuNamed(windowsMenu(view), QVizWindowMenu.DELETE)

    assert delete is not None and delete.isEnabled()
    # The line says the word the title bar shows, not the key the registry
    # addresses -- `Plot1` is still the key, `Plot 1` the name on the
    # line.
    assert titles(delete) == ['Plot 1', QVizWindowMenu.ALL]


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
    next curve was handed ``Plot1`` again.

    So the box hides -- the window keeps its key and the menu keeps naming it,
    unchecked -- and the key comes back with the *Delete* line, or with the box
    when ``Close_button_deletes`` says the box means it.
    """
    frame = QWidget()
    view.imas_viz_api.figureframes['Plot1'] = frame
    view.imas_viz_api.addPlotWidgetToMDI(frame)
    window = frame.parent()

    window.close()
    assert view.imas_viz_api.GetFiguresKeys('Plot') == ['Plot1']
    assert window.isHidden()

    # The *Delete* line is the one that ends a window: it names the word the
    # bar shows, and the key it addresses stays out on the registry.
    delete = subMenuNamed(windowsMenu(view), QVizWindowMenu.DELETE)
    actionNamed(delete, 'Plot 1').trigger()
    assert view.imas_viz_api.GetFiguresKeys('Plot') == []

    # And the box does the same when the user asked for that behaviour.
    QVizPreferences.Close_button_deletes = 1
    other = QWidget()
    view.imas_viz_api.figureframes['Plot2'] = other
    view.imas_viz_api.addPlotWidgetToMDI(other)
    other.parent().close()
    assert view.imas_viz_api.GetFiguresKeys('Plot') == []
