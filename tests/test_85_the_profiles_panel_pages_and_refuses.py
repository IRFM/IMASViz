# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What the Profiles panel refuses, pages, and moves -- measured on the case.

`test_51` runs the entry and pins what it puts on screen. This file pins the
answers around it: what happens when a group is longer than a page, when a whole
page cannot be read, when the abscissa changes under an open tab, and what the
folded time cursor at the bottom is allowed to move.

Four numbers from the reference case (WEST 54924 run 0, dictionary 3.35.0) set the
shape of the tests, because each one is a defect the old panel carried:

* **111 quantities on one array.** `equilibrium` occurrence 2 answers 111
  quantities in `time_slice/constraints`, so this case finally has a group longer
  than the page of 100. The old panel laid its pages out with two separate
  spellings of `tab * 100 + panels so far` (`VizProfiles.py:169` and `:234`), which
  stop agreeing as soon as more than one page arrives at once -- showing one
  quantity twice and skipping its neighbour. Ten years of occurrence 0, whose
  longest array answers 50 quantities, never reached that line.
* **a whole page that cannot be read.** `wall` occurrence 0 answers 22 quantities
  outside any array of structures, and every one of them is empty in this case: the
  command refuses the page, the panel says so in the log of the case, and **no
  window is left in `figureframes`** -- an empty table on screen is what the user
  would otherwise have to find out about by clicking through it.
* **4 rows, or 10.** The `magnetics` tab `bpol_probe` answers 4 quantities along
  the clock and 10 along each quantity's own axis, because that IDS is written at
  `homogeneous_time = 1` and its arrays have an index, not a time base, to run
  along. And `equilibrium`'s `time_slice/coordinate_system` answers **21**
  quantities of which **3** can be read along either reading: the 18 left out
  (`volume_element`, `r`, `z`, the Jacobian and friends) carry two axes of their
  own and are named on the tab, because a count that quietly drops rows reads as a
  bug in the panel.
* **one base, or none.** `equilibrium` answers a time base -- `time_slice`, 49
  slices at occurrence 0 -- and `magnetics` answers none, because it is written at
  `homogeneous_time = 1`. A cursor for a base no open window pins is a slider whose
  number nothing came from, so the band offers only what a window actually answers.
"""

import logging

import pytest
from PySide6.QtWidgets import QMainWindow, QMdiArea

from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizMainMenuController \
    import QVizMainMenuController
from imasviz.VizPlugins.VizPlugin import QVizPluginAnswers
from imasviz.VizPlugins.viz_Profiles.viz_profiles import \
    QVizProfileOffer as offerModule, QVizProfilePanel as panelModule
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizProfileOffer import \
    OWN_AXIS, PAGE
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizProfilePanel import \
    QVizProfilePanel

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip)
from support import ownership

IDS_NAME = 'equilibrium'
ROOT_WINDOW = 'IMASViz root window'

# `equilibrium` occurrence 2: the one array of this case longer than a page.
LONG_ARRAY = 'time_slice/constraints'
LONG_QUANTITIES = 111
# The same array at occurrence 0 answers 30, so the paging below is about the case,
# not about a number the panel invented.
SAME_ARRAY_AT_OCCURRENCE_0 = 30
# The page the paging tests below ask the code to lay out. The shipped page stays
# 100 -- it is what the two list-level tests pin on occurrence 2, where drawing it
# would cost 45 s (see `test_the_next_page_opens_a_window_of_its_own`).
SMALL_PAGE = 10

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


def panelFor(session, idsName, occurrence):
    """A panel of that IDS, with its tabs built -- the cost includes the load."""
    panel = ownership.keep(QVizProfilePanel(session.api, session.view, idsName,
                                            occurrence))
    session.qapp.processEvents()
    return panel


def tabNamed(panel, title):
    for index in range(panel.tabs.count()):
        if panel.tabs.tabText(index) == title:
            return panel.tabs.widget(index)
    raise AssertionError('no %r tab among %r'
                         % (title, [panel.tabs.tabText(index)
                                    for index in range(panel.tabs.count())]))


# --------------------------------------------------------------------------
# A group longer than a page
# --------------------------------------------------------------------------

def test_a_group_longer_than_a_page_is_paged_without_a_gap(session):
    """111 quantities, two pages, nothing shown twice and nothing skipped.

    Measured: page 1 holds 100 and page 2 holds the 11 left, and the two pages
    read end to end are exactly `following(abscissa)`. The old panel spelled the
    same arithmetic in two places and the two spellings disagreed as soon as a
    second page arrived: measured before the fix, quantity 100 appeared twice and
    101 never appeared at all.
    """
    panel = panelFor(session, IDS_NAME, 2)
    tab = tabNamed(panel, LONG_ARRAY)
    everything = tab.group.following(panel.abscissa())
    pages = tab.pages()

    assert len(everything) == LONG_QUANTITIES
    assert [len(page) for page in pages] == [PAGE, LONG_QUANTITIES - PAGE]
    assert [leaf for page in pages for leaf in page] == everything, \
        'a quantity is skipped or shown twice'
    paths = [leaf.getPath() for page in pages for leaf in page]
    assert len(set(paths)) == len(paths)


def test_the_page_on_screen_and_the_button_next_to_it_answer_for_each_other(
        session):
    """The list holds the page, the summary says which one, the button says if
    there is another.

    A list longer than what one click can draw is how the old panel came to have
    tabs nobody could reach: the window it opened held at most a page of panels,
    and the rows below it could not be drawn at all.
    """
    panel = panelFor(session, IDS_NAME, 2)
    tab = tabNamed(panel, LONG_ARRAY)

    assert tab.page == 0
    assert tab.quantities.count() == PAGE
    assert 'page 1 of 2 (100 on this page, 100 per page)' in tab.summary.text()
    assert tab.nextButton.isEnabled() is True
    headOfFirstPage = [tab.quantities.item(row).text() for row in range(3)]

    tab.page = 1
    tab.refresh()
    assert tab.quantities.count() == LONG_QUANTITIES - PAGE
    assert 'page 2 of 2 (11 on this page, 100 per page)' in tab.summary.text()
    assert tab.nextButton.isEnabled() is False
    # The rows on screen are the two halves of one list, in order: the head of
    # page 2 is the quantity right after the last row of page 1, which is what the
    # two spellings of `VizProfiles.py:169` and `:234` used to break.
    everything = [tab.labelFor(leaf)
                  for leaf in tab.group.following(panel.abscissa())]
    assert headOfFirstPage == everything[:3]
    assert [tab.quantities.item(row).text() for row in range(3)] \
        == everything[PAGE:PAGE + 3]


def test_the_next_page_opens_a_window_of_its_own(session, monkeypatch):
    """A second window, not a second half of the first.

    A Table Plot View asks the width of its grid **once for the whole table**, from
    how many panels it holds -- `QVizTablePlot.layoutTable`, the same reason the
    15-panel overlap of `test_65` happened at all. Panels arriving in a window that
    is already laid out would be placed on one width and then relayed on another, so
    the next page goes in a window of its own: two `TablePlotView:` keys, each with
    its own count, and the first window untouched.

    The page is lowered to 10 for this one test, in **both** modules that spell the
    constant -- the offer that cuts the pages and the page that names its size --
    because the shipped 100 is pinned at the list level by the two tests above, and
    drawing a hundred quantities of `constraints` occurrence 2 along the 17 344 time
    slices this case holds there costs **45 s**. The paging code is the same path.
    """
    monkeypatch.setattr(offerModule, 'PAGE', SMALL_PAGE)
    monkeypatch.setattr(panelModule, 'PAGE', SMALL_PAGE)
    panel = panelFor(session, IDS_NAME, 0)
    tab = tabNamed(panel, LONG_ARRAY)

    assert len(tab.group.following(panel.abscissa())) \
        == SAME_ARRAY_AT_OCCURRENCE_0
    assert [len(page) for page in tab.pages()] \
        == [SMALL_PAGE] * (SAME_ARRAY_AT_OCCURRENCE_0 // SMALL_PAGE)

    before = set(session.api.figureframes)
    first = tab.drawPage()
    second = tab.addNextPage()
    session.qapp.processEvents()

    assert first is not None and second is not None
    assert first.figureKey != second.figureKey
    assert sorted(set(session.api.figureframes) - before) == \
        [first.figureKey, second.figureKey]
    assert first.panelCount() > 0 and second.panelCount() > 0
    assert tab.page == 1
    assert second.getPlotAxis() == 'TIME'


# --------------------------------------------------------------------------
# What a page refuses, and where that is said
# --------------------------------------------------------------------------

def test_a_page_that_cannot_be_read_is_refused_and_leaves_no_window(session,
                                                                   caplog):
    """22 quantities, 0 panels, and no empty window left on the screen.

    `wall` occurrence 0 answers 22 quantities outside any array of structures and
    every one of them is empty in this case. The command behind the click raises
    with its reason, the panel puts it in the log **of the case**, and the figure
    the command had started is deleted again -- which is what `QVizPlotAsTable`
    does, and what the panel does not undo.
    """
    panel = panelFor(session, 'wall', 0)
    tab = tabNamed(panel, 'no array of structures')
    before = set(session.api.figureframes)

    with caplog.at_level(logging.ERROR, logger=session.view.uri):
        frame = tab.drawPage()
    session.qapp.processEvents()

    assert frame is None
    assert set(session.api.figureframes) == before, \
        'a window nobody can draw is left in figureframes'
    assert 'Nothing to plot' in caplog.text


def test_an_occurrence_the_case_does_not_hold_refuses_the_entry_by_name(session,
                                                                       caplog):
    """The entry answers the case, not the data dictionary.

    `wall` holds one occurrence here. A session file naming another one is refused
    with the list the case answers, and that sentence is what `test_69` reads to
    know the window was lost and why.
    """
    from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog
    catalog = QVizPluginCatalog(session.view)
    entry = [one for one in catalog.entriesFor(session.view.IDSRoots['wall'])
             if one.pluginName == 'VizProfiles_plugin'][0]

    with caplog.at_level(logging.ERROR, logger=session.view.uri):
        catalog.run(entry, answers=QVizPluginAnswers(occurrence=7,
                                                     figureKey='PlotView:9'))
    assert 'the opened case holds no occurrence 7 of the wall IDS' in caplog.text
    assert 'it answers 0' in caplog.text


# --------------------------------------------------------------------------
# The two choices at the top of the window
# --------------------------------------------------------------------------

def test_the_occurrence_combo_is_bounded_by_the_case_and_reloads(session):
    """Choosing another occurrence loads it and asks the tree again.

    Measured: `magnetics` answers occurrences [0, 1] of this case and the combo
    answers exactly that; the tab bar of the other occurrence is not the same one
    (the quantities it holds differ), and the load is asked synchronously because
    the tabs are built on the tree that load produces.
    """
    panel = panelFor(session, 'magnetics', 0)
    box = panel.occurrenceBox
    assert [box.itemData(index) for index in range(box.count())] == [0, 1]

    box.setCurrentIndex(1)
    session.qapp.processEvents()

    assert panel.occurrence == 1
    assert 'magnetics occurrence 1' in panel.explains.text()
    assert box.currentData() == 1


def test_the_absissa_choice_reshapes_the_tabs_it_is_asked_of(session):
    """Four rows along the clock, ten along each quantity's own axis.

    `magnetics` is written at `homogeneous_time = 1`, so its arrays have an index to
    run along rather than a time base: the same tab answers 4 quantities under one
    reading and 10 under the other. The tabs are refreshed, not rebuilt, because the
    offer is a fact about the tree and the abscissa is a choice -- and the sentence
    on the tab changes with it, so the count on screen always names the reading it
    was counted under.
    """
    panel = panelFor(session, 'magnetics', 0)
    tab = tabNamed(panel, 'bpol_probe')
    assert tab.quantities.count() == 4
    assert 'along time' in tab.summary.text()

    panel.abscissaBox.setCurrentIndex(1)
    session.qapp.processEvents()

    assert panel.abscissa() == OWN_AXIS
    assert tab.quantities.count() == 10
    assert 'along its own axis' in tab.summary.text()


def test_a_tab_that_shows_fewer_rows_names_the_rows_it_leaves_out(session):
    """Twenty-one quantities, three rows, and the other eighteen by name.

    `time_slice/coordinate_system` is the tab where both readings answer the same
    three rows: the 18 others (`volume_element`, `r`, `z`, the Jacobian, the two
    metric tensors and friends) have **two** axes of their own, so a panel has
    nothing to draw them against -- they are pictures, and *Draw the selected
    quantity* opens them as one. A count that drops rows without naming them is how
    a tab reads as a bug in the panel.
    """
    panel = panelFor(session, IDS_NAME, 0)
    tab = tabNamed(panel, 'time_slice/coordinate_system')

    assert len(tab.group.following(panel.abscissa())) == 3
    assert len(tab.group.leftOut(panel.abscissa())) == 18
    assert tab.quantities.count() == 3
    assert '18 cannot be read along' in tab.summary.text()
    assert 'volume_element' in tab.summary.text()

    panel.abscissaBox.setCurrentIndex(1)
    session.qapp.processEvents()

    assert panel.abscissa() == OWN_AXIS
    assert tab.quantities.count() == 3, \
        'a quantity of two axes of its own is not made readable by the reading'
    assert '18 cannot be read along' in tab.summary.text()


# --------------------------------------------------------------------------
# The folded cursor at the bottom
# --------------------------------------------------------------------------

def test_the_cursor_band_offers_only_a_base_an_open_window_pins(session):
    """A slider whose number nothing came from is worse than no slider.

    Measured: `equilibrium` answers one time base (`time_slice`, 49 slices at
    occurrence 0) and `magnetics` none -- it is written at `homogeneous_time = 1`.
    And a panel whose curve runs **along** the clock has no row for that base, so
    the band stays empty over a window drawn along time, even for `equilibrium`.
    """
    curves = panelFor(session, IDS_NAME, 0)
    assert [base.key() for base in curves.offer().timeBases()] == \
        [('AOS', IDS_NAME, 'time_slice')]
    assert [base.length for base in curves.offer().timeBases()] == [49]
    assert panelFor(session, 'magnetics', 0).offer().timeBases() == []

    tab = tabNamed(curves, 'time_slice/profiles_1d')
    drawn = tab.drawPage()
    assert drawn is not None and drawn.getPlotAxis() == 'TIME'
    assert curves.cursors.keys() == [], \
        'a window read along the clock pins no time row to move'


def test_a_cursor_moves_the_panels_that_answer_it(session):
    """The band drives the windows this panel opened, through their own rows.

    Measured: the same `profiles_1d` page read along each quantity's own axis
    answers a `('AOS', 'equilibrium', 'time_slice')` row per panel, the band offers
    it, and moving it to slice 7 changes the first point of a profile from
    -7,974793 to -5,175139 -- the panel re-reads itself through the control it
    already carries, so the index lives in one place.
    """
    panel = panelFor(session, IDS_NAME, 0)
    panel.abscissaBox.setCurrentIndex(1)
    session.qapp.processEvents()
    tab = tabNamed(panel, 'time_slice/profiles_1d')
    frame = tab.drawPage()
    assert frame is not None

    base = ('AOS', IDS_NAME, 'time_slice')
    assert panel.cursors.keys() == [base]
    panelOfTable = frame.panels()[0]
    started = list(panelOfTable.curves()[0].getData()[1])[0]

    panel.cursors.setIndex(base, 7)
    session.qapp.processEvents()

    moved = list(panelOfTable.curves()[0].getData()[1])[0]
    assert moved != started, 'the cursor moved nothing'
    # The row that moved belongs to the panel, not to the band: the band only
    # repeats what the panels answer, so a window with no row for this axis (the
    # one drawn along the clock in the test above) is never touched.
    assert panel.cursors.indices() == {base: 7}
    assert panelOfTable.sliceControls.indices() == {base: 7}
