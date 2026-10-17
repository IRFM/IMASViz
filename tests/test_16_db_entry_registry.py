# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""One IMAS entry per URI, references counted.

Each data source used to own its imas.DBEntry and to open and close it once per
IDS. Two consequences were measured on the reference case: loading a second IDS
through the same source raised (the entry was closed but the reference kept, so
the next open() tried to re-open an entry built from an URI, which IMAS-Python
refuses), and a plugin asking for the same case opened the very same file a
second time and read the same IDS all over again.
"""

import pytest

from conftest import CASE_DATA_DICTIONARY_VERSION, case_uri_or_skip

from imasviz.VizDataSource.QVizDBEntryRegistry import QVizDBEntryRegistry

PATH_URI = 'imas:hdf5?path=/afs/eufus.eu/g2itmdev/user/g2lfleur/public/imasdb/west/3/54924/0'


class CountingEntry:
    """Stands in for imas.DBEntry: counts opens, closes and get() calls."""

    def __init__(self, uri, mode):
        self.uri = uri
        self.mode = mode
        self.opens = 0
        self.closes = 0
        self.closed = False

    def open(self):
        self.opens += 1
        return (0, 0)

    def close(self):
        self.closes += 1
        self.closed = True

    def get(self, IDSName, occurrence):
        return (IDSName, occurrence, self.mode)


@pytest.fixture(autouse=True)
def emptyRegistry():
    QVizDBEntryRegistry.reset()
    yield QVizDBEntryRegistry
    QVizDBEntryRegistry.reset()


def acquire(uri=PATH_URI, mode='r', dd_version=None):
    return QVizDBEntryRegistry.acquire(
        uri, mode, dd_version,
        build=lambda: CountingEntry(uri, mode))


def test_the_same_uri_is_opened_only_once():
    first = acquire()
    second = acquire()

    assert first is second
    assert QVizDBEntryRegistry.count(PATH_URI) == 2
    assert len(QVizDBEntryRegistry.live_entries()) == 1


def test_an_entry_is_closed_when_the_last_user_releases_it():
    entry = acquire()
    acquire()

    QVizDBEntryRegistry.release(PATH_URI)
    assert not entry.closed
    assert QVizDBEntryRegistry.count(PATH_URI) == 1

    QVizDBEntryRegistry.release(PATH_URI)
    assert entry.closed
    assert QVizDBEntryRegistry.count(PATH_URI) == 0
    assert QVizDBEntryRegistry.live_entries() == []


def test_a_released_entry_is_not_left_behind_as_a_stale_handle():
    # The measured defect: close() closed the entry but the source kept the
    # object, so the next open() tried to re-open it and IMAS-Python refused.
    entry = acquire()
    QVizDBEntryRegistry.release(PATH_URI)

    rebuilt = acquire()
    assert rebuilt is not entry
    assert not rebuilt.closed


def test_the_data_dictionary_pin_is_part_of_the_key():
    # IMAS-Python pins the dictionary when the entry is built, so one case read
    # under two dictionary versions cannot share a single entry.
    unpinned = acquire()
    pinned = acquire(dd_version=CASE_DATA_DICTIONARY_VERSION)

    assert pinned is not unpinned
    assert len(QVizDBEntryRegistry.live_entries()) == 2


def test_write_mode_does_not_share_with_read_mode():
    reader = acquire()
    writer = acquire(mode='w')

    assert writer is not reader
    assert writer.mode == 'w'


def test_releasing_more_than_acquired_does_not_disturb_the_next_user():
    # A caller that lost its reference must not close the file under the feet
    # of whoever asks for the case afterwards.
    first = acquire()
    QVizDBEntryRegistry.release(PATH_URI)
    QVizDBEntryRegistry.release(PATH_URI)

    assert QVizDBEntryRegistry.count(PATH_URI) == 0
    second = acquire()
    assert second is not first
    assert not second.closed


def test_the_loaded_idss_survive_the_entry_being_closed():
    # exportToLocal (QVizIMASDataSource.py) writes what has been loaded, reading
    # it from this cache: an IDS loaded, then the case closed, must still be
    # there to export. An entry loads the whole IDS in memory, so the instance
    # stays valid once the file is closed.
    entry = acquire()
    cache = QVizDBEntryRegistry.ids_cache(PATH_URI)
    cache['tf/0'] = entry.get('tf', 0)
    QVizDBEntryRegistry.release(PATH_URI)

    assert list(QVizDBEntryRegistry.ids_cache(PATH_URI)) == ['tf/0']
    assert QVizDBEntryRegistry.live_entries() == []


def test_dropping_a_case_forgets_the_loaded_idss():
    entry = acquire()
    QVizDBEntryRegistry.ids_cache(PATH_URI)['tf/0'] = entry.get('tf', 0)
    QVizDBEntryRegistry.release(PATH_URI)

    assert QVizDBEntryRegistry.drop(PATH_URI) is True
    assert QVizDBEntryRegistry.ids_cache(PATH_URI) == {}
    assert QVizDBEntryRegistry.known_cases() == []


def test_the_loaded_idss_are_shared_between_users_of_one_uri():
    entry = acquire()
    cache = QVizDBEntryRegistry.ids_cache(PATH_URI)
    cache['equilibrium/0'] = entry.get('equilibrium', 0)

    assert QVizDBEntryRegistry.ids_cache(PATH_URI) is cache


def makeSource(uri):
    from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
    source = QVizDataSourceFactory().create(uri)
    # The case was written with this dictionary; the harness runs against
    # another one, so the entry has to be pinned or the AL refuses to read it.
    source.dd_version = CASE_DATA_DICTIONARY_VERSION
    return source


def loadIDS(source, IDSName):
    from imasviz.VizDataAccess.QVizIDSViewParser import QVizIDSViewParser
    from imasviz.VizUtils import QVizPreferences
    from support.fakes import FakeTreeView

    QVizPreferences.Ignore_GGD = 1
    view = FakeTreeView(uri=source.uri)
    parser = QVizIDSViewParser(source.uri, view, IDSName, 0, None, False)
    parser.dataSource = source
    parser.loadIDS(IDSName, 0)


@pytest.mark.case
def test_two_idss_can_be_loaded_through_one_source(qapp):
    # This is what the shot view does: QVizLoadSelectedData.py:33 calls
    # dataSource.load() on the view's source, once per selected IDS.
    uri = case_uri_or_skip()
    source = makeSource(uri)

    loadIDS(source, 'tf')
    loadIDS(source, 'pulse_schedule')

    assert sorted(source.data_entries) == ['pulse_schedule/0', 'tf/0']


@pytest.mark.case
def test_a_second_source_on_the_same_uri_reuses_the_entry(qapp):
    # Plugins build their own source through the factory (viz_Profiles,
    # viz_equi), which used to open the same HDF5 file a second time and read
    # the same IDS all over again.
    uri = case_uri_or_skip()
    shotView = makeSource(uri)
    plugin = makeSource(uri)

    loadIDS(shotView, 'tf')
    loadIDS(plugin, 'tf')

    assert len(QVizDBEntryRegistry.known_cases()) == 1
    assert plugin.data_entries['tf/0'] is shotView.data_entries['tf/0']
    # Both loads released their reference: nobody holds the file open.
    assert QVizDBEntryRegistry.live_entries() == []


@pytest.mark.case
def test_the_case_is_closed_again_once_nobody_needs_it(qapp):
    uri = case_uri_or_skip()
    source = makeSource(uri)
    loadIDS(source, 'tf')

    assert QVizDBEntryRegistry.live_entries() == []


@pytest.mark.case
def test_a_shot_view_going_away_forgets_the_case_it_loaded(qapp):
    # Viz_API.RemoveDTVFrame calls forget_case() on the view's source; the
    # loaded IDSs used to go away with the source it owned.
    uri = case_uri_or_skip()
    source = makeSource(uri)
    loadIDS(source, 'tf')

    assert list(source.data_entries) == ['tf/0']
    assert source.forget_case() is True
    assert source.data_entries == {}
    assert QVizDBEntryRegistry.known_cases() == []
