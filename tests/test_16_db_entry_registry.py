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
from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource

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

    def get(self, IDSName, occurrence, lazy=False):
        return (IDSName, occurrence, self.mode, lazy)


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


def test_an_eagerly_read_ids_survives_the_entry_being_closed():
    # exportToLocal (QVizIMASDataSource.py) writes what has been loaded, reading
    # it from this cache: an IDS read **whole**, then the case closed, must still
    # be there to export. `get()` copied the whole IDS into memory, so the
    # instance stays valid once the file is closed.
    entry = acquire()
    QVizDBEntryRegistry.cache_ids(PATH_URI, 'tf/0', entry.get('tf', 0))
    QVizDBEntryRegistry.release(PATH_URI)

    assert list(QVizDBEntryRegistry.ids_cache(PATH_URI)) == ['tf/0']
    assert QVizDBEntryRegistry.live_entries() == []


def test_a_lazily_read_ids_is_forgotten_when_the_entry_closes():
    # A lazy instance is a window on the open file, not a copy of it: measured on
    # the reference case, reading a node of one after `entry.close()` answers
    # `RuntimeError: Cannot lazy load the requested data: the data entry is no
    # longer available for reading.` Keeping it would hand the views and the
    # export a handle that has gone blind, refusing at a distance whatever the
    # read was about.
    entry = acquire()
    QVizDBEntryRegistry.cache_ids(PATH_URI, 'tf/0', entry.get('tf', 0),
                                  lazy=True)
    assert list(QVizDBEntryRegistry.ids_cache(PATH_URI)) == ['tf/0']

    QVizDBEntryRegistry.release(PATH_URI)
    assert QVizDBEntryRegistry.ids_cache(PATH_URI) == {}


def test_a_lazily_read_ids_survives_while_someone_holds_the_case():
    # The other half of the rule: a shot view holds a reference for as long as
    # its tree shows nodes of the case, and the lazy handles it drew stay
    # readable for exactly that long.
    acquire()
    acquire()
    entry = QVizDBEntryRegistry.entry(PATH_URI)
    QVizDBEntryRegistry.cache_ids(PATH_URI, 'tf/0', entry.get('tf', 0),
                                  lazy=True)

    QVizDBEntryRegistry.release(PATH_URI)
    assert list(QVizDBEntryRegistry.ids_cache(PATH_URI)) == ['tf/0']

    QVizDBEntryRegistry.release(PATH_URI)
    assert QVizDBEntryRegistry.ids_cache(PATH_URI) == {}


def test_the_source_asks_for_its_idss_lazily():
    # What the reading of an IDS costs is dominated by that flag: measured on the
    # reference case, the walk of `equilibrium` occurrence 0 answers 3,99 s and
    # +122,8 Mo read whole, 0,10 s and +7,7 Mo read lazily -- for an identical
    # tree (7203 elements, 7030 leaves).
    source = QVizIMASDataSource('west 54924', PATH_URI)
    acquire()

    instance = source.get('tf', 0)
    assert instance == ('tf', 0, 'r', True)
    assert source.data_entries['tf/0'] is instance
    # The reference the source holds was taken by `open()`; while someone holds
    # it, the instance is in the cache.
    QVizDBEntryRegistry.release(PATH_URI)
    assert source.data_entries == {}


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


def test_a_source_entry_tracks_the_registry():
    # A source must not own a handle of its own: whatever it hands out is what
    # the registry currently holds, or nothing at all.
    source = QVizIMASDataSource('west 54924', PATH_URI)
    assert source.db_entry is None

    entry = acquire()
    assert source.db_entry is entry

    QVizDBEntryRegistry.release(PATH_URI)
    assert source.db_entry is None


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
    # dataSource.load() on the view's source, once per selected IDS. The view
    # holds its own reference on the case between the two loads
    # (createEmptyIDSsTree), which is what keeps the lazy instances it drew
    # readable; without it the walk would close the file under its own tree.
    uri = case_uri_or_skip()
    source = makeSource(uri)

    source.open()
    try:
        loadIDS(source, 'tf')
        loadIDS(source, 'pulse_schedule')

        assert sorted(source.data_entries) == ['pulse_schedule/0', 'tf/0']
    finally:
        source.close()


@pytest.mark.case
def test_a_second_source_on_the_same_uri_reuses_the_entry(qapp):
    # Plugins build their own source through the factory (viz_Profiles,
    # viz_equi), which used to open the same HDF5 file a second time and read
    # the same IDS all over again.
    uri = case_uri_or_skip()
    shotView = makeSource(uri)
    plugin = makeSource(uri)

    shotView.open()
    try:
        loadIDS(shotView, 'tf')
        loadIDS(plugin, 'tf')

        assert len(QVizDBEntryRegistry.known_cases()) == 1
        assert plugin.data_entries['tf/0'] is shotView.data_entries['tf/0']
        # Only the view's own reference is left: the two walks gave theirs back.
        assert QVizDBEntryRegistry.count(uri, shotView.MODE,
                                         shotView.dd_version) == 1
    finally:
        shotView.close()

    # Nobody needs the case any more: nothing is left holding it.
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
    source.open()
    loadIDS(source, 'tf')

    assert list(source.data_entries) == ['tf/0']
    assert source.forget_case() is True
    assert source.data_entries == {}
    assert QVizDBEntryRegistry.known_cases() == []


@pytest.mark.case
def test_a_failed_walk_gives_back_the_reference_it_took(qapp):
    # The walk is all that stands between the parser's open() and its close().
    # run() (:139-157) logs the failure and leaves without closing, so the
    # reference stayed held and the case was never released again.
    uri = case_uri_or_skip()
    source = makeSource(uri)

    # An IDS this case does not hold. The read used to be swallowed into a None
    # that died further away on `.metadata`; it now raises with what was asked,
    # of which case and why. What this test pins is that the reference comes
    # back either way, and the `finally` of `loadIDS` is what does it.
    with pytest.raises(ValueError) as raised:
        loadIDS(source, 'no_such_ids')
    assert "Cannot read no_such_ids occurrence 0" in str(raised.value)

    assert QVizDBEntryRegistry.count(uri, source.MODE, source.dd_version) == 0
    assert QVizDBEntryRegistry.live_entries() == []


@pytest.mark.case
def test_the_view_reference_keeps_one_entry_for_the_whole_view(qapp):
    # createEmptyIDSsTree opens for the view and holds that reference until
    # RemoveDTVFrame. The parser's own open() and close() then only move the
    # count, so nothing is closed and rebuilt between two IDSs.
    uri = case_uri_or_skip()
    source = makeSource(uri)
    source.open()
    try:
        loadIDS(source, 'tf')
        entry = source.db_entry
        loadIDS(source, 'pulse_schedule')

        assert source.db_entry is entry
        assert QVizDBEntryRegistry.count(uri, source.MODE, source.dd_version) == 1
    finally:
        source.close()
