# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Exporting what a shot view holds, then opening again what was written.

The manual's Export copies *the IDSs currently opened in the tree view* into
another case. ``QVizExportToIDS`` reads them from ``dataSource.data_entries``,
the cache the plots read, and the proof this file makes is the only one that
counts for a gesture whose failure is silent: bytes on disk that the Access Layer
hands back, holding the same numbers.

What was measured on the reference case (``west`` 54924 run 0, data dictionary
3.35.0) before a line of this file was written. A view whose case is opened but
whose occurrences are not loaded holds ``data_entries == {}``, and the command
refuses with "no IDS is open". Loading ``pulse_schedule`` occurrence 0 puts one
key in the cache, ``pulse_schedule/0``, and gives the tree **264** leaves;
loading ``equilibrium`` occurrence 0 puts ``equilibrium/0`` beside it and takes
the tree to **3 632** leaves. The command then finds two IDSs, named by the cache
key and not by any node of the tree, and writes them in **0,85 s**: a
``master.h5`` of 2 056 bytes, an ``equilibrium.h5`` of **13 326 708**, a
``pulse_schedule.h5`` of **83 618**. Opening that case again (3,63 s) answers the
same filled-path counts as the source -- **133** and **15** -- and the same
values: ``global_quantities.ip`` -77009.31617883372, a ``time`` array of 49
samples equal element for element.

Two facts worth having measured, because they are not what the sentence "export
what is open" suggests.

An occurrence *loaded for the tree* is not an occurrence truncated to what the
tree shows: the tree keeps one time slice of ``equilibrium`` (3 368 leaves) while
the cache holds the whole IDS, and the written case answers 133 filled paths, the
same as the source. What the user sees and what the user exports are two
different amounts, and the second is the larger.

And the export leaves the view it read from exactly as it was: same cache keys,
same loaded occurrences, same 3 632 leaves. What it writes, though, is a copy
read **whole** through the open entry, not the handle the tree reads: the views
read lazily and the Access Layer refuses to write a lazy handle
(``ValueError: Lazy loaded IDSs cannot be used in put or put_slice.``, measured;
filling it in place is refused too, ``get(destination=...)`` answering
``ValueError: Lazy-loaded IDSs are read-only.``). Exporting the two occurrences
as the tree held them left one 1 912-byte ``master.h5`` and nothing else, and the
case read back answered ``IDS 'equilibrium', occurrence 0 is empty``.

The writing target is named by a ``path=`` URI throughout, never by a database
name: measured earlier and pinned in ``test_40_export_to_ids.py``, an URI naming
a database that does not exist does not fail, it creates one under the login's
own ``imasdb`` tree.

And the view this file builds looks at a case of its own, holding the two IDSs
above copied out of the reference case. Not for shyness about the reference
case: ``dataSource.data_entries`` is ``QVizDBEntryRegistry.ids_cache(uri, mode,
dd_version)``, **one dict per case for the whole process**. Every other file of
the suite opens the reference case, so a view of it shares a cache that other
files have already filled -- measured in a full run, ``calorimetry/0`` through
``tf/0`` were there before this file's first load -- and an export from it writes
every one of those. The application never meets that, because
``QVizOpenShotView.Open`` reuses the one view of a case; a test must not depend
on which files ran first.
"""

import os

import pytest

from PySide6.QtWidgets import QMdiArea

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)
from support import ownership

from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizGUICommands.VizDataExport.QVizExportDialog import \
    QVizExportTarget
from imasviz.VizGUI.VizGUICommands.VizDataExport.QVizExportToIDS \
    import QVizExportToIDS
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.Viz_API import Viz_API

PULSE = 'pulse_schedule'
EQUILIBRIUM = 'equilibrium'
OCCURRENCE = 0

# What the reference case answers, counted rather than assumed.
PULSE_LEAVES = 264
EQUILIBRIUM_LEAVES = 3368
BOTH_LEAVES = 3632
FILLED_PATHS = {EQUILIBRIUM: 133, PULSE: 15}

# The written case, measured. Byte sizes move with the Access Layer's compressor,
# so they are asserted as orders of magnitude; the filled-path counts are what the
# data dictionary answers, and they are asserted exactly.
MASTER_BYTES = 2056
EQUILIBRIUM_BYTES = 13326708
PULSE_BYTES = 83618

IP = -77009.31617883372
TIME_SAMPLES = 49

pytestmark = [pytest.mark.case, pytest.mark.dd, pytest.mark.ui]


class Session:
    """One shot view of a case this file made, and the case it exports into.

    The view is built the way ``QVizOpenShotView.Open`` builds one, so the cache
    the export reads is the cache an occurrence load fills -- which is the whole
    point of this file: the stub view of ``test_40_export_to_ids.py`` had its
    cache filled by hand.
    """

    def __init__(self, api, view, targetUri):
        self.api = api
        self.view = view
        self.targetUri = targetUri

    def load(self, idsName, occurrence=OCCURRENCE):
        QVizLoadOccurrence(dataTreeView=self.view, idsName=idsName,
                           occurrence=occurrence, asynch=False).execute()

    def cacheKeys(self):
        return sorted(self.view.dataSource.data_entries)

    def exported(self, target=None):
        """The Export entry, with the target already chosen -- no dialog."""
        return QVizExportToIDS(
            self.view, target=target or QVizExportTarget(
                uri=self.targetUri)).execute()


def privateCase(directory):
    """The two IDSs this file works on, held by a case of its own.

    Asked of the Access Layer, never of the file system. Measured: the reference
    run directory holds **one** file, a 6 365-byte ``master.h5``, and its
    ``equilibrium`` group is an HDF5 link into ``../4/equilibrium.h5`` -- so a
    copy of that directory answers ``Unable to open HDF5 group: equilibrium``
    the moment the Access Layer follows it. Asking the layer for the IDS and
    putting it into a case of the same shape follows the link for us.

    The layout spells ``west``, because the prefill checked at the end of this
    file takes the database name out of the path the case was opened from.
    """
    import imas

    uri = 'imas:hdf5?path=' + os.path.join(directory, 'west', '3', '54924', '0')
    reader = imas.DBEntry(CASE_URI, 'r', dd_version=CASE_DATA_DICTIONARY_VERSION)
    writer = None
    try:
        writer = imas.DBEntry(uri, 'w', dd_version=CASE_DATA_DICTIONARY_VERSION)
        for name in (EQUILIBRIUM, PULSE):
            writer.put(reader.get(name, OCCURRENCE), OCCURRENCE)
    finally:
        reader.close()
        if writer is not None:
            writer.close()
    return uri


@pytest.fixture(scope='module')
def session(qapp, tmp_path_factory):
    """The case opened, nothing loaded yet, and a directory to write into."""
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    caseUri = privateCase(str(tmp_path_factory.mktemp('ownCase')))
    targetDir = str(tmp_path_factory.mktemp('exportedCase'))
    targetUri = 'imas:hdf5?path=' + os.path.join(targetDir, '3', '54924', '0')
    api = Viz_API(parent=QMdiArea())
    ownership.keep(api)
    source = QVizDataSourceFactory().create(caseUri)
    source.dd_version = CASE_DATA_DICTIONARY_VERSION
    view = api.CreateDataTree(source).dataTreeView
    api.ShowDataTree(view)
    session = Session(api, view, targetUri)
    # The readers this file opens are the harness's, and they have to be closed:
    # an entry left open on a case directory keeps the HDF5 file behind it.
    session.readers = []
    try:
        yield session
    finally:
        for entry in session.readers:
            entry.close()


def openForReading(session):
    """The case the session wrote, opened the way any other case is opened."""
    import imas
    entry = imas.DBEntry(session.targetUri, 'r',
                         dd_version=CASE_DATA_DICTIONARY_VERSION)
    session.readers.append(entry)
    return entry


def leavesOf(view, idsName):
    """The paths this view's tree holds for one IDS, as the leaves spell them."""
    return [leaf.getDataName() or '' for leaf in view.signalsList
            if (leaf.getDataName() or '').startswith(idsName)]


def treeSlices(view, idsName):
    """The ``time_slice`` indexes this view's tree actually holds for an IDS.

    Asked of the leaves, because they are what the user can select: a leaf's
    ``dataName`` spells the path it points at, index included
    (``equilibrium.time_slice[0].global_quantities.ip``). Kept as text, since a
    parametrized view writes the index *name* where a loaded one writes a number.
    """
    prefix = idsName + '.time_slice['
    return sorted({name[len(prefix):].split(']', 1)[0]
                   for name in leavesOf(view, idsName)
                   if name.startswith(prefix)})


# --------------------------------------------------------------------------
# What the command reads is the cache of a real view
# --------------------------------------------------------------------------

def test_a_view_that_has_loaded_nothing_has_exported_nothing(session):
    assert session.cacheKeys() == []
    assert QVizExportToIDS(session.view).loadedIds() == []

    with pytest.raises(ValueError, match='no IDS is open'):
        session.exported()


def test_an_occurrence_load_is_what_the_export_finds(session):
    session.load(PULSE)

    # One key per opened IDS, spelling the occurrence.
    assert session.cacheKeys() == ['%s/%d' % (PULSE, OCCURRENCE)]
    assert len(session.view.signalsList) == PULSE_LEAVES
    loaded = QVizExportToIDS(session.view).loadedIds()
    assert [(name, occurrence) for name, occurrence, _ in loaded] == \
        [(PULSE, OCCURRENCE)]

    # The occurrences written are the ones the view opened; the objects written
    # are not the objects the tree reads. The tree's handle is a lazy window on
    # the open file, and the Access Layer refuses to write one -- measured,
    # `put` answers `ValueError: Lazy loaded IDSs cannot be used in put or
    # put_slice.` -- so the command asks the entry for a whole copy.
    cached = session.view.dataSource.data_entries['%s/%d' % (PULSE, OCCURRENCE)]
    assert getattr(cached, '_lazy', False) is True
    assert getattr(loaded[0][2], '_lazy', False) is False
    assert loaded[0][2] is not cached
    # And it is the same occurrence of the same case, not another read of
    # something else: `event` is the array of structures this IDS is made of,
    # and the tree walked 135 elements of it.
    assert len(loaded[0][2].event) == len(cached.event) == 135


def test_two_open_ids_are_two_exported_ids_in_the_order_the_cache_answers(session):
    session.load(EQUILIBRIUM)

    assert session.cacheKeys() == ['%s/%d' % (EQUILIBRIUM, OCCURRENCE),
                                   '%s/%d' % (PULSE, OCCURRENCE)]
    assert len(session.view.signalsList) == BOTH_LEAVES
    assert [(name, occurrence) for name, occurrence, _
            in QVizExportToIDS(session.view).loadedIds()] == \
        [(EQUILIBRIUM, OCCURRENCE), (PULSE, OCCURRENCE)]
    # The version written is the one the case was opened at, and the loaded IDS
    # says the same number: two answers, no contradiction to resolve.
    loaded = QVizExportToIDS(session.view).loadedIds()
    assert QVizExportToIDS.dataDictionaryOf(session.view.dataSource,
                                            loaded) == CASE_DATA_DICTIONARY_VERSION


# --------------------------------------------------------------------------
# The round trip: what was written, opened again
# --------------------------------------------------------------------------

def test_the_written_case_holds_the_two_occurrences_that_were_open(session):
    writtenUri = session.exported()
    assert writtenUri == session.targetUri

    entry = openForReading(session)
    assert entry.list_all_occurrences(EQUILIBRIUM) == [OCCURRENCE]
    assert entry.list_all_occurrences(PULSE) == [OCCURRENCE]


def test_the_written_files_are_the_size_the_data_of_this_case_costs(session):
    files = {}
    directory = session.targetUri.split('path=', 1)[-1]
    for root, _, names in os.walk(directory):
        for name in names:
            files[os.path.relpath(os.path.join(root, name), directory)] = \
                os.path.getsize(os.path.join(root, name))

    assert sorted(files) == ['%s.h5' % EQUILIBRIUM, 'master.h5',
                             '%s.h5' % PULSE]
    assert files['master.h5'] == MASTER_BYTES
    # Bytes depend on the Access Layer's compressor; an IDS that came back empty
    # would not, which is what this guards.
    assert files['%s.h5' % EQUILIBRIUM] > EQUILIBRIUM_BYTES // 2, files
    assert files['%s.h5' % PULSE] > PULSE_BYTES // 2, files


def test_what_the_tree_keeps_is_not_what_the_export_writes(session):
    # Tree leaves and filled paths are two different units, so the honest
    # comparison here is slice against slice. The tree of this view keeps the
    # default view of a dynamic IDS: one time slice, spelled `time_slice[0]` on
    # every one of its 3 368 leaves. The cache holds the whole IDS, and so does
    # the case that was written -- which answers 49 slices for this case.
    entry = openForReading(session)
    written = {name: len(entry.list_filled_paths(name))
               for name in (EQUILIBRIUM, PULSE)}
    assert written == FILLED_PATHS, written

    assert len(leavesOf(session.view, EQUILIBRIUM)) == EQUILIBRIUM_LEAVES
    kept = treeSlices(session.view, EQUILIBRIUM)
    assert kept == ['%d' % OCCURRENCE], kept
    slices = len(entry.get(EQUILIBRIUM, OCCURRENCE).time)
    assert slices == TIME_SAMPLES
    # What the user sees is one slice of what the user exported.
    assert len(kept) < slices


def test_the_values_survive_being_written_and_read_back(session):
    entry = openForReading(session)
    ids = entry.get(EQUILIBRIUM, OCCURRENCE)

    assert ids.time_slice[0].global_quantities.ip == IP
    assert len(ids.time) == TIME_SAMPLES
    cached = session.view.dataSource.data_entries[
        '%s/%d' % (EQUILIBRIUM, OCCURRENCE)]
    assert list(ids.time) == list(cached.time)
    assert ids.ids_properties.version_put.data_dictionary == \
        CASE_DATA_DICTIONARY_VERSION


def test_the_target_of_another_major_version_is_refused_before_a_byte_is_written(session):
    otherMajor = os.path.join(os.path.dirname(
        os.path.dirname(session.targetUri.split('path=', 1)[-1])), '4',
        '54924', '0')

    with pytest.raises(ValueError, match='major version'):
        session.exported(target=QVizExportTarget(uri='imas:hdf5?path=' +
                                                 otherMajor,
                                                 dataVersion='4'))
    # Refused before the Access Layer was asked for an entry, so there is no
    # half-made case directory behind it.
    assert not os.path.exists(otherMajor)


def test_the_view_the_export_read_from_is_left_as_it_was(session):
    # Exporting neither re-reads the case nor empties what it read: the plots are
    # still holding the IDSs they drew from.
    assert session.cacheKeys() == ['%s/%d' % (EQUILIBRIUM, OCCURRENCE),
                                   '%s/%d' % (PULSE, OCCURRENCE)]
    assert session.view.loadedOccurrences(EQUILIBRIUM) == [OCCURRENCE]
    assert session.view.loadedOccurrences(PULSE) == [OCCURRENCE]
    assert len(session.view.signalsList) == BOTH_LEAVES


def test_the_target_the_dialog_starts_from_names_the_case_on_the_screen(session):
    """The prefill the manual describes, taken from a real source rather than a stub."""
    target = QVizExportTarget.fromCase(session.view.dataSource)

    assert (target.database, target.shot, target.run) == ('west', 54924, 0)
    assert target.dataVersion == CASE_DATA_DICTIONARY_VERSION
    # A case named by a path names no user, so the login stands in -- and the
    # URI the dialog would build is the user-form one, not the path on screen.
    assert target.user == os.environ.get('USER', '')
    assert target.uri() == ('imas:hdf5?user=%s;shot=54924;run=0;database=west;'
                            'version=3' % target.user)
