# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Opening a case at the data dictionary the case itself was written with.

The report was a load dying inside the walk, with the reason it should have
carried sitting one line above it in a different log:

    ERROR|'NoneType' object has no attribute 'metadata'
      File ".../QVizIDSViewParser.py", line 220, in run
      File ".../QVizIDSViewParser.py", line 283, in loadIDS
          self.rootMetaData = idsInstance.metadata

Measured on the reference case, offscreen, replaying the application's own
objects (`QVizIMASDataSource` then `QVizIDSViewParser.run`), the whole path came
out in order:

* an entry built from an URI with no `dd_version` settles on the version
  `IMAS_VERSION` names, or on the newest one the distribution bundles -- 4.1.1
  here with the variable unset;
* `DBEntry.get` then refuses, and **raises**: `RuntimeError: On-disk data is
  stored in DD 3.35.0 which has a different major version than the requested DD
  version (4.1.1)`. It answers that for every IDS of the case, while
  `list_all_occurrences` answers across a major version -- so the shot view is
  built, the IDS names are coloured as holding data, and only the loads die;
* `QVizIMASDataSource.get` wrapped the read in `except BaseException`, logged a
  bare `str(e)` into the log panel of the *session*, and returned **None** --
  caching that None under the `IDSName/occurrence` key, so the next ask did not
  even reach the Access Layer;
* `loadIDS` then died on `None.metadata`, and the walk's `AttributeError` branch
  added a diagnosis nothing supported: *the data dictionary of the data entry
  does not match the fields IMASViz expects*.

The case answers the version question itself, and cheaply: asking a filled IDS
for the `ids_properties/version_put/data_dictionary` node names, per occurrence,
the version its data was written with -- **0,41 s** for the four occurrences of
`equilibrium`, no IDS read. It can only be asked of an entry whose major already
matches, so the major is read off the URI (`version=3`, or the `<db>/<data
version>/<shot>/<run>` of a path case) and probed at the newest dictionary
bundled inside it. Pinned that way, the case needs no conversion and its tree is
the case's own: walking `equilibrium` occurrence 0 measured **3519 leaves** at
3.35.0 against **3594** at 3.42.2 -- 75 nodes the newest dictionary of the same
major would have added to a case written with an older one.

Measured here, in seconds: 0,10 s for the whole occurrence inventory of the
reference case, 0,41 s for the version node of one IDS, 4,14 s for the walk of
`equilibrium` at its own dictionary.
"""

import pytest
from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip)

from imasviz.VizDataSource.QVizIMASDataSource import (
    DD_VERSION_NODE, QVizIMASDataSource, candidateDDVersions, dataVersionFromUri)

PARAM_URI = ('imas:hdf5?user=g2lfleur;shot=54924;run=0;database=west'
             ';version=3')


@pytest.fixture(scope='module')
def case(qapp):
    """The reference case, by URI only: what is under test is opening it."""
    uri = case_uri_or_skip()
    if uri is None:
        pytest.skip('the reference case is not reachable')
    return {'uri': uri}


def _source(uri, ddVersion=None):
    source = QVizIMASDataSource('west 54924', uri)
    source.dd_version = ddVersion
    return source


class RecordingView:
    """Enough of a shot view for the parser to deliver to, or fail to."""

    def __init__(self):
        self.IDSNameSelected = {}
        self.delivered = []

    def updateView(self, idsName, idsInstance, occurrence, idsData, selection):
        self.delivered.append((idsName, occurrence))


def test_the_data_version_is_read_from_both_uri_spellings():
    # `caseUri` writes `version=3`; a case on disk lives under
    # <database>/<data version>/<shot>/<run>. Both spell the data version, and
    # only its major is ever asked of them.
    assert dataVersionFromUri(CASE_URI) == '3'
    assert dataVersionFromUri(PARAM_URI) == '3'
    assert dataVersionFromUri('imas:mdsplus?user=u;shot=1;run=0;database=d'
                              ';version=4') == '4'
    # An URI that spells nothing is not guessed at.
    assert dataVersionFromUri('imas:hdf5?user=u;shot=1') is None


def test_the_first_guess_lives_inside_the_major_the_uri_spells():
    from imas.dd_zip import dd_xml_versions
    from packaging.version import Version

    bundled = sorted(dd_xml_versions(), key=Version)
    newestOf = {}
    for version in bundled:
        newestOf[version.split('.')[0]] = version

    guesses = candidateDDVersions(CASE_URI)
    # The major the URI spells first -- IMAS-Python converts between minors of
    # one major -- then what an unpinned entry would have settled on anyway.
    assert guesses[0] == newestOf['3']
    assert guesses[-1] == bundled[-1]
    assert len(guesses) == 2
    # 35 versions are bundled (3.22.0 .. 4.1.1); the case's major is not the
    # newest of them, which is the whole reason this guess is needed.
    assert len(bundled) == 35
    assert newestOf['3'] != bundled[-1]


def test_the_version_node_is_spelled_the_way_the_access_layer_reads_it():
    # Measured: the node path is spelled with slashes. Dots answer
    # `ValueError: Invalid node name 'ids_properties.version_put...' in path`.
    assert DD_VERSION_NODE == 'ids_properties/version_put/data_dictionary'


@pytest.mark.case
@pytest.mark.dd
def test_an_unpinned_case_is_opened_at_the_dictionary_it_was_written_with(case):
    # The defect: unpinned, this case opens at 4.1.1 and every read is refused.
    source = _source(case['uri'])
    assert source.dd_version is None
    source.open()
    try:
        assert source.dd_version == CASE_DATA_DICTIONARY_VERSION
        assert source.db_entry.dd_version == CASE_DATA_DICTIONARY_VERSION
    finally:
        source.close()


@pytest.mark.case
@pytest.mark.dd
def test_an_explicit_pin_is_never_overruled(case):
    source = _source(case['uri'], CASE_DATA_DICTIONARY_VERSION)
    source.open()
    try:
        assert source.dd_version == CASE_DATA_DICTIONARY_VERSION
    finally:
        source.close()


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_the_roots_of_an_unpinned_case_come_from_the_case_own_dictionary(qtbot,
                                                                        case):
    from imasviz.VizGUI.VizTreeView.QVizDataTreeView import QVizDataTreeViewFrame
    from imasviz.VizUtils import QVizPreferences

    QVizPreferences().build()
    source = _source(case['uri'])
    frame = QVizDataTreeViewFrame(None, [], source, None)
    qtbot.addWidget(frame)
    view = frame.dataTreeView

    # 69 roots, the 3.35.0 count -- not the 82 of the newest bundled dictionary,
    # which is what an unpinned entry used to build a shot view from.
    assert source.dd_version == CASE_DATA_DICTIONARY_VERSION
    assert len(view.IDSRoots) == 69
    assert view.occurrencesOf('equilibrium') == [0, 1, 2, 3]


@pytest.mark.case
@pytest.mark.dd
def test_a_read_across_a_major_version_names_everything_it_refuses_on(case):
    # The pin is asked for by hand here, so the refusal the report met is the
    # state under test rather than something the discovery has to be trusted to
    # avoid.
    source = _source(case['uri'], '4.0.0')
    source.open()
    try:
        with pytest.raises(ValueError) as raised:
            source.get('equilibrium', 0)
        reason = str(raised.value)
        assert "Cannot read equilibrium occurrence 0" in reason
        assert 'opened at data dictionary 4.0.0' in reason
        assert 'DD 3.35.0' in reason
        assert 'different major version' in reason
    finally:
        source.close()


@pytest.mark.case
@pytest.mark.dd
def test_an_ids_the_case_does_not_hold_is_refused_by_name(case):
    # The case answers `[]` for `amns_data`, and the read answers
    # `DataEntryException: IDS 'amns_data', occurrence 0 is empty.` -- both had
    # been swallowed into a None that died further away.
    source = _source(case['uri'])
    source.open()
    try:
        assert source.db_entry.list_all_occurrences('amns_data') == []
        with pytest.raises(ValueError) as raised:
            source.get('amns_data', 0)
        assert "'amns_data'" in str(raised.value)
        assert 'empty' in str(raised.value)
    finally:
        source.close()


@pytest.mark.case
@pytest.mark.dd
def test_a_refused_read_is_not_left_in_place_of_the_answer(case):
    # The None used to be cached under `IDSName/occurrence`: the second ask
    # handed the same None out without asking the case again.
    source = _source(case['uri'], '4.0.0')
    source.open()
    try:
        for _ in range(2):
            with pytest.raises(ValueError) as raised:
                source.get('equilibrium', 0)
            assert 'different major version' in str(raised.value)
        assert 'equilibrium/0' not in source.data_entries
    finally:
        source.close()


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_the_walk_carries_the_refusal_and_invents_no_diagnosis(qtbot, case,
                                                              caplog):
    from imasviz.VizDataAccess.QVizIDSViewParser import QVizIDSViewParser

    source = _source(case['uri'], '4.0.0')
    view = RecordingView()
    parser = QVizIDSViewParser(case['uri'], view, 'equilibrium', 0, None, False)
    parser.dataSource = source

    with caplog.at_level('ERROR', logger=source.uri):
        parser.run()

    assert view.delivered == []
    assert 'Cannot read equilibrium occurrence 0' in caplog.text
    # The sentence this branch used to add, measured false in the case that
    # reached it.
    assert 'does not match the fields IMASViz expects' not in caplog.text
    # And it is the log of the case that carries it, not the session's panel.
    assert any(record.name == source.uri for record in caplog.records)


@pytest.mark.case
@pytest.mark.dd
def test_a_case_that_is_not_there_is_refused_with_the_access_layer_sentence(case):
    from conftest import CASE_URI

    missing = CASE_URI.replace('/54924/0', '/54924/9')
    source = _source(missing)
    with pytest.raises(ValueError) as raised:
        source.open()
    assert 'Cannot open' in str(raised.value)
    assert 'master.h5' in str(raised.value)
