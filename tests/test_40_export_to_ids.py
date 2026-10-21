# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Export to IDS: what the gesture writes, and what it used to answer instead.

The manual promises that the IDSs currently opened in a shot view are written to
a case the user names, and shows a dialog of four fields. Measured on the code
this replaces, the gesture wrote **no IDS at all**, twice over:

* the first statement of the handler built the URI through a helper doing
  ``from imas import _al_lowlevel as ll``. IMAS-Python 2.3.0 has no such module:
  the click answered ``ImportError: cannot import name '_al_lowlevel'``, and
  that line sat **outside** the ``try``, so nothing was caught and nothing was
  written -- **0 files**. The same helper carries the command line's
  ``-u -d -s -r -b`` path.
* with the URI spelled by hand, the handler called ``open()`` on an entry it had
  just built from that URI. IMAS-Python opens such an entry at construction and
  answers ``RuntimeError: This DBEntry is already open``; the bare ``except:``
  turned that into one *info* line -- "Unable to create pulse file with URI:" --
  and returned. On disk: **one** file, a 1912-byte ``master.h5``, **0 IDSs**, no
  reason.
* an entry built without a data dictionary refuses every IDS: ``RuntimeError:
  Provided IDS uses DD 3.35.0 which has a different major version than the Data
  Entry (-1)``. Pinned at ``3.35.0``, the same two IDSs came out as
  ``master.h5`` 2000 bytes and ``pulse_schedule.h5`` 83662 bytes, and the case
  read back ``pulse_schedule`` at occurrence 0.

Two numbers are needed and the old code had one. The URI carries the **major**
of the data dictionary -- the real cases sit under ``west/3/54924/0`` -- while
the entry is built at the **full** version: ``dd_version='3'`` answers
``UnknownDDVersion: Data dictionary version '3' cannot be found``. And the old
code took its version from ``IMAS_MAJOR_VERSION``, the Access Layer's own number,
which on this stack measured ``5``: the bytes went to ``no_such_db/5/1/0/``, a
directory no reader of this application looks in.

The dialog is checked where the values are typed. Its text boxes used to be read
with ``int()`` inside the handler, so a shot of ``abc`` answered ``ValueError:
invalid literal for int() with base 10: 'abc'``; and it prefilled ``/`` for the
user and ``/`` for the database.
"""

import logging
import os
import sys

import pytest
from PySide6.QtGui import QValidator

from conftest import CASE_URI, CASE_DATA_DICTIONARY_VERSION, case_uri_or_skip

from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource, \
    _readCaseFromUri, caseUri
from imasviz.VizGUI.VizGUICommands.VizDataExport import QVizExportDialog, \
    QVizExportTarget, QVizExportToIDS, HDF5, MDSPLUS

exportModule = sys.modules[QVizExportToIDS.__module__]

USER_URI = ('imas:hdf5?user=g2lfleur;shot=54924;run=0;database=west;version=3')


# ---------------------------------------------------------------------------
# What the gesture stands on: a case named by four fields.

def test_a_case_uri_is_the_inverse_of_the_reader():
    """What the data layer spells, the same layer reads back.

    ``_readCaseFromUri`` is what opens a case; a URI built by the export that it
    cannot read is a case the user can write and never open again.
    """
    uri = caseUri(HDF5, 'g2lfleur', 'west', 54924, 0, '3')
    assert uri == USER_URI
    assert _readCaseFromUri(uri) == ('west', '54924', '0')


def test_the_other_backend_is_spelled_by_the_same_number():
    """The backend number the manual's dialog never showed, once asked as a choice."""
    assert caseUri(MDSPLUS, 'g2lfleur', 'west', 54924, 0, '3').startswith(
        'imas:mdsplus?')


def test_an_unknown_backend_has_no_uri():
    with pytest.raises(ValueError, match='HDF5'):
        caseUri(7, 'g2lfleur', 'west', 54924, 0, '3')


def test_a_uri_without_a_data_version_is_refused():
    """The version names a directory, so there is no sensible default for it."""
    with pytest.raises(ValueError, match='version'):
        caseUri(HDF5, 'g2lfleur', 'west', 54924, 0, '')


def test_extra_options_are_appended_once():
    uri = caseUri(HDF5, 'g2lfleur', 'west', 54924, 0, '3', options=';tag=x')
    assert uri.endswith(';version=3;tag=x')
    assert uri.count(';tag=x') == 1


# ---------------------------------------------------------------------------
# The four fields, checked before anything is asked of the Access Layer.

def _target(**kwargs):
    fields = dict(user='g2lfleur', database='west', shot=54924, run=0,
                  dataVersion='3.35.0')
    fields.update(kwargs)
    return QVizExportTarget(**fields)


def test_an_empty_field_is_named_in_the_reason():
    for field, message in (('user', 'user'), ('database', 'database')):
        with pytest.raises(ValueError) as error:
            _target(**{field: ''}).uri()
        assert message in str(error.value)


def test_a_separator_inside_a_field_is_refused():
    """A field holding the separator of the URI would spell two fields."""
    with pytest.raises(ValueError, match='separator'):
        _target(user='a/b').uri()
    with pytest.raises(ValueError, match='separator'):
        _target(database='a;b').uri()


def test_the_default_the_old_dialog_prefilled_is_refused():
    """The old dialog started with ``/`` for a user and ``/`` for a database.

    A URI naming a user literally called ``/`` is never what the user meant, and
    the Access Layer accepted it without a word: measured, it built
    ``no_such_db/5/1/0/`` and put the bytes there.
    """
    with pytest.raises(ValueError, match='separator'):
        _target(user='/', database='/').uri()


@pytest.mark.parametrize('shot', [None, 0, -1, '54924'])
def test_a_shot_number_has_to_be_a_positive_number(shot):
    """``int('abc')`` used to answer from the OK button; a text box of its own
    cannot hold letters in the first place, and a missing shot is said here."""
    with pytest.raises(ValueError, match='shot'):
        _target(shot=shot).uri()


@pytest.mark.parametrize('run', [None, -1, '0'])
def test_a_run_number_has_to_be_a_number(run):
    with pytest.raises(ValueError, match='run'):
        _target(run=run).uri()


def test_an_unknown_backend_is_refused_with_the_two_it_knows():
    with pytest.raises(ValueError, match='MDSplus'):
        _target(backend=99).uri()


def test_a_case_named_by_a_path_is_written_where_it_is_named():
    """A scripted caller -- or a test -- names a directory, not four fields."""
    assert _target(uri=CASE_URI).uri() == CASE_URI


# ---------------------------------------------------------------------------
# Two versions, and the old code carried one of them.

def test_the_uri_carries_the_major_of_the_data_dictionary():
    target = _target(dataVersion='3.35.0')
    assert 'version=3;' in target.uri() + ';'
    assert 'version=3.35.0' not in target.uri()
    assert target.dataMajor() == '3'


def test_a_target_without_a_version_says_so_instead_of_naming_a_directory():
    with pytest.raises(ValueError, match='version'):
        _target(dataVersion=None).uri()


def test_the_write_entry_is_built_at_the_full_dictionary_version(monkeypatch):
    """``dd_version='3'`` is refused: ``UnknownDDVersion: Data dictionary version
    '3' cannot be found``, while the URI next to it says ``version=3``."""
    recorder = RecordingIMAS()
    monkeypatch.setattr(exportModule, 'imas', recorder)
    QVizExportToIDS.openForWriting(USER_URI, '3.35.0')
    assert recorder.calls == [(USER_URI, 'w', '3.35.0')]


def test_no_version_is_invented_when_there_is_none_to_pin(monkeypatch):
    recorder = RecordingIMAS()
    monkeypatch.setattr(exportModule, 'imas', recorder)
    QVizExportToIDS.openForWriting(USER_URI, None)
    assert recorder.calls == [(USER_URI, 'w', None)]


# ---------------------------------------------------------------------------
# What the dialog starts from.

class StubSource:
    def __init__(self, uri, dd_version=None):
        self.uri = uri
        self.dd_version = dd_version
        self.data_entries = {}


def test_the_prefill_names_the_case_that_is_open():
    """Not ``/`` and ``/``: the case on the screen is the best guess there is."""
    target = QVizExportTarget.fromCase(StubSource(USER_URI, '3.35.0'))
    assert (target.user, target.database) == ('g2lfleur', 'west')
    assert (target.shot, target.run) == (54924, 0)
    assert target.dataVersion == '3.35.0'


def test_a_case_named_by_a_path_still_prefills_what_a_path_names():
    target = QVizExportTarget.fromCase(
        StubSource(CASE_URI, CASE_DATA_DICTIONARY_VERSION))
    assert (target.database, target.shot, target.run) == ('west', 54924, 0)
    assert target.dataVersion == CASE_DATA_DICTIONARY_VERSION
    # A path names no user, so the login stands in for it rather than an empty
    # box that the export would refuse.
    assert target.user == os.environ.get('USER', '')


# ---------------------------------------------------------------------------
# The dialog itself.

@pytest.fixture
def dialog(qapp):
    built = QVizExportDialog(None, QVizExportTarget.fromCase(
        StubSource(USER_URI, '3.35.0')))
    yield built
    built.destroy()


@pytest.mark.ui
def test_the_dialog_asks_the_four_fields_the_manual_lists(dialog):
    for name in ('userBox', 'databaseBox', 'shotBox', 'runBox'):
        assert getattr(dialog, name).isHidden() is False


@pytest.mark.ui
def test_the_dialog_starts_from_the_open_case(dialog):
    assert dialog.userBox.text() == 'g2lfleur'
    assert dialog.databaseBox.text() == 'west'
    assert dialog.shotBox.text() == '54924'
    assert dialog.runBox.text() == '0'


@pytest.mark.ui
def test_a_shot_box_cannot_hold_letters(dialog):
    """The old handler read its text boxes with ``int()`` and answered
    ``ValueError: invalid literal for int() with base 10: 'abc'`` from the OK
    button; here the box refuses the letters before the handler sees them."""
    shot = dialog.shotBox.validator()
    assert shot.validate('abc', 0)[0] == QValidator.Invalid
    assert shot.validate('54924', 0)[0] == QValidator.Acceptable
    assert dialog.runBox.validator().validate('-1', 0)[0] == QValidator.Invalid


@pytest.mark.ui
def test_the_backend_is_a_choice_and_not_a_number(dialog):
    """The old dialog asked for ``13`` in a text box the manual never mentions."""
    labels = [dialog.backendCombo.itemText(i)
              for i in range(dialog.backendCombo.count())]
    assert labels == ['HDF5', 'MDSplus']
    assert dialog.target().backend == HDF5
    dialog.backendCombo.setCurrentIndex(1)
    assert dialog.target().backend == MDSPLUS
    assert 'mdsplus' in dialog.target().uri()


@pytest.mark.ui
def test_a_run_of_zero_stays_a_run_of_zero(dialog):
    """``int('')`` and ``int('0')`` used to be the only reading of the box; an
    empty run number is a missing field, and 0 is a run."""
    dialog.runBox.setText('0')
    assert dialog.target().run == 0
    dialog.runBox.setText('')
    with pytest.raises(ValueError, match='run'):
        dialog.target().uri()


@pytest.mark.ui
def test_a_field_cleared_in_the_dialog_is_named_by_the_reason(dialog):
    dialog.databaseBox.setText('')
    with pytest.raises(ValueError, match='database'):
        dialog.target().uri()


@pytest.mark.ui
def test_the_two_notes_the_manual_shows_are_in_the_dialog(dialog):
    from PySide6.QtWidgets import QLabel
    texts = [label.text() for label in dialog.findChildren(QLabel)]
    assert any('CURRENTLY OPENED' in text for text in texts)
    assert any('imasdb' in text for text in texts)


# ---------------------------------------------------------------------------
# The command: what it writes, and what it says when it cannot.

class StubIds:
    """Enough of an IDS for the version and the occurrence the export needs."""

    def __init__(self, version='3.35.0'):
        self.ids_properties = type(str('Props'), (), {})()
        self.ids_properties.version_put = type(str('Put'), (), {})()
        self.ids_properties.version_put.data_dictionary = version


class StubTreeView:
    """Enough of a shot view for the command: a case, its cache, no Qt."""

    def __init__(self, uri=USER_URI, dd_version='3.35.0', opened=None):
        self.uri = uri
        self.parent = None
        self.selectedItem = None
        self.dataSource = StubSource(uri, dd_version)
        for key, ids in (opened or {}).items():
            self.dataSource.data_entries[key] = ids


class FakeEntry:
    """An IMAS-Python entry: open from construction, and it says so twice."""

    def __init__(self, uri, mode, dd_version=None):
        self.uri = uri
        self.mode = mode
        self.dd_version = dd_version
        self.putOccurrences = {}
        self.closed = 0
        self.openCalls = 0

    def open(self):
        self.openCalls += 1
        raise RuntimeError('This DBEntry is already open')

    def put(self, ids, occurrence):
        self.putOccurrences[ids.name] = occurrence

    def close(self):
        self.closed += 1


class RecordingIMAS:
    """The Access Layer, standing in for a module that needs a real case.

    Its entries answer what the real ones answer -- an entry built from an URI
    is open already and refuses a second ``open()`` -- so the command's own
    choices (never call it, close the entry whatever happens) are what fails a
    test here, not the absence of an Access Layer.
    """

    entryClass = FakeEntry

    def __init__(self):
        self.entries = []
        self.calls = []

    def DBEntry(self, uri, mode, dd_version=None):
        self.calls.append((uri, mode, dd_version))
        entry = self.entryClass(uri, mode, dd_version)
        self.entries.append(entry)
        return entry


@pytest.fixture
def fakeAccessLayer(monkeypatch):
    """The Access Layer, replaced by something that answers when asked to open twice."""
    fake = RecordingIMAS()
    monkeypatch.setattr(exportModule, 'imas', fake)
    return fake


def viewWith(*idsNames, **kwargs):
    opened = {}
    for index, name in enumerate(idsNames):
        ids = StubIds(kwargs.get('version', '3.35.0'))
        ids.name = name
        opened['%s/%d' % (name, kwargs.get('occurrence', index))] = ids
    return StubTreeView(opened=opened,
                        dd_version=kwargs.get('dd_version', '3.35.0'))


class RefusingEntry(FakeEntry):
    """An entry that refuses every IDS it is handed."""

    def put(self, ids, occurrence):
        raise RuntimeError('IDS %s is refused' % ids.name)


class PartlyRefusingEntry(FakeEntry):
    """An entry that refuses one named IDS and takes the rest."""

    refused = 'hard_x_rays'

    def put(self, ids, occurrence):
        if ids.name == self.refused:
            raise RuntimeError('IDS %s is refused' % ids.name)
        return FakeEntry.put(self, ids, occurrence)


def useAccessLayer(monkeypatch, entryClass=FakeEntry):
    """Replace the Access Layer of the command module, entries of one kind."""
    fake = RecordingIMAS()
    fake.entryClass = entryClass
    monkeypatch.setattr(exportModule, 'imas', fake)
    return fake


def test_nothing_is_written_when_no_ids_is_open(fakeAccessLayer):
    """The manual says what is exported: the IDSs CURRENTLY OPENED in the tree
    view. With none, there is no export to attempt -- and no half-made case."""
    with pytest.raises(ValueError, match='no IDS is open'):
        QVizExportToIDS(StubTreeView(), target=_target()).execute()
    assert fakeAccessLayer.entries == []


def test_the_entry_is_never_asked_to_open_a_second_time(fakeAccessLayer):
    """An entry built from an URI is open already; ``open()`` on it is what used
    to fail, and nothing here calls it."""
    view = viewWith('pulse_schedule')
    QVizExportToIDS(view, target=_target()).execute()
    entry = fakeAccessLayer.entries[0]
    assert entry.openCalls == 0
    assert entry.mode == 'w'


def test_the_dictionary_version_is_pinned_where_the_entry_is_built(fakeAccessLayer):
    view = viewWith('pulse_schedule')
    QVizExportToIDS(view, target=_target()).execute()
    entry = fakeAccessLayer.entries[0]
    assert entry.dd_version == '3.35.0'
    assert 'version=3;' in entry.uri + ';'


def test_the_occurrence_written_is_the_occurrence_that_is_open(fakeAccessLayer):
    opened = {'equilibrium/2': StubIds()}
    opened['equilibrium/2'].name = 'equilibrium'
    opened['interferometer/0'] = StubIds()
    opened['interferometer/0'].name = 'interferometer'
    view = StubTreeView(opened=opened)
    QVizExportToIDS(view, target=_target()).execute()
    entry = fakeAccessLayer.entries[0]
    assert entry.putOccurrences == {'equilibrium': 2, 'interferometer': 0}


def test_an_entry_the_access_layer_refuses_to_build_is_said_in_words(monkeypatch):
    class UnavailableIMAS:
        def DBEntry(self, uri, mode, dd_version=None):
            raise RuntimeError('Database west is not available')

    monkeypatch.setattr(exportModule, 'imas', UnavailableIMAS())
    with pytest.raises(ValueError) as error:
        QVizExportToIDS(viewWith('pulse_schedule'),
                        target=_target()).execute()
    assert 'not available' in str(error.value)
    assert USER_URI in str(error.value)


def test_an_entry_is_closed_when_a_put_fails(monkeypatch):
    """A failed put leaves the entry open behind itself unless a ``finally``
    closes it; the old code had none, so a second attempt never worked."""
    fake = useAccessLayer(monkeypatch, RefusingEntry)
    with pytest.raises(ValueError, match='refused'):
        QVizExportToIDS(viewWith('pulse_schedule'), target=_target()).execute()
    assert fake.entries[0].closed == 1


def test_one_refused_ids_does_not_cost_the_others(monkeypatch, caplog):
    """The user who opened three IDSs and lost two of them to one the target
    refuses is the reason every refusal is named, and the counts are absolute."""
    fake = useAccessLayer(monkeypatch, PartlyRefusingEntry)
    view = viewWith('pulse_schedule', 'hard_x_rays', 'equilibrium')
    with caplog.at_level(logging.INFO, logger=view.uri):
        QVizExportToIDS(view, target=_target()).execute()
    assert sorted(fake.entries[0].putOccurrences) == ['equilibrium',
                                                      'pulse_schedule']
    assert '2 of 3 IDS(s) written' in caplog.text
    assert 'hard_x_rays' in caplog.text


def test_an_export_that_writes_nothing_is_reported(monkeypatch):
    """A case directory and no IDS is not an export, and it cannot be left silent
    the way the bare ``except:`` left it."""
    fake = useAccessLayer(monkeypatch, RefusingEntry)
    with pytest.raises(ValueError, match='Nothing was written'):
        QVizExportToIDS(viewWith('pulse_schedule'), target=_target()).execute()
    assert fake.entries[0].closed == 1


# ---------------------------------------------------------------------------
# Which version the export is written at is not a free choice.

def test_the_version_written_is_the_one_the_case_was_opened_at():
    """The pin the case was opened at wins: every loaded IDS was already
    validated against it, so it is the version the entry can be built at."""
    view = viewWith('pulse_schedule', dd_version='3.44.0')
    assert QVizExportToIDS.dataDictionaryOf(
        view.dataSource, QVizExportToIDS(view).loadedIds()) == '3.44.0'


def test_the_ids_themselves_answer_when_the_case_names_no_version():
    view = viewWith('pulse_schedule', dd_version=None)
    assert QVizExportToIDS.dataDictionaryOf(
        view.dataSource, QVizExportToIDS(view).loadedIds()) == '3.35.0'


def test_two_major_versions_cannot_be_written_into_one_case():
    opened = {'a/0': StubIds('3.35.0'), 'b/0': StubIds('4.1.1')}
    opened['a/0'].name = 'a'
    opened['b/0'].name = 'b'
    view = StubTreeView(opened=opened, dd_version=None)
    with pytest.raises(ValueError, match='major versions'):
        QVizExportToIDS.dataDictionaryOf(view.dataSource,
                                         QVizExportToIDS(view).loadedIds())


def test_a_target_of_another_major_is_refused_before_anything_is_written(fakeAccessLayer):
    """The Access Layer would answer it too, after some IDSs were already stored."""
    with pytest.raises(ValueError, match='major version'):
        QVizExportToIDS(viewWith('pulse_schedule'),
                        target=_target(dataVersion='4')).execute()
    assert fakeAccessLayer.entries == []


# ---------------------------------------------------------------------------
# The real thing: an IDS read from the reference case, written, read back.

@pytest.mark.case
def test_an_exported_ids_is_found_again_in_the_case_it_was_written_to(tmp_path):
    """The only proof that counts for a gesture that wrote 0 IDSs: bytes on disk
    that the Access Layer hands back.

    Written under a ``path=`` URI inside the test directory, never through a
    database name: measured, an URI naming a database that does not exist does
    not fail, it creates one under the login's own imasdb tree.
    """
    uri = case_uri_or_skip()
    if uri is None:
        pytest.skip('reference case not reachable')
    import imas

    reader = imas.DBEntry(uri, 'r', dd_version=CASE_DATA_DICTIONARY_VERSION)
    ids = reader.get('pulse_schedule', 0)
    reader.close()

    target = os.path.join(str(tmp_path), 'exported', '3', '54924', '0')
    exportUri = 'imas:hdf5?path=' + target
    view = StubTreeView(opened={'pulse_schedule/0': ids},
                        dd_version=CASE_DATA_DICTIONARY_VERSION)
    writtenUri = QVizExportToIDS(
        view, target=QVizExportTarget(uri=exportUri)).execute()
    assert writtenUri == exportUri

    back = imas.DBEntry(exportUri, 'r',
                        dd_version=CASE_DATA_DICTIONARY_VERSION)
    try:
        assert back.list_all_occurrences('pulse_schedule') == [0]
    finally:
        back.close()

    files = {name: os.path.getsize(os.path.join(root, name))
             for root, _, names in os.walk(target) for name in names}
    assert 'pulse_schedule.h5' in files
    assert files['pulse_schedule.h5'] > 1000
