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
from imasviz.VizUtils import QVizPreferences


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
    """The list is the flat read, one row per case, URI on it as data and tip.

    The defaults of the two protocol boxes are asked of the preferences class,
    and a test that runs after one that left the state switched (HDF5 off, MDS+
    on) would see a list that is not the flat read. This test is the flat read
    -- both protocols on -- so it asks the defaults explicitly, the same way a
    fresh installation would answer them.
    """
    _setPrefs(monkeypatch, Uri_list_filter_HDF5=1, Uri_list_filter_MDSplus=1)
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


# The sort: the field the list is laid out by, and its sense.
# The filter: which of the two protocols the list shows.
# The refusal: an empty list is not what the two boxes are for.
# And the round trip: the choice a hand makes is a line in the file.


def _setPrefs(monkeypatch, **options):
    """Set the four Uri_list_* class attributes via monkeypatch (auto-restores).

    The reader (`build`) is a no-op on subsequent calls (it is gated by
    ``userPreferencesInitialized``); a test that wants a different state asks
    the class directly, and this is the one place to do that so the state is
    restored when the test is over.
    """
    for name, value in options.items():
        monkeypatch.setattr(QVizPreferences, name, value)


def test_shot_sorts_by_the_number_not_the_word(imasdb, qapp, monkeypatch):
    """The sort on `shot` reads it as a number.

    The numeric order is 999, 1234, 7777, 54924, 54924. The word order (the
    old behaviour) is 1234, 54924, 54924, 7777, 999 -- the same set, a
    different order. This test is what tells the two apart: the first row is
    a 999 in one order and a 1234 in the other.
    """
    monkeypatch.setattr('imasviz.VizGUI.VizWidgets.QVizCaseSelector.caseRootForUser',
                        lambda username: imasdb)
    _setPrefs(monkeypatch, Uri_list_sort_key='shot',
              Uri_list_sort_direction='asc',
              Uri_list_filter_HDF5=1, Uri_list_filter_MDSplus=1)
    sel = QVizCaseSelector()
    cases = sel.refresh(USER)
    assert [c['shot'] for c in cases] == ['999', '1234', '7777', '54924', '54924']
    assert sel.listView.count() == 5
    for i, case in enumerate(cases):
        assert sel.listView.item(i).data(Qt.UserRole) == \
            QVizCaseSelector.uriOf(USER, case)


def test_unchecking_MDSplus_keeps_only_the_HDF5_rows(imasdb, qapp, monkeypatch):
    """Turning MDS+ off at the box shows the three HDF5 cases and no MDS+.

    The list is *which kind of case to open*, and the box is the kind. A
    change at the box re-shapes the list, and the list shows the change.
    """
    monkeypatch.setattr('imasviz.VizGUI.VizWidgets.QVizCaseSelector.caseRootForUser',
                        lambda username: imasdb)
    _setPrefs(monkeypatch, Uri_list_filter_HDF5=1, Uri_list_filter_MDSplus=1)
    sel = QVizCaseSelector()
    sel.refresh(USER)
    assert sel.listView.count() == 5
    sel.filterMDS.setChecked(False)
    assert sel.listView.count() == 3
    backends = set()
    for i in range(sel.listView.count()):
        backends.add(sel.listView.item(i).text().split(' \u00b7 ')[0])
    assert backends == {'HDF5'}
    assert QVizPreferences.Uri_list_filter_HDF5 == 1
    assert QVizPreferences.Uri_list_filter_MDSplus == 0


def test_unchecking_the_last_protocol_is_refused(imasdb, qapp, monkeypatch, caplog):
    """Refused by name, and the box the user just turned off stays on.

    The list is not a place to look at that shows nothing, so the two boxes
    have one rule between them: at least one stays checked, and the one the
    user just turned off is the one that stays. The user is told by the name
    of the protocol the box tried to hide.
    """
    monkeypatch.setattr('imasviz.VizGUI.VizWidgets.QVizCaseSelector.caseRootForUser',
                        lambda username: imasdb)
    _setPrefs(monkeypatch, Uri_list_filter_HDF5=1, Uri_list_filter_MDSplus=1)
    sel = QVizCaseSelector()
    sel.refresh(USER)
    # The first uncheck is allowed: it leaves the other on.
    sel.filterHDF5.setChecked(False)
    assert sel.filterHDF5.isChecked() is False
    assert sel.filterMDS.isChecked() is True
    assert sel.listView.count() == 2           # only the two MDS+ remain
    # The second uncheck is the last one: refused, and the name is logged.
    with caplog.at_level(logging.WARNING, logger='logPanel'):
        sel.filterMDS.setChecked(False)
    assert sel.filterMDS.isChecked() is True   # the refusal re-checked it
    assert 'MDS+' in caplog.text
    assert 'restait masqu' in caplog.text      # the refusal names the rule
    # The list still shows the MDS+ cases, because the box the user tried to
    # turn off is the one that stays.
    assert sel.listView.count() == 2


def test_the_sort_direction_button_reverses_the_list(imasdb, qapp, monkeypatch):
    """The arrow beside the *Trier par* box: a click turns the list.

    With the sort on `shot`, the first row is a 999 (ascending) and a 7777
    (descending). A hand on the button is a hand on the order, and the list
    answers.
    """
    monkeypatch.setattr('imasviz.VizGUI.VizWidgets.QVizCaseSelector.caseRootForUser',
                        lambda username: imasdb)
    _setPrefs(monkeypatch, Uri_list_sort_key='shot',
              Uri_list_sort_direction='asc',
              Uri_list_filter_HDF5=1, Uri_list_filter_MDSplus=1)
    sel = QVizCaseSelector()
    sel.refresh(USER)
    firstAsc = sel.listView.item(0).data(Qt.UserRole)
    assert '999' in firstAsc
    sel.sortDirButton.click()
    firstDesc = sel.listView.item(0).data(Qt.UserRole)
    assert '54924' in firstDesc
    assert firstAsc != firstDesc
    assert QVizPreferences.Uri_list_sort_direction == 'desc'


def test_persist_writes_and_the_reader_reads_the_choice(tmp_path, monkeypatch):
    """The round trip a test that does not open a display still checks.

    A hand at the selector writes a line to the file, and the reader reads it
    back the next time it is asked. The file is the place the two halves of
    a session meet, so a test that only builds the widget and toggles a box
    sees the state in the file, not in a variable that dies with the process.
    """
    monkeypatch.setenv('HOME', str(tmp_path))
    # Save the state, because the test's choice would leak into the others.
    save_key = QVizPreferences.Uri_list_sort_key
    save_dir = QVizPreferences.Uri_list_sort_direction
    save_fh = QVizPreferences.Uri_list_filter_HDF5
    save_fm = QVizPreferences.Uri_list_filter_MDSplus
    save_init = QVizPreferences.userPreferencesInitialized
    try:
        QVizPreferences.Uri_list_sort_key = 'shot'
        QVizPreferences.Uri_list_sort_direction = 'desc'
        QVizPreferences.Uri_list_filter_HDF5 = 0
        QVizPreferences.Uri_list_filter_MDSplus = 1
        QVizPreferences.persist(
            Uri_list_sort_key='shot',
            Uri_list_sort_direction='desc',
            Uri_list_filter_HDF5=0,
            Uri_list_filter_MDSplus=1)
        path = tmp_path / '.imasviz' / 'preferences'
        assert path.exists()
        content = path.read_text()
        assert 'Uri_list_sort_key=shot' in content
        assert 'Uri_list_sort_direction=desc' in content
        assert 'Uri_list_filter_HDF5=0' in content
        assert 'Uri_list_filter_MDSplus=1' in content
        # Now reset the in-memory state and ask the reader for the file again.
        QVizPreferences.Uri_list_sort_key = 'database'
        QVizPreferences.Uri_list_sort_direction = 'asc'
        QVizPreferences.Uri_list_filter_HDF5 = 1
        QVizPreferences.Uri_list_filter_MDSplus = 1
        QVizPreferences.userPreferencesInitialized = False
        QVizPreferences().build()
        assert QVizPreferences.Uri_list_sort_key == 'shot'
        assert QVizPreferences.Uri_list_sort_direction == 'desc'
        assert QVizPreferences.Uri_list_filter_HDF5 == 0
        assert QVizPreferences.Uri_list_filter_MDSplus == 1
    finally:
        QVizPreferences.Uri_list_sort_key = save_key
        QVizPreferences.Uri_list_sort_direction = save_dir
        QVizPreferences.Uri_list_filter_HDF5 = save_fh
        QVizPreferences.Uri_list_filter_MDSplus = save_fm
        QVizPreferences.userPreferencesInitialized = save_init


def test_bad_values_in_the_preferences_file_are_refused(tmp_path, monkeypatch):
    """The reader refuses a word it does not sort on, and a sense it does not
    turn, and keeps the state the class was holding.

    These are the two new lines the file can hold, and the two that have a
    refusal to give. The other two of the file (the two protocol boxes) are
    0 or 1, and a word is refused by the same rule `build` has always applied
    to the other switches in the file, so one bad line costs its own option
    and nothing else changes.
    """
    monkeypatch.setenv('HOME', str(tmp_path))
    save_key = QVizPreferences.Uri_list_sort_key
    save_dir = QVizPreferences.Uri_list_sort_direction
    save_fh = QVizPreferences.Uri_list_filter_HDF5
    save_fm = QVizPreferences.Uri_list_filter_MDSplus
    save_init = QVizPreferences.userPreferencesInitialized
    try:
        # A file that names a key the box does not offer, and a sense it does
        # not turn: both are refused, and the state is left where it was.
        (tmp_path / '.imasviz').mkdir(parents=True, exist_ok=True)
        (tmp_path / '.imasviz' / 'preferences').write_text(
            'Uri_list_sort_key=alphabetical\n'
            'Uri_list_sort_direction=uphill\n')
        QVizPreferences.Uri_list_sort_key = 'database'
        QVizPreferences.Uri_list_sort_direction = 'asc'
        QVizPreferences.Uri_list_filter_HDF5 = 1
        QVizPreferences.Uri_list_filter_MDSplus = 1
        QVizPreferences.userPreferencesInitialized = False
        QVizPreferences().build()
        # Both lines refused; the state is left exactly where it was.
        assert QVizPreferences.Uri_list_sort_key == 'database'
        assert QVizPreferences.Uri_list_sort_direction == 'asc'
        assert QVizPreferences.Uri_list_filter_HDF5 == 1
        assert QVizPreferences.Uri_list_filter_MDSplus == 1
        # And a file that names a word the box offers is read, because the
        # refusal is the name of the word that is refused, not the box itself.
        (tmp_path / '.imasviz' / 'preferences').write_text(
            'Uri_list_sort_key=shot\n'
            'Uri_list_sort_direction=desc\n')
        QVizPreferences.userPreferencesInitialized = False
        QVizPreferences().build()
        assert QVizPreferences.Uri_list_sort_key == 'shot'
        assert QVizPreferences.Uri_list_sort_direction == 'desc'
    finally:
        QVizPreferences.Uri_list_sort_key = save_key
        QVizPreferences.Uri_list_sort_direction = save_dir
        QVizPreferences.Uri_list_filter_HDF5 = save_fh
        QVizPreferences.Uri_list_filter_MDSplus = save_fm
        QVizPreferences.userPreferencesInitialized = save_init


def test_the_controls_are_synced_from_the_preferences_at_init(qapp, monkeypatch):
    """A widget that is built after a choice is made in a previous session
    sees that choice in its controls, and not the defaults of the class.

    The state a hand left in the file is the state a new session starts in,
    and the controls are the place the user sees that state: the box is at
    the key, the arrow is at its sense, the two checkboxes at the two
    protocols.
    """
    # Set the state, and pretend the file was just read with that state.
    _setPrefs(monkeypatch, Uri_list_sort_key='run',
              Uri_list_sort_direction='desc',
              Uri_list_filter_HDF5=0, Uri_list_filter_MDSplus=1)
    sel = QVizCaseSelector()
    # The box's currentData is the file name the box carries for its label,
    # and the label the UI spells.
    assert sel.sortKeyBox.currentData() == 'run'
    assert sel.sortKeyBox.currentText() == 'Run'
    assert sel.sortDirButton.isChecked() is True
    assert sel.filterHDF5.isChecked() is False
    assert sel.filterMDS.isChecked() is True
