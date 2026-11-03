# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The start window's case selector: a list of local cases, each a URI.

The selection of a case used to be a five-level tree of the local imasdb that
answered five derived parameters behind a URI nobody saw. The professional
selection is the URI: a flat list of the local cases, each row a readable label
and -- stored as data and spelled as its tooltip -- the very URI the Access
Layer opens the case with. These tests pin that a case that is a case on disk
is a row in the list and a selection that names nothing is refused, not opened
on an empty choice.
"""

import logging
import os

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from imasviz.VizGUI.VizWidgets.QVizCaseSelector import QVizCaseSelector
from imasviz.VizGUI.VizWidgets.QVizIMASdbBrowserWidget import (
    caseRootForUser, localCases)
from imasviz.VizDataSource.QVizIMASDataSource import caseUri, hdf5PathUri


USER = 'g2lfleur'


@pytest.fixture()
def imasdb(tmp_path):
    """A local imasdb holding two HDF5 databases' cases and one MDS+ case set.

    Two runs of one west shot, one run of a second west shot, and two MDS+
    pulses of equinox -- one bookkeeping file that must not be read as a case.
    """
    root = tmp_path / 'imasdb'

    def make(*parts, file=None):
        folder = root.joinpath(*parts)
        folder.mkdir(parents=True, exist_ok=True)
        if file is not None:
            (folder / file).write_text('')

    make('west', '3', '54924', '0', file='equilibrium.h5')
    make('west', '3', '54924', '2', file='core.h5')
    make('west', '3', '999', '0', file='magnet.h5')
    make('equinox', '3', '0', file='bar_77770001.datafile')
    make('equinox', '3', '1', file='foo_12345678.datafile')
    make('equinox', '3', '0', file='ids_model.datafile')
    return str(root)


# What the scanner and the URI spelling answer.

def test_the_scan_finds_every_local_case_as_a_uri(imasdb):
    """A case that is a case on disk is a case in the list -- and no more.

    The bookkeeping `ids_model.datafile` and the two MDS+ names are read; the
    three `*.h5` run folders are found with their path; and nothing else is
    invented. This is the reading a user will click and the reader will then
    open, so what it lists is what it will be opened with.
    """
    cases = localCases(imasdb)
    assert len(cases) == 5

    by = {(c['database'], c['shot'], c['run'], c['backend']) for c in cases}
    assert by == {
        ('west', '54924', '0', 'HDF5'),
        ('west', '54924', '2', 'HDF5'),
        ('west', '999', '0', 'HDF5'),
        ('equinox', '1234', '15678', 'MDS+'),
        ('equinox', '7777', '0001', 'MDS+'),
    }


def test_the_hdf5_case_carries_its_path_uri(imasdb):
    east = [c for c in localCases(imasdb) if c['database'] == 'west']
    for case in east:
        assert case['path'].endswith('/west/3/%s/%s' % (case['shot'], case['run']))
    assert all(c['backend'] == 'HDF5' for c in east)


def test_the_mdsplus_case_carries_no_path_and_is_read_from_its_name(imasdb):
    """The MDS+ row is shot and run, read from the .datafile name; no path.

    The run number is the digit folder's leading character followed by the last
    four digits of the name's last word (`1` + `5678` = `15678`), and the book-
    keeping file that spells no case contributed nothing to the list.
    """
    west = [c for c in localCases(imasdb) if c['database'] == 'equinox']
    assert {c['run'] for c in west} == {'15678', '0001'}
    assert all(c['path'] is None for c in west)
    assert all(c['backend'] == 'MDS+' for c in west)


def test_an_empty_imasdb_answers_no_case(imasdb):
    # A root that holds no database is not a case, and answers [] -- an empty
    # list the list can draw, and the log can name if the user expects more.
    empty = os.path.join(imasdb, 'no-such-db')
    assert localCases(empty) == []


def test_an_unset_home_answers_no_root(monkeypatch):
    """No HOME and no IMAS_HOME is a refusal, not a NameError mid-walk."""
    monkeypatch.delenv('HOME', raising=False)
    monkeypatch.delenv('IMAS_HOME', raising=False)
    assert caseRootForUser(USER) is None
    assert caseRootForUser('public') is None


def test_the_named_user_root_is_under_public(imasdb, monkeypatch):
    """A named user's cases live under their home's public/imasdb."""
    monkeypatch.setenv('HOME', '/abs/home')
    assert caseRootForUser(USER) == '/abs/%s/public/imasdb' % USER


def test_the_public_root_is_under_shared_imasdb(monkeypatch):
    """'public' is not a user and lives under IMAS_HOME/shared/imasdb."""
    monkeypatch.setenv('IMAS_HOME', '/abs/imas')
    assert caseRootForUser('public') == '/abs/imas/shared/imasdb'


def test_a_local_case_is_opened_with_the_uri_the_access_layer_takes():
    """HDF5 opens on its path; MDS+ on the parameter set the stack spells."""
    assert hdf5PathUri('/x/west/3/54924/0') == 'imas:hdf5?path=/x/west/3/54924/0'
    assert QVizCaseSelector.uriOf(
        USER, {'backend': 'HDF5', 'database': 'west', 'shot': '54924',
               'run': '0', 'path': '/x/west/3/54924/0'}) \
        == 'imas:hdf5?path=/x/west/3/54924/0'
    assert QVizCaseSelector.uriOf(
        USER, {'backend': 'MDS+', 'database': 'equinox', 'shot': '1234',
               'run': '15678', 'path': None}) \
        == caseUri(12, USER, 'equinox', '1234', '15678', '3', '')


# The widget itself: the list, and the gestures that open and copy it.

def test_refresh_lays_every_case_as_a_row_with_its_uri(imasdb, qapp, monkeypatch):
    """The list is the flat read, one row per case, URI on it as data and tip."""
    monkeypatch.setattr('imasviz.VizGUI.VizWidgets.QVizCaseSelector.caseRootForUser',
                        lambda username: imasdb)
    sel = QVizCaseSelector()
    cases = sel.refresh(USER)
    assert len(cases) == 5
    assert sel.listView.count() == 5
    for i in range(sel.listView.count()):
        item = sel.listView.item(i)
        case = cases[i]
        uri = QVizCaseSelector.uriOf(USER, case)
        assert item.text() == QVizCaseSelector.labelOf(case)
        assert item.data(Qt.UserRole) == uri
        assert item.toolTip() == uri


def test_the_selected_row_opens_its_uri(imasdb, qapp, monkeypatch, qtbot):
    """The *Ouvrir* button -- and a double click -- open the selected row's URI."""
    monkeypatch.setattr('imasviz.VizGUI.VizWidgets.QVizCaseSelector.caseRootForUser',
                        lambda username: imasdb)
    sel = QVizCaseSelector()
    sel.refresh(USER)
    emitted = []
    sel.uriOpened.connect(lambda u: emitted.append(u))

    sel.listView.setCurrentRow(1)
    sel.openCurrent()
    first = sel.listView.item(1).data(Qt.UserRole)
    assert emitted == [first]

    sel.openRow(sel.listView.item(0))
    assert emitted == [first, sel.listView.item(0).data(Qt.UserRole)]


def test_a_pasted_uri_opens_as_typed(qapp, qtbot):
    """The free line is a URI and opens as typed -- UDA, remote, or local."""
    sel = QVizCaseSelector()
    emitted = []
    sel.uriOpened.connect(lambda u: emitted.append(u))
    sel.freeText.setText('imas:uda?user=g2lfleur;database=JT60SA;shot=957;run=0')
    sel.openFree()
    assert emitted == ['imas:uda?user=g2lfleur;database=JT60SA;shot=957;run=0']


def test_nothing_selected_is_refused_and_costs_no_open(qapp, qtbot, caplog):
    """An empty choice is a refusal in the log, not a case opened on the empty."""
    sel = QVizCaseSelector()
    emitted = []
    sel.uriOpened.connect(lambda u: emitted.append(u))
    with caplog.at_level(logging.ERROR, logger='logPanel'):
        sel.openCurrent()
    assert emitted == []
    assert 'Aucune' in caplog.text


def test_copy_puts_the_selected_uri_on_the_clipboard(imasdb, qapp, monkeypatch):
    """The one affordance that makes a case portable: copy it as its URI."""
    monkeypatch.setattr('imasviz.VizGUI.VizWidgets.QVizCaseSelector.caseRootForUser',
                        lambda username: imasdb)
    sel = QVizCaseSelector()
    sel.refresh(USER)
    sel.listView.setCurrentRow(0)

    captured = {}

    class Clipboard:
        def setText(self, text):
            captured['text'] = text

    monkeypatch.setattr(QApplication, 'clipboard',
                        staticmethod(lambda: Clipboard()))
    sel.copyUri()
    assert captured['text'] == sel.listView.item(0).data(Qt.UserRole)


def test_the_frame_opens_what_the_selector_hands_over(qapp):
    """The frame's Open is the one every URI-first gesture lands on."""
    from imasviz.VizGUI.QtVIZ_GUI import GUIFrame

    class OpenShotView:
        def __init__(self):
            self.opened = []

        def Open(self, evt, uri):
            self.opened.append((evt, uri))

    class Controller:
        def __init__(self):
            self.openShotView = OpenShotView()

    class StandIn:
        def __init__(self):
            self.mainMenuController = Controller()

    window = StandIn()
    GUIFrame.openUri(window, 'imas:hdf5?path=/x/west/3/54924/0')
    assert window.mainMenuController.openShotView.opened == \
        [(None, 'imas:hdf5?path=/x/west/3/54924/0')]


def test_the_frame_refuses_an_empty_uri(qapp, caplog):
    """An empty selection is refused, with the gesture left unspent."""
    from imasviz.VizGUI.QtVIZ_GUI import GUIFrame

    class OpenShotView:
        def Open(self, evt, uri):
            raise AssertionError('the empty URI must not reach the Open')

    class Controller:
        def __init__(self):
            self.openShotView = OpenShotView()

    class StandIn:
        def __init__(self):
            self.mainMenuController = Controller()

    window = StandIn()
    with caplog.at_level(logging.ERROR, logger='logPanel'):
        GUIFrame.openUri(window, '   ')
        GUIFrame.openUri(window, None)
    assert 'No URI' in caplog.text
