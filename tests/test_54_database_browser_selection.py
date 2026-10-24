# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Double clicking the IMAS database browser: what one selection has to answer.

The report was a traceback printed on the console, outside every refusal the
application logs, from a double click in the browser of the start window:

    File ".../QtVIZ_GUI.py", line 199, in updateIDSparam
        self.backend = self.IMASdbBrowserWidget.getActiveBackend()
    AttributeError: 'QVizIMASdbBrowserWidget' object has no attribute 'backend'

Measured offscreen, with no IMAS and no case in it, on a tree of the five levels
the browser's own `Worker` builds (user, backend, database, shot, run):

* the constructor set `activeUsername`, `activeDatabase`, `activeShot` and
  `activeRun` — and never the backend, which only ever appeared inside
  `setActiveBackend`, under another name. A browser nobody had clicked yet
  answered AttributeError on `getActiveBackend()`, and that is the **first**
  thing `updateIDSparam` asks of it;
* `doubleClickHandler` set its five values **only** for a run leaf, but emitted
  `onItemDoubleClick` **whatever** had been clicked. A double click on a shot, a
  database or a backend row therefore ran the frame's update with three None
  values and no backend at all — measured on all three rows;
* those values were written as they were read, and on PySide6 6.6.3
  `QLineEdit.setText(None)` answers no error and leaves the field empty (it was
  measured here, because the traceback reaching line 199 shows the four earlier
  lines went through). So the parameters the user had typed disappeared, one by
  one, before the fifth line died;
* `setActiveBackend` mapped the two labels with two tests and no `else`, so
  `'hdf5'` — the labels are case sensitive — and `'ITER'` both answered
  `UnboundLocalError: cannot access local variable 'backend'`.

The manual (`manual/loading_IDS.rst:56`) promises the browser fills the
parameters when a case is double clicked. That is what these tests pin: the five
values arrive together or not at all, and a click that spells no case says so in
the log of the session instead of taking the gesture down.
"""

import logging

import pytest
from PySide6.QtWidgets import (QComboBox, QLineEdit, QMainWindow,
                               QTreeWidgetItem)

from support import ownership

from imasviz.VizGUI.VizWidgets.QVizIMASdbBrowserWidget import (
    QVizIMASdbBrowserWidget, BACKENDS)


USER = 'g2lfleur'
DATABASE = 'west'
SHOT = '54924'
RUN = '0'


@pytest.fixture()
def browser(qapp, tmp_path, monkeypatch):
    """A browser of the application's own class, with an empty home.

    Its constructor populates itself for the logged-in user, walking
    ``$HOME/../<user>/public/imasdb`` in a thread of its own and showing a
    progress bar while it does. ``HOME`` is redirected so that walk finds
    nothing and returns: what these tests care about is the selection, and the
    tree is built by hand exactly the way the ``Worker`` spells it.

    The window handed to the constructor is owned here on purpose: Shiboken
    does not keep a parent's wrapper alive from its child, so a parent built
    inline dies with the fixture and Qt deletes the browser with it -- measured,
    every test below then answers ``RuntimeError: Internal C++ object
    (QVizIMASdbBrowserWidget) already deleted``.
    """
    monkeypatch.setenv('HOME', str(tmp_path))
    window = QMainWindow()
    ownership.keep(window)
    view = QVizIMASdbBrowserWidget(window)
    qapp.processEvents()
    return view


def aCaseIn(browser, backendLabel='HDF5'):
    """The five levels the Worker builds; returns the rows bottom-up."""
    user = QTreeWidgetItem(browser)
    user.setText(0, USER)
    backend = QTreeWidgetItem(user)
    backend.setText(0, backendLabel)
    database = QTreeWidgetItem(backend)
    database.setText(0, DATABASE)
    shot = QTreeWidgetItem(database)
    shot.setText(0, SHOT)
    run = QTreeWidgetItem(shot)
    run.setText(0, RUN)
    return [run, shot, database, backend, user]


def emittedBy(browser):
    """A list the signal appends to, so an emission can be counted."""
    emissions = []
    browser.onItemDoubleClick.connect(lambda: emissions.append(1))
    return emissions


def selected(browser):
    return (browser.getActiveUsername(), browser.getActiveBackend(),
            browser.getActiveDatabase(), browser.getActiveShot(),
            browser.getActiveRun())


class StartWindow:
    """The five widgets ``GUIFrame.updateIDSparam`` writes, and nothing else.

    Building the real ``GUIFrame`` would build the whole start window — menus,
    MDI area, the browser populating itself — to reach one method that reads
    five getters and writes five widgets. What the method needs of its owner is
    spelled here.
    """

    def __init__(self, browser):
        self.userName = QLineEdit('typed by hand')
        self.imasDbName = QLineEdit('typed by hand')
        self.shotNumber = QLineEdit('typed by hand')
        self.runNumber = QLineEdit('typed by hand')
        self.backend = 13
        self.backendCombo = QComboBox()
        self.backendCombo.addItems(['HDF5', 'MDS+'])
        self.IMASdbBrowserWidget = browser

    def texts(self):
        return (self.userName.text(), self.imasDbName.text(),
                self.shotNumber.text(), self.runNumber.text())


@pytest.mark.ui
def test_a_browser_that_has_not_been_clicked_answers_five_values(browser):
    # The AttributeError of the report: the fifth value used not to exist until
    # a run row had been double clicked.
    assert selected(browser) == (USER, None, None, None, None)


@pytest.mark.ui
def test_a_run_leaf_spells_the_whole_case(browser, qtbot):
    rows = aCaseIn(browser)
    emissions = emittedBy(browser)
    browser.doubleClickHandler(rows[0], 0)
    assert selected(browser) == (USER, 13, DATABASE, SHOT, RUN)
    assert len(emissions) == 1


@pytest.mark.ui
def test_the_other_backend_label_is_the_other_id(browser, qtbot):
    rows = aCaseIn(browser, 'MDS+')
    browser.doubleClickHandler(rows[0], 0)
    assert browser.getActiveBackend() == 12


@pytest.mark.ui
@pytest.mark.parametrize('row', [1, 2, 3, 4],
                         ids=['shot', 'database', 'backend', 'user'])
def test_a_row_that_is_not_a_run_selects_nothing_and_says_why(browser, qtbot,
                                                              caplog, row):
    rows = aCaseIn(browser)
    emissions = emittedBy(browser)
    with caplog.at_level(logging.INFO, logger='logPanel'):
        browser.doubleClickHandler(rows[row], 0)
    # Nothing was emitted, so the frame was never asked to refill its fields;
    # and the reason is in the log of the session, not on the console.
    assert emissions == []
    assert selected(browser) == (USER, None, None, None, None)
    assert "selects no case" in caplog.text
    assert rows[row].text(0) in caplog.text


@pytest.mark.ui
def test_a_tree_shallower_than_five_levels_selects_nothing(browser, caplog):
    # The handler used to walk exactly four parent() steps without looking.
    user = QTreeWidgetItem(browser)
    user.setText(0, USER)
    database = QTreeWidgetItem(user)
    database.setText(0, DATABASE)
    shot = QTreeWidgetItem(database)
    shot.setText(0, SHOT)
    emissions = emittedBy(browser)
    with caplog.at_level(logging.INFO, logger='logPanel'):
        browser.doubleClickHandler(shot, 0)
    assert emissions == []
    assert "selects no case" in caplog.text


@pytest.mark.ui
def test_a_backend_label_nobody_knows_is_refused_by_name(browser, caplog):
    rows = aCaseIn(browser, 'hdf5')
    emissions = emittedBy(browser)
    with caplog.at_level(logging.ERROR, logger='logPanel'):
        browser.doubleClickHandler(rows[0], 0)
    assert emissions == []
    assert selected(browser) == (USER, None, None, None, None)
    assert "'hdf5'" in caplog.text
    assert 'HDF5' in caplog.text and 'MDS+' in caplog.text


@pytest.mark.ui
def test_a_backend_id_nobody_knows_is_refused_by_name(browser):
    with pytest.raises(ValueError, match='7'):
        browser.setActiveBackend(7)
    assert set(BACKENDS.values()) == {13, 12}


@pytest.mark.ui
def test_a_partial_selection_leaves_the_parameters_as_they_were(browser, caplog):
    from imasviz.VizGUI.QtVIZ_GUI import GUIFrame

    window = StartWindow(browser)
    aCaseIn(browser)
    with caplog.at_level(logging.ERROR, logger='logPanel'):
        GUIFrame.updateIDSparam(window)
    assert window.texts() == ('typed by hand',) * 4
    assert "did not select a database" in caplog.text


@pytest.mark.ui
def test_a_run_leaf_fills_the_five_parameters(browser):
    from imasviz.VizGUI.QtVIZ_GUI import GUIFrame

    window = StartWindow(browser)
    rows = aCaseIn(browser)
    browser.doubleClickHandler(rows[0], 0)
    GUIFrame.updateIDSparam(window)
    assert window.texts() == (USER, DATABASE, SHOT, RUN)
    assert window.backend == 13
    assert window.backendCombo.currentIndex() == 0

    rows = aCaseIn(browser, 'MDS+')
    browser.doubleClickHandler(rows[0], 0)
    GUIFrame.updateIDSparam(window)
    assert window.backend == 12
    assert window.backendCombo.currentIndex() == 1
