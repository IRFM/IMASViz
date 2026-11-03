# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Four improvements of the Profiles window, measured on the case.

One window per IDS. The entry used to open a second panel for an IDS that
already had one -- each click a new top-level window, each with its own tabs
and its own occurrence choice for the case that already answered them. An entry
that finds its window opened brings it to the front instead, and keeps opening
a window of its own for any other IDS.

And a page that cannot read one of its quantities does not cost the user the
others: each of them says why in the panel that refused it, and the ones that
read keep their curves. The page that reads nothing is still refused out loud,
because an empty window is what the user is to find out about by clicking.

Both are measured on the reference case (WEST 54924 run 0, dictionary
3.35.0), where 50 quantities of one tab come back with 13 of them unreadable --
a page that is partly refused, which the case finally makes possible.
"""

import logging

import pytest
from PySide6.QtWidgets import QMainWindow, QMdiArea

from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizMainMenuController \
    import QVizMainMenuController
from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizProfilePanel import \
    QVizProfilePanel

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip)
from support import ownership

IDS_NAME = 'equilibrium'
OTHER_IDS = 'magnetics'
ROOT_WINDOW = 'IMASViz root window'

pytestmark = [pytest.mark.case, pytest.mark.dd, pytest.mark.ui]


class StubBrowser:
    def getActiveUsername(self):
        return ''

    def addUserDB(self, username):
        pass


class RootWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName(ROOT_WINDOW)
        self.MDI = QMdiArea(self)
        self.IMASdbBrowserWidget = StubBrowser()

    def getMDI(self):
        return self.MDI


@pytest.fixture(scope='module')
def session(qapp):
    """One case view, held for the whole file: the panels below are cheap, the
    view they ask is not (1,55 s to open the reference case)."""
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    from imasviz.VizDataSource.QVizDataSourceFactory import \
        QVizDataSourceFactory
    root = RootWindow()
    root.show()
    qapp.processEvents()
    api = QVizMainMenuController(root).openShotView.api
    source = QVizDataSourceFactory().create(CASE_URI)
    source.dd_version = CASE_DATA_DICTIONARY_VERSION
    view = api.CreateDataTree(source).dataTreeView
    api.ShowDataTree(view)
    qapp.processEvents()
    made = type('Session', (), {})()
    made.qapp = qapp
    made.root = root
    made.api = api
    made.view = view
    ownership.keep(made)
    return made


def entryFor(session, idsName):
    """The Profiles line the tree offers for that IDS root."""
    catalog = QVizPluginCatalog(session.view)
    entries = catalog.entriesFor(session.view.IDSRoots[idsName])
    for one in entries:
        if one.pluginName == 'VizProfiles_plugin':
            return one
    raise AssertionError('no Profiles entry among %r'
                         % ', '.join(one.pluginName for one in entries))


def panelsOf(session, idsName=None):
    """The live panels in the api's figures, in the order they were opened."""
    panels = [frame for frame in session.api.figureframes.values()
              if isinstance(frame, QVizProfilePanel)]
    if idsName is None:
        return panels
    return [one for one in panels if one.idsName == idsName]


# -----------------------------------------------------------------------------
# One window per IDS
# -----------------------------------------------------------------------------

def test_the_entry_of_an_ids_already_opened_bringst_its_window_forward(session,
                                                                       caplog):
    """A second click for the same IDS does not open a second window.

    It brings the one already opened to the front -- the same object under the
    same key -- instead of answering the case's questions all over again.
    Measured before the change: two `QVizProfilePanel` in `figureframes`, one
    per click, each with its own tabs for the same IDS.
    """
    entry = entryFor(session, IDS_NAME)

    QVizPluginCatalog(session.view).run(entry)
    session.qapp.processEvents()
    first = panelsOf(session, IDS_NAME)
    assert len(first) == 1, first

    with caplog.at_level(logging.INFO, logger=session.view.uri):
        QVizPluginCatalog(session.view).run(entry)
    session.qapp.processEvents()

    again = panelsOf(session, IDS_NAME)
    assert again == [first[0]], \
        'the same window stays the only one: got %r' % again
    assert session.api.figureframes[first[0].figureKey] is first[0], \
        'the window comes back under the key it was opened with'
    assert 'already open' in caplog.text


def test_the_entry_of_another_ids_still_opens_its_own_window(session):
    """The reuse is per IDS: another IDS still earns a window of its own."""
    QVizPluginCatalog(session.view).run(entryFor(session, OTHER_IDS))
    session.qapp.processEvents()

    panels = panelsOf(session)
    assert {one.idsName for one in panels} == {IDS_NAME, OTHER_IDS}, panels
    assert len(panels) == len({one for one in panels}), \
        'two windows, one per IDS'


# -----------------------------------------------------------------------------
# The width the panel leaves on its pages
# -----------------------------------------------------------------------------

def test_the_width_the_panel_leaves_on_its_pages(session):
    """What the combo says is what the command gets, and it starts on auto.

    Left auto -- the first entry, and the default, because a page of two panels
    laid in eight columns would be a surprise nobody asked for -- the command
    answers no width and the page keeps the one its size gives it. A number on
    the combo is carried through as the command's width, and `test_90` pins the
    layout that width buys.
    """
    panel = panelsOf(session, IDS_NAME)[0]

    assert panel.columnsBox.count() == 13, \
        'auto plus one entry per width, one to twelve'
    assert panel.columnsBox.currentText() == 'auto (from the page size)'
    assert panel.columns() is None
    panel.columnsBox.setCurrentIndex(3)
    assert panel.columns() == 3
    panel.columnsBox.setCurrentIndex(0)
    assert panel.columns() is None
