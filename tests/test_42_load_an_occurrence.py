# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Loading one occurrence of one IDS, measured before and after.

The gestures under test are the double click, the Return key, "Get … data for
occurrence", "Add a new view" and Shift+right click. Everything below was
measured on the reference case (west 54924) before the change:

* which occurrences a case holds was asked of the data dictionary with
  `eval("imas." + idsName + "().getMaxOccurrences()")` at 5 places. On this
  IMAS-Python stack that attribute does not exist: every one of the 5 answers
  `AttributeError: module 'imas' has no attribute '<ids>'`, and the first sits
  above `containsData`'s own `try`, so **building the shot view of the reference
  case died on its first IDS** (`amns_data`) and no occurrence could be chosen
  at all;
* the shot view now builds in 1.22 s and asks the case for the occurrences of
  all its IDS names in 0.10 s, where reading each IDS to answer the same
  question costs 336 s;
* `loadDefaultOccurrence` with nothing selected answered `IndexError: list index
  out of range`;
* the slice choice travelled as one of the integers 1, 2, 3 and 4, an unrecognised
  name became 1 in silence, and `getLabel()` answered None for all four coming out
  of `getAllStrategies()` -- three views in four got no label, and the flag that
  made "Add a new view" reachable was raised only in the branch of the fourth;
* slice 49 of the 49 the reference `equilibrium` occurrence holds was refused
  four seconds later, from inside the walk, in a message naming neither the
  count nor the bound;
* the slice dialog had no parent and its spin box accepted anything up to
  2147483647 while only 0 to 48 are valid;
* the guard against loading one occurrence twice was a class attribute keyed by
  IDS name and shared by every shot view, and `__init__` wrote `Lock[IDSName] =
  False`: measured `{'equilibrium': True}` right after a load started, `{'equilibrium':
  False}` as soon as the next command object was built -- a double click never
  met a guard;
* the walk left its progress bar alive (`hide()`, never `close()`), and wrote a
  `limited_nodes` attribute on every array of structures that nothing ever read.
"""

import importlib.util

import pytest
from PySide6.QtWidgets import QMenu

from imas.ids_data_type import IDSDataType

from imasviz.VizDataSource.QVizCaseOccurrences import QVizCaseOccurrences
from imasviz.VizDataAccess.QVizIDSViewParser import QVizIDSViewParser
from imasviz.VizDataAccess.VizTimeSlices import (ALL_SLICES, FIRST_SLICE,
                                                 ONE_IN_TEN,
                                                 QVizTimeSliceSelection,
                                                 atIndex, dynamicArrayCount,
                                                 menuSelections)
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizOccurrenceMenu \
    import QVizOccurrenceMenu

from conftest import CASE_DATA_DICTIONARY_VERSION
from support.caseTrees import loadCaseTrees

REFERENCE_SLICES = 49


# --------------------------------------------------------------------------
# The four choices, as objects rather than as numbers
# --------------------------------------------------------------------------

def test_the_manuals_four_choices_are_listed_in_the_manuals_order():
    # The old menu listed the four names and mapped them to 3, 2, 1, 4, so the
    # menu order and the code order disagreed by construction.
    assert [choice.menuLabel() for choice in menuSelections()] == [
        'All time slices', 'One over 10 time slices',
        'Specific time slice only', 'First time slice only']


@pytest.mark.parametrize('choice, window', [
    (ALL_SLICES, (0, 49, 1)),
    (ONE_IN_TEN, (0, 49, 10)),
    (FIRST_SLICE, (0, 1, 1)),
    (atIndex(0), (0, 1, 1)),
    (atIndex(48), (48, 49, 1)),
])
def test_the_window_each_choice_keeps_out_of_49_slices(choice, window):
    assert choice.window(REFERENCE_SLICES) == window


def test_an_index_past_the_end_is_refused_before_the_walk():
    # Measured: the refusal came four seconds later, from inside the walk, and
    # named neither how many slices there are nor the bound that was crossed.
    with pytest.raises(ValueError) as refused:
        atIndex(REFERENCE_SLICES).window(REFERENCE_SLICES)

    assert str(refused.value) == (
        '49 is not a time slice of this IDS: it holds 49, so the index runs '
        'from 0 to 48.')


def test_the_choice_the_menu_offers_still_needs_a_number():
    assert atIndex(None).asksForAnIndex() is True
    for answered in (ALL_SLICES, ONE_IN_TEN, FIRST_SLICE, atIndex(3)):
        assert answered.asksForAnIndex() is False


def test_a_choice_never_asked_refuses_and_says_how_many_there_are():
    with pytest.raises(ValueError) as refused:
        atIndex(None).window(REFERENCE_SLICES)

    assert str(refused.value) == ('No time slice index was given: this IDS '
                                  'holds 49, so the index runs from 0 to 48.')


def test_the_first_slice_of_an_array_holding_nothing_keeps_nothing():
    # Measured on the reference case: `tf.time_slice` is empty and asking for
    # slice 0 of it invented 11 nodes of the 77 in that IDS's tree, where the
    # walk kept none.
    assert FIRST_SLICE.window(0) == (0, 0, 1)


@pytest.mark.parametrize('choice, label', [
    (ALL_SLICES, 'displaying all time slices'),
    (ONE_IN_TEN, 'displaying one over 10 time slices'),
    (atIndex(7), 'displaying time slice with index=7'),
    (FIRST_SLICE, 'displaying first time slice'),
])
def test_every_choice_names_the_view_it_heads(choice, label):
    # Measured: `getLabel()` answered None for all four coming out of
    # `getAllStrategies()`, because the flag it checked was raised only in the
    # branch of the fourth choice.
    assert choice.viewLabel() == label


def test_nothing_about_a_choice_travels_as_an_integer():
    strategies = importlib.import_module('imasviz.VizDataAccess.VizTimeSlices'
                                         '.QVizTimeSliceSelection')
    for name in ('getLoadingStrategyIdentifier', 'getAllStrategies',
                 'setIdentifier', 'identifier'):
        assert not hasattr(strategies, name), name

    for choice in menuSelections():
        assert isinstance(choice, QVizTimeSliceSelection)
        assert not hasattr(choice, 'getIdentifier')
        assert not hasattr(choice, 'identifier')


@pytest.mark.parametrize('gone', [
    'imasviz.VizGUI.VizTreeView.QVizViewLoadingStrategy',
    'imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizLoadDataHandling',
    'imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadSelectedData',
])
def test_the_modules_that_asked_these_questions_are_gone(gone):
    assert importlib.util.find_spec(gone) is None


# --------------------------------------------------------------------------
# The stubs the command, the menus and the walk are driven through
# --------------------------------------------------------------------------

class StubEntry:
    """A case that names the occurrences it holds, or refuses the question."""

    def __init__(self, table=None, refuses=()):
        self.table = table if table is not None else {'equilibrium': [0, 1, 2, 3]}
        self.refuses = list(refuses)
        self.asked = []

    def list_all_occurrences(self, idsName):
        self.asked.append(idsName)
        if idsName in self.refuses:
            raise RuntimeError('backend failure listing %s' % idsName)
        return self.table.get(idsName, [])


class StubSource:
    """What a load is asked of: records the request, never walks anything."""

    def __init__(self, entry=None):
        self.entry = entry if entry is not None else StubEntry()
        self.loads = []

    @property
    def db_entry(self):
        return self.entry

    def load(self, dataTreeView, IDSName, occurrence, sliceSelection, asynch):
        self.loads.append((IDSName, occurrence, sliceSelection, asynch))
        dataTreeView.beginLoad(IDSName, occurrence)


class StubView:
    """Enough of the shot view to own a load and to fill both menus."""

    def __init__(self, source=None, uri='imas:hdf5?path=/stub/3/1/0',
                 loaded=(), idsInstance=None):
        self.uri = uri
        self.dataSource = source if source is not None else StubSource()
        self.occurrences = QVizCaseOccurrences(self.dataSource)
        self.selectedItem = None
        # The parser writes what it is about to walk here before it walks it.
        self.IDSNameSelected = {}
        self.loadsInProgress = set()
        self.loaded = list(loaded)
        self.idsInstance = idsInstance

    def loadedOccurrences(self, idsName):
        return list(self.loaded)

    def loadedIds(self, idsName):
        return self.idsInstance

    def isLoadInFlight(self, idsName, occurrence):
        return (idsName, occurrence) in self.loadsInProgress

    def beginLoad(self, idsName, occurrence):
        self.loadsInProgress.add((idsName, occurrence))

    def endLoad(self, idsName, occurrence):
        self.loadsInProgress.discard((idsName, occurrence))


class StubRoot:
    """The IDS root of the empty shot view, or the entry of one on screen."""

    def __init__(self, idsName='equilibrium', occurrence=0, view=None):
        self.idsName = idsName
        self.occurrence = occurrence
        self.view = view

    def getIDSName(self):
        return self.idsName

    def getOccurrence(self):
        return self.occurrence

    def getDataTreeView(self):
        return self.view


# --------------------------------------------------------------------------
# What the opened case answers
# --------------------------------------------------------------------------

def test_the_occurrences_come_back_ascending_and_as_numbers():
    entry = StubEntry({'equilibrium': ['3', 1, 2, 0]})
    assert QVizCaseOccurrences(StubSource(entry)).occurrencesOf(
        'equilibrium') == [0, 1, 2, 3]


def test_a_case_that_refuses_the_question_is_said_as_a_sentence():
    # Measured: the old question raised AttributeError out of the loop that
    # builds the shot view, so one IDS decided what the other 54 looked like --
    # they were not built at all.
    occurrences = QVizCaseOccurrences(StubSource(StubEntry(refuses=['amns_data'])))

    with pytest.raises(ValueError) as refused:
        occurrences.occurrencesOf('amns_data')

    assert str(refused.value) == ("Cannot ask the case for the occurrences of "
                                  "'amns_data': RuntimeError: backend failure "
                                  "listing amns_data")


def test_the_occurrences_still_to_load_are_the_ones_not_on_screen():
    occurrences = QVizCaseOccurrences(StubSource())

    assert occurrences.unloaded('equilibrium', [0, 1]) == [2, 3]
    assert occurrences.nextUnloaded('equilibrium', [0, 1]) == 2
    assert occurrences.nextUnloaded('equilibrium', [0, 1, 2, 3]) is None
    assert occurrences.holdsIds('equilibrium') is True
    assert occurrences.holdsIds('nothing') is False


# --------------------------------------------------------------------------
# The one command between a gesture and the walk
# --------------------------------------------------------------------------

def test_the_choice_reaches_the_walk_as_the_object_it_is():
    view = StubView()

    QVizLoadOccurrence(dataTreeView=view, idsName='equilibrium', occurrence=2,
                       sliceSelection=ONE_IN_TEN).execute()

    assert view.dataSource.loads == [('equilibrium', 2, ONE_IN_TEN, True)]


def test_a_plain_load_keeps_the_first_slice():
    view = StubView()

    QVizLoadOccurrence(dataTreeView=view, idsName='equilibrium').execute()

    assert view.dataSource.loads == [('equilibrium', 0, FIRST_SLICE, True)]


def test_a_choice_that_still_needs_a_number_is_refused_rather_than_asked():
    # A dialog opened from a command would appear in the middle of a script;
    # measured, the old command opened one whatever the caller was.
    view = StubView()

    with pytest.raises(ValueError) as refused:
        QVizLoadOccurrence(dataTreeView=view, idsName='equilibrium',
                           sliceSelection=atIndex(None)).execute()

    assert str(refused.value) == ('No time slice index was given for occurrence '
                                  '0 of the equilibrium IDS: the menu asks the '
                                  'user for one, a script has to name it.')
    assert view.dataSource.loads == []


def test_the_same_occurrence_is_not_loaded_twice_in_one_view(caplog):
    view = StubView()
    QVizLoadOccurrence(dataTreeView=view, idsName='equilibrium').execute()
    assert view.isLoadInFlight('equilibrium', 0) is True

    with caplog.at_level('INFO', logger=view.uri):
        QVizLoadOccurrence(dataTreeView=view, idsName='equilibrium').execute()

    assert view.dataSource.loads == [('equilibrium', 0, FIRST_SLICE, True)]
    assert ('Occurrence 0 of the equilibrium IDS is already being loaded in '
            'this view: this request is ignored.') in caplog.text


def test_another_view_is_free_to_load_the_same_occurrence():
    # Measured: the guard was a class attribute keyed by IDS name, so loading
    # equilibrium in one shot view blocked the other -- and it was rewritten to
    # False by the next command object before anything was asked of the case.
    source = StubSource()
    first = StubView(source)
    second = StubView(source)
    QVizLoadOccurrence(dataTreeView=first, idsName='equilibrium').execute()

    QVizLoadOccurrence(dataTreeView=second, idsName='equilibrium').execute()

    assert len(source.loads) == 2
    assert second.isLoadInFlight('equilibrium', 0) is True


def test_the_guard_lives_on_the_view_and_not_on_the_command():
    assert not hasattr(QVizLoadOccurrence, 'Lock')


# --------------------------------------------------------------------------
# The two sub-menus
# --------------------------------------------------------------------------

@pytest.mark.ui
def test_one_entry_per_occurrence_the_case_holds_and_the_view_has_not_shown(qapp):
    view = StubView(loaded=[0])
    menu = QMenu()

    QVizOccurrenceMenu().buildOccurrencesMenu(StubRoot(), view, menu)

    assert [action.text() for action in menu.actions()] == [
        'Occurrence 1', 'Occurrence 2', 'Occurrence 3']

    menu.actions()[0].trigger()
    assert view.dataSource.loads == [('equilibrium', 1, FIRST_SLICE, True)]


@pytest.mark.ui
def test_a_view_showing_every_occurrence_says_so_instead_of_nothing(qapp):
    view = StubView(loaded=[0, 1, 2, 3])
    menu = QMenu()

    QVizOccurrenceMenu().buildOccurrencesMenu(StubRoot(), view, menu)

    assert [action.text() for action in menu.actions()] == [
        'all occurrences of equilibrium are already displayed']
    assert menu.actions()[0].isEnabled() is False


@pytest.mark.ui
def test_the_views_menu_lists_the_four_choices(qapp):
    view = StubView(loaded=[0])
    menu = QMenu()

    QVizOccurrenceMenu().buildViewsMenu(StubRoot(occurrence=0, view=view), view,
                                        menu)

    assert [action.text() for action in menu.actions()] == [
        'All time slices', 'One over 10 time slices',
        'Specific time slice only', 'First time slice only']

    menu.actions()[1].trigger()
    assert view.dataSource.loads == [('equilibrium', 0, ONE_IN_TEN, True)]


class StubDialog:
    """The slice question, recorded instead of asked."""

    asked = []
    answer = (7, True)

    def __init__(self, parent=None):
        self.parent = parent

    @staticmethod
    def getInt(parent, title, label, value, minimum, maximum):
        StubDialog.asked.append((parent, title, label, value, minimum, maximum))
        return StubDialog.answer


@pytest.fixture
def askedThrough(qapp, monkeypatch):
    # `from ...VizMenusManagement import QVizOccurrenceMenu` answers the class:
    # the package's `import *` rebinds that name over the module. Ask for the
    # module itself to put the dialog stub where the code looks it up.
    menuModule = importlib.import_module(
        'imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizOccurrenceMenu')
    StubDialog.asked = []
    StubDialog.answer = (7, True)
    monkeypatch.setattr(menuModule, 'QInputDialog', StubDialog)
    return StubDialog


def test_the_slice_question_belongs_to_the_view_that_asks_it(askedThrough):
    # Measured: `QInputDialog()` with no parent, `getInt(None, ...)`, and a spin
    # box accepting up to 2147483647 while the occurrence in memory holds 49.
    view = StubView(loaded=[0], idsInstance=_LoadedIds(REFERENCE_SLICES))

    assert QVizOccurrenceMenu.askTimeSliceIndex(view, 'equilibrium') == 7
    assert askedThrough.asked == [(view, 'Add a view of the equilibrium IDS',
                                   'Time slice index:', 0, 0, 48)]


def test_the_question_stays_open_while_the_number_is_unknown(askedThrough):
    view = StubView()
    QVizOccurrenceMenu.askTimeSliceIndex(view, 'equilibrium')

    assert askedThrough.asked[0][5] == QVizTimeSliceSelection.LARGEST_INDEX


def test_declining_the_question_adds_no_view_and_says_so(askedThrough, caplog):
    askedThrough.answer = (0, False)
    view = StubView(loaded=[0])

    with caplog.at_level('INFO', logger=view.uri):
        QVizOccurrenceMenu().loadOccurrence(view, 'equilibrium', 0,
                                            atIndex(None))

    assert view.dataSource.loads == []
    assert ('No time slice index was given: occurrence 0 of the equilibrium '
            'IDS is displayed as it is, no new view was added.' in caplog.text)


def test_an_answered_question_loads_the_slice_it_names(askedThrough):
    askedThrough.answer = (12, True)
    view = StubView(loaded=[0])

    QVizOccurrenceMenu().loadOccurrence(view, 'equilibrium', 0, atIndex(None))

    assert len(view.dataSource.loads) == 1
    assert view.dataSource.loads[0][:2] == ('equilibrium', 0)
    assert view.dataSource.loads[0][2].window(REFERENCE_SLICES) == (12, 13, 1)


class _LoadedIds:
    """The one question `dynamicArrayCount` asks of a loaded IDS instance."""

    class _Type:
        def __init__(self, isDynamic):
            self.is_dynamic = isDynamic

    class _Meta:
        def __init__(self, name, isDynamic=True):
            self.name = name
            self.data_type = IDSDataType.STRUCT_ARRAY
            self.type = _LoadedIds._Type(isDynamic)

    def __init__(self, slices):
        # equilibrium occurrence 0 on the reference case: 49 time slices and 1
        # grids_ggd, and the narrow one is the first the dictionary lists.
        self.metadata = [self._Meta('grids_ggd'), self._Meta('time_slice')]
        self.grids_ggd = [None]
        self.time_slice = list(range(slices))


# --------------------------------------------------------------------------
# What the walk does with the choice
# --------------------------------------------------------------------------

class StubMeta:
    def __init__(self, name, isDynamic):
        self.name = name
        self.type = type('_T', (), {'is_dynamic': isDynamic})()


def _parser(sliceSelection):
    return QVizIDSViewParser('imas:hdf5?path=/stub/3/1/0', StubView(),
                             'equilibrium', 0, sliceSelection, False)


def test_the_walk_asks_the_choice_for_its_window_and_records_the_array():
    asked = []
    choice = type('Choice', (), {'window': lambda self, length:
                                 asked.append(length) or (2, 5, 1)})()
    parser = _parser(choice)

    assert parser.slicing(StubMeta('time_slice', True), 49) == (2, 5, 1)
    assert asked == [49]
    assert parser.sawDynamicArrays is True


def test_a_static_array_is_walked_whole_and_unchosen():
    parser = _parser(ONE_IN_TEN)

    assert parser.slicing(StubMeta('coil', False), 3) == (0, 3, 1)
    assert parser.sawDynamicArrays is False


def test_the_default_choice_is_the_first_slice_of_what_is_there():
    parser = _parser(None)

    assert parser.slicing(StubMeta('time_slice', True), 49) == (0, 1, 1)


def test_the_refusal_names_the_array_it_cannot_take():
    # One index serves every dynamic array of the IDS, and equilibrium holds
    # time_slice (49) as well as grids_ggd (1) -- measured.
    parser = _parser(atIndex(30))

    with pytest.raises(ValueError) as refused:
        parser.slicing(StubMeta('grids_ggd', True), 1)

    assert str(refused.value) == ('grids_ggd: 30 is not a time slice of this '
                                  'IDS: it holds 1, so the index runs from 0 '
                                  'to 0.')


def test_the_progress_bar_of_a_walk_is_taken_down_not_hidden():
    closed = []

    class Bar:
        def close(self):
            closed.append('close')

        def hide(self):
            closed.append('hide')

    parser = _parser(FIRST_SLICE)
    parser.setProgressBar(Bar())
    parser.closeProgressBar()

    assert closed == ['close']


# --------------------------------------------------------------------------
# The reference case
# --------------------------------------------------------------------------

class WalkingView(StubView):
    """A view the parser delivers to, recording what reached it."""

    def __init__(self, uri):
        StubView.__init__(self, uri=uri)
        self.roots = {}
        self.built = []

    def updateView(self, idsName, idsInstance, occurrence, idsData, selection):
        self.roots[(idsName, occurrence)] = idsData
        self.built.append(selection)


def _source(uri, ddVersion):
    from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
    source = QVizIMASDataSource('west 54924', uri)
    source.dd_version = ddVersion
    return source


@pytest.fixture(scope='module')
def case(qapp, request):
    return loadCaseTrees(qapp, ('equilibrium', 'tf'), request=request)


@pytest.mark.case
def test_the_widest_dynamic_array_bounds_the_question(case):
    # equilibrium: time_slice 49 and grids_ggd 1 -- the first one found is the
    # narrow one, which used to bound the question at 0.
    assert dynamicArrayCount(case['runtime']['equilibrium']) == REFERENCE_SLICES
    assert dynamicArrayCount(case['runtime']['tf']) == 0
    assert dynamicArrayCount(None) is None


@pytest.mark.case
def test_the_walk_says_whether_it_met_a_dynamic_array(case):
    assert case['trees']['equilibrium'].get('dynamic_arrays') == '1'
    assert case['trees']['tf'].get('dynamic_arrays') == '1'


@pytest.mark.case
def test_the_walk_no_longer_writes_an_attribute_nothing_reads(case):
    for trees in case['trees'].values():
        assert not [element for element in trees.iter()
                    if 'limited_nodes' in element.attrib]


@pytest.mark.case
@pytest.mark.ui
def test_a_walk_refusing_an_index_says_so_and_loads_nothing(qtbot, case):
    from conftest import CASE_DATA_DICTIONARY_VERSION
    view = WalkingView(case['uri'])
    parser = QVizIDSViewParser(case['uri'], view, 'equilibrium', 0,
                               atIndex(REFERENCE_SLICES), False)
    parser.dataSource = _source(case['uri'], CASE_DATA_DICTIONARY_VERSION)
    closed = []
    parser.setProgressBar(type('Bar', (),
                               {'close': lambda self: closed.append('close'),
                                'hide': lambda self: closed.append('hide')})())

    parser.run()

    assert view.roots == {}
    assert closed == ['close']


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_the_refusal_the_walk_answers_with_names_the_count(qtbot, case, caplog):
    from conftest import CASE_DATA_DICTIONARY_VERSION
    view = WalkingView(case['uri'])
    parser = QVizIDSViewParser(case['uri'], view, 'equilibrium', 0,
                               atIndex(REFERENCE_SLICES), False)
    parser.dataSource = _source(case['uri'], CASE_DATA_DICTIONARY_VERSION)
    logger = 'imasviz.VizDataAccess.QVizIDSViewParser'

    with caplog.at_level('ERROR', logger=parser.dataSource.uri):
        parser.run()

    assert ('time_slice: 49 is not a time slice of this IDS: it holds 49, so '
            'the index runs from 0 to 48.') in caplog.text


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_a_shot_view_of_the_reference_case_is_built(qtbot, case):
    # Measured before: this raised on the first IDS of the list (amns_data) and
    # no shot view existed at all.
    from imasviz.VizGUI.VizTreeView.QVizDataTreeView import QVizDataTreeViewFrame
    from imasviz.VizUtils import QVizPreferences
    from conftest import CASE_DATA_DICTIONARY_VERSION

    QVizPreferences().build()
    frame = QVizDataTreeViewFrame(None, [],
                                  _source(case['uri'],
                                          CASE_DATA_DICTIONARY_VERSION),
                                  None)
    qtbot.addWidget(frame)
    view = frame.dataTreeView

    # The roots are the IDS names of the dictionary the entry is open at (3.35.0
    # for this case), not the 55 of a file named by IMAS_VERSION: measured, the
    # entry declares 3.35.0 and its factory enumerates 69 names, while the 3.23.3
    # file the harness used to point at holds 55 -- two of them (ec_antennas,
    # sdn) gone by 3.35.0, sixteen added.
    assert len(view.IDSRoots) == 69
    assert view.occurrencesOf('equilibrium') == [0, 1, 2, 3]
    assert view.occurrencesOf('core_sources') == []
    assert view.IDSRoots['equilibrium'].hasAvailableData() is True
    assert view.IDSRoots['core_sources'].hasAvailableData() is False

    menu = QMenu()
    QVizOccurrenceMenu().buildOccurrencesMenu(view.IDSRoots['equilibrium'],
                                              view, menu)
    assert [action.text() for action in menu.actions()] == [
        'Occurrence 0', 'Occurrence 1', 'Occurrence 2', 'Occurrence 3']


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_the_roots_are_the_names_the_entry_declares(qtbot, case):
    # What the roots are is answered by the case, not by a file the environment
    # names: the entry says the dictionary it is open at, and that entry's own
    # factory enumerates it. Measured on the reference case: `dd_version` answers
    # '3.35.0', `IDSFactory('3.35.0').ids_names()` gives 69 names in 0.000 s
    # (cached after the parse), and reading all 69 documentations through
    # `IDSFactory.new(name).metadata` costs 0.401 s and answers a non-empty
    # string for every one of them.
    import imas

    from imasviz.VizGUI.VizTreeView.QVizDataTreeView import QVizDataTreeViewFrame
    from imasviz.VizUtils import QVizPreferences
    from conftest import CASE_DATA_DICTIONARY_VERSION

    QVizPreferences().build()
    source = _source(case['uri'], CASE_DATA_DICTIONARY_VERSION)
    frame = QVizDataTreeViewFrame(None, [], source, None)
    qtbot.addWidget(frame)
    view = frame.dataTreeView

    assert source.db_entry.dd_version == CASE_DATA_DICTIONARY_VERSION
    names = imas.IDSFactory(source.db_entry.dd_version).ids_names()
    assert sorted(view.IDSRoots) == sorted(names)

    equilibrium = view.IDSRoots['equilibrium']
    assert equilibrium.getDocumentation().startswith(
        'Description of a 2D, axi-symmetric, tokamak equilibrium')
    assert [name for name, root in view.IDSRoots.items()
            if not root.getDocumentation()] == []


@pytest.mark.case
@pytest.mark.dd
def test_a_dictionary_the_package_does_not_hold_is_refused_by_name(case):
    # The path the shot view used to build named IDSDef_<IMAS_VERSION>.xml, and
    # IMAS_VERSION was the Access Layer's own number on any stack that exports
    # AL_VERSION: 5.7.1 here, which is not one of the 35 dictionaries the
    # distribution bundles (3.22.0 through 4.1.1). The old failure was therefore
    # `[Errno 2] No such file or directory: .../IDSDef_5.7.1.xml`, raised as a
    # FileNotFoundError outside the gesture that opened the pulse. Now the entry
    # itself refuses, naming the version: UnknownDDVersion, a ValueError.
    from imasviz.VizGUI.VizTreeView.QVizDataTreeView import QVizDataTreeViewFrame
    from imasviz.VizUtils import QVizPreferences

    QVizPreferences().build()
    with pytest.raises(ValueError) as refusal:
        QVizDataTreeViewFrame(None, [], _source(case['uri'], '5.7.1'), None)

    assert '5.7.1' in str(refusal.value)


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_the_occurrences_the_scripting_api_asks_for_answer(qtbot, case):
    from imasviz.Viz_API import Viz_API
    from imasviz.VizGUI.VizTreeView.QVizDataTreeView import QVizDataTreeViewFrame
    from imasviz.VizUtils import QVizPreferences
    from conftest import CASE_DATA_DICTIONARY_VERSION

    QVizPreferences().build()
    frame = QVizDataTreeViewFrame(None, [],
                                  _source(case['uri'],
                                          CASE_DATA_DICTIONARY_VERSION),
                                  None)
    qtbot.addWidget(frame)
    view = frame.dataTreeView
    api = Viz_API()
    root = view.IDSRoots['magnetics']

    # Measured: all three answered AttributeError on this IMAS stack, and the
    # guard under them (`if availableOccurrences is None`) was dead code.
    assert api.GetAllOccurrencesWithAvailableData(root) == [0, 1]
    assert api.GetAllOccurrencesUnloadedWithAvailableData(view, root) == [0, 1]
    assert api.GetNextOccurrenceUnloadedWithAvailableData(view, root) == 0
    assert api.GetNextOccurrenceUnloadedWithAvailableData(view, root) == 0


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_an_occurrence_loaded_with_the_default_choice_is_marked_dynamic(qtbot,
                                                                        case):
    # Measured: the flag that makes "Add a new view" reachable was raised only
    # in the branch of the fourth choice, so a view built with the default one
    # could never be looked at another way.
    from imasviz.VizGUI.VizTreeView.QVizDataTreeView import QVizDataTreeViewFrame
    from imasviz.VizUtils import QVizPreferences
    from conftest import CASE_DATA_DICTIONARY_VERSION

    QVizPreferences().build()
    source = _source(case['uri'], CASE_DATA_DICTIONARY_VERSION)
    frame = QVizDataTreeViewFrame(None, [], source, None)
    qtbot.addWidget(frame)
    view = frame.dataTreeView

    QVizLoadOccurrence(dataTreeView=view, idsName='equilibrium', occurrence=0,
                       asynch=False).execute()

    entry = view.ids_roots_occurrence['equilibrium/0']
    assert entry.text(0) == 'occurrence 0 [displaying first time slice]'
    assert entry.isIDSDynamic() is True
    assert entry.getHomogeneousTime() == 0
    assert entry.hasHomogeneousTime() is False
    assert view.loadedOccurrences('equilibrium') == [0]
    assert view.loadsInProgress == set()
    assert source.runningParsers == set()


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_the_double_click_delivers_its_view_through_the_event_loop(qtbot, case):
    from imasviz.VizGUI.VizTreeView.QVizDataTreeView import QVizDataTreeViewFrame
    from imasviz.VizUtils import QVizPreferences
    from conftest import CASE_DATA_DICTIONARY_VERSION

    QVizPreferences().build()
    source = _source(case['uri'], CASE_DATA_DICTIONARY_VERSION)
    frame = QVizDataTreeViewFrame(None, [], source, None)
    qtbot.addWidget(frame)
    view = frame.dataTreeView

    # Measured: the walk used to run in a thread of its own while updateView
    # waited on a condition, and built the items in a thread that does not own
    # the widget ('Dummy-1' while the main thread sat in cv.wait()).
    view.setCurrentItem(view.IDSRoots['magnetics'])
    assert [item.text(0) for item in view.selectedItems()] == ['magnetics']
    view.loadDefaultOccurrence()

    assert view.isLoadInFlight('magnetics', 0) is True
    assert len(source.runningParsers) == 1
    qtbot.waitUntil(lambda: 'magnetics/0' in view.ids_roots_occurrence,
                    timeout=60000)
    qtbot.waitUntil(lambda: not source.runningParsers, timeout=60000)
    assert view.loadsInProgress == set()
    assert (view.ids_roots_occurrence['magnetics/0'].text(0)
            == 'occurrence 0 [displaying first time slice]')


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_a_double_click_with_nothing_selected_loads_nothing(qtbot, case, caplog):
    from imasviz.VizGUI.VizTreeView.QVizDataTreeView import QVizDataTreeViewFrame
    from imasviz.VizUtils import QVizPreferences
    from conftest import CASE_DATA_DICTIONARY_VERSION

    QVizPreferences().build()
    frame = QVizDataTreeViewFrame(None, [],
                                  _source(case['uri'],
                                          CASE_DATA_DICTIONARY_VERSION),
                                  None)
    qtbot.addWidget(frame)
    view = frame.dataTreeView
    view.clearSelection()

    # Measured: IndexError: list index out of range.
    with caplog.at_level('INFO', logger=view.uri):
        view.loadDefaultOccurrence()

    assert view.ids_roots_occurrence == {}
    assert ('Nothing is selected in the shot view: no occurrence to load.'
            in caplog.text)
