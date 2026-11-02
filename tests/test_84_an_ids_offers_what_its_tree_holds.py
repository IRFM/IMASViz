# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What one IDS of one case can be plotted as, derived from the tree it holds.

The Profiles plugin used to be **told** what to draw. Its own file carried, for
each of five IDS names, the array of structures to slice, the paths to keep and
the label of each tab -- about a hundred and twenty literals -- so an IDS with no
list had no tab to open and the sixth IDS had to be written by hand before anyone
could look at it. `QVizProfileOffer` answers the same questions off the tree this
shot view already built, for every IDS the case holds. This file pins the answers
it owes the panel before the panel is rebuilt on them.

Two of those answers were defects while they were written by hand, and both are
pinned here on stubs so the shape is refused whatever the case holds:

* **The group is the array that drives the quantity, not the innermost one.** The
  tree spells `equilibrium.time_slice[itime].constraints.bpol_probe[j].measured`
  with both arrays in the path. Asked for the innermost, that quantity answers
  `bpol_probe` and lands in the family with no time base, so no slider moves it.
  Measured on the reference case, 2 310 of the 3 368 plottable leaves of
  `equilibrium` occurrence 0 would have answered under an array no tab names.
* **One page window, spelled once.** The panel laid panels out in two places, each
  with its own arithmetic, and the two disagreed as soon as more than one page was
  added at a time: `start = tab * 100 + last_index` restarts from the tab number
  while `last_index` already counts the panels laid. It answers correctly only
  while exactly one tab is added at a time -- which is why ten years of this case
  (41 quantities, one page) never showed it. `pages()` is the window, and the
  tests below run it over 250 quantities, a shape no test ever reached.

What the reference case answers, measured with the GGD walk off and the rank
filter off, and pinned below: `equilibrium` occurrence 0 gives **10 groups in
0,04 s** over **191 quantities** (3 368 plottable leaves answering 727 quantities,
**536** of them error fields left out); `magnetics` occurrence 0 -- an IDS the
plugin never named -- gives **4 groups** (`flux_loop` 7, `bpol_probe` 10, `method`
2, no array 2) and answers **no time group at all**, because this case writes that
IDS with `homogeneous_time = 1`: its clock is a coordinate of each quantity, not
the index of a dynamic array, so there is no slice to move.

The unit of those counts is a **quantity**, not a tree node, and that is a third
thing this file refuses. The tree keeps one node per element of a *static* array of
structures: the `magnetics.bpol_probe` of this case is 130 probes holding 10
quantities, so the walk meets 1 300 leaves. A panel per leaf would draw the same
curve 130 times, one per probe, while the rule of a plot entry is that it draws an
*element* pinned to the index its node carries -- so the index is a control (the
panel's, in the next step) and the group answers `elementsOf` to say how far that
control reaches.
"""

import time

import pytest

from PySide6.QtWidgets import QMainWindow, QMdiArea

from imasviz.VizDataAccess.QVizCurveAbscissa import TIME, choose
from imasviz.VizDataAccess.QVizNodePlotting import QVizNodePlotting
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizMainMenuController \
    import QVizMainMenuController
from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizProfileOffer import \
    PAGE, QVizProfileOffer
from imasviz.VizUtils import QVizPreferences

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip)
from support import ownership

pytestmark = [pytest.mark.case, pytest.mark.dd, pytest.mark.ui]

IDS = 'equilibrium'

# What the case answers for equilibrium occurrence 0: (title, a time base moves
# it, how many quantities). Measured; the seven the hand-written lists spelled are
# in it, plus the two separatrices those lists left out.
EQUILIBRIUM_GROUPS = [
    ('no array of structures', False, 3),
    ('time_slice/boundary', True, 27),
    ('time_slice/boundary_separatrix', True, 28),
    ('time_slice/boundary_secondary_separatrix', True, 4),
    ('time_slice/constraints', True, 30),
    ('time_slice/global_quantities', True, 26),
    ('time_slice/profiles_1d', True, 50),
    ('time_slice/coordinate_system', True, 21),
    ('time_slice/convergence', True, 1),
    ('time_slice', True, 1),
]
EQUILIBRIUM_KEPT = sum(count for _t, _time, count in EQUILIBRIUM_GROUPS)
# 3 368 plottable leaves answer 727 quantities, and 536 of them are error fields.
EQUILIBRIUM_ERRORS = 536
EQUILIBRIUM_WITH_ERRORS = 727

# magnetics, which no list in the plugin ever named.
MAGNETICS_GROUPS = [('flux_loop', False, 7), ('bpol_probe', False, 10),
                    ('method', False, 2), ('no array of structures', False, 2)]
# How many elements of its array the tree holds for one quantity of these groups.
MAGNETICS_ELEMENTS = {'flux_loop': 17, 'bpol_probe': 130}
CONSTRAINTS_ELEMENTS = [1, 17, 110]


# --------------------------------------------------------------------------
# The stubs: a tree of the shape the builder leaves, and a view holding it.
# --------------------------------------------------------------------------

def makeLeaf(name, dataType='FLT_1D', path='time_slice[itime].profiles_1d',
             coordinates=('rho_tor_norm',), itimeIndex=0, aosCount=1,
             indices=None, lengths=None, idsName=IDS):
    """One quantity, as the tree builder leaves it (see test_31 for the recipe).

    The enclosing arrays are in the parametrized path and in the count, exactly as
    the view writes them, because that is the spelling the axes model reads.
    """
    infoDict = {'IDSName': idsName, 'name': name, 'dataName': name,
                'data_type': dataType, 'occurrence': 0, 'isSignal': 1,
                'isStatic': 0, 'isSelected': 0, 'availableData': 1,
                'aos_parents_count': str(aosCount),
                'Path': path + '.' + name if path else name}
    node = QVizTreeNode(None, [name], infoDict)
    node.parametrizedPath = path
    node.itime_index = itimeIndex if path else None
    node.aos_parents_count = str(aosCount)
    node.coordinates = list(coordinates)
    node.parameters_values = dict(indices or {})
    node.parameters_max_values = dict(lengths or {})
    return node


class FakeBranch:
    """A structure or an array of structures, reduced to what the walk asks."""

    def __init__(self, *children, **kind):
        self.children = list(children)
        self.kind = kind.get('kind', 'structure')

    def childCount(self):
        return len(self.children)

    def child(self, row):
        return self.children[row]

    def isIDSRoot(self):
        return self.kind == 'ids'

    def isStructure(self):
        return self.kind == 'structure'

    def isArrayOfStructure(self):
        return self.kind == 'aos'


def makeView(root, idsName=IDS, occurrence=0, filterOn=None):
    """A shot view holding one built occurrence, and the filter flag."""
    view = type('FakeView', (), {'uri': 'imas:hdf5?case=1'})()
    view.ids_roots_occurrence = {'%s/%s' % (idsName, occurrence): root}
    if filterOn is not None:
        view.showOnlyTensorsRankGe1 = filterOn
    return view


def offerOf(*leaves, **kw):
    """An offer over a stub tree, asked under the IDS name the leaves carry."""
    idsName = kw.pop('idsName', IDS)
    occurrence = kw.pop('occurrence', 0)
    view = makeView(FakeBranch(*leaves, kind='ids'), idsName=idsName,
                    occurrence=occurrence, filterOn=kw.pop('filterOn', None))
    return QVizProfileOffer(view, idsName, occurrence,
                            withErrors=kw.pop('withErrors', False))


def titles(offer):
    return [(group.title(), group.alongTime, len(group.leaves))
            for group in offer.groups()]


# --------------------------------------------------------------------------
# What a group is
# --------------------------------------------------------------------------

def test_a_quantity_of_the_dynamic_array_groups_under_that_array(qapp):
    offer = offerOf(
        makeLeaf('f', 'FLT_1D', path='time_slice[itime].profiles_1d',
                 coordinates=('psi',)),
        makeLeaf('r', 'FLT_0D', path='time_slice[itime].global_quantities',
                 coordinates=()))
    assert titles(offer) == [('time_slice/profiles_1d', True, 1),
                             ('time_slice/global_quantities', True, 1)]
    assert offer.timeGroups() == offer.groups()
    assert offer.staticGroups() == []


def test_the_innermost_array_does_not_take_the_group(qapp):
    # The array the time slider moves is the group; the structure under it names
    # the tab. Asked for the innermost array, this quantity would answer
    # `bpol_probe` -- a tab of its own, in the family that has no time base -- and
    # on the reference case that reading moves 2 310 of 3 368 quantities.
    offer = offerOf(makeLeaf('measured', 'FLT_0D',
                             path='time_slice[itime].constraints.bpol_probe[j]',
                             coordinates=(), aosCount=2,
                             indices={'i': '0', 'j': '0'},
                             lengths={'i': 49, 'j': 60}))
    assert titles(offer) == [('time_slice/constraints', True, 1)]


def test_a_quantity_hanging_straight_off_the_array_names_the_array(qapp):
    offer = offerOf(makeLeaf('gap', 'FLT_0D', path='time_slice[itime]',
                             coordinates=()))
    assert titles(offer) == [('time_slice', True, 1)]


def test_a_quantity_of_a_static_array_has_no_time_base_to_move(qapp):
    # `magnetics.flux_loop[i].flux.data` has a clock -- its own coordinate -- but
    # no dynamic array, so there is no slice index for a slider to move. The clock
    # is the abscissa the curve runs along, which is why TIME is offered and no
    # time group exists.
    leaf = makeLeaf('data', 'FLT_1D', path='flux_loop[i].flux',
                    coordinates=('flux_loop.flux.time',), itimeIndex=-1,
                    aosCount=1, idsName='magnetics')
    offer = offerOf(leaf, idsName='magnetics')
    assert titles(offer) == [('flux_loop', False, 1)]
    assert offer.timeGroups() == []
    assert offer.staticGroups() == offer.groups()
    assert leaf in offer.staticGroups()[0].following(TIME)


def test_three_elements_of_one_quantity_are_one_quantity_with_three_elements(qapp):
    # The tree keeps one node per element of a static array, and its parametrized
    # path spells the element with a placeholder, so the three probes of this stub
    # answer the same path. They are one thing to draw and an index to pick, not
    # three panels: measured on the case, `bpol_probe` is 130 probes of 10
    # quantities, which would be 1 300 panels of the same ten curves.
    def probe(index):
        return makeLeaf('data', 'FLT_1D', path='bpol_probe[i].flux',
                        coordinates=('bpol_probe.flux.time',), itimeIndex=-1,
                        aosCount=1, indices={'i': str(index)}, idsName='magnetics')

    offer = offerOf(probe(0), probe(1), probe(2), idsName='magnetics')
    group = offer.groups()[0]
    assert titles(offer) == [('bpol_probe', False, 1)]
    assert group.elementsOf(group.leaves[0]) == 3


def test_a_quantity_outside_any_array_is_one_group_named_for_what_it_lacks(qapp):
    offer = offerOf(makeLeaf('b0', 'FLT_1D', path='', coordinates=('time',),
                             itimeIndex=-1, aosCount=0))
    assert titles(offer) == [('no array of structures', False, 1)]
    assert offer.groups()[0].title() == 'no array of structures'


def test_a_leaf_of_text_and_a_bare_scalar_are_not_offered(qapp):
    # A string has nothing to draw whatever its axes, and a scalar with nothing
    # around it has no axis to draw along -- which is why the read refuses it
    # rather than borrowing another quantity's abscissa.
    offer = offerOf(makeLeaf('output_flag', 'STR_1D', path='',
                             coordinates=('time',), itimeIndex=-1, aosCount=0),
                    makeLeaf('rho_pcs', 'FLT_0D', path='', coordinates=(),
                             itimeIndex=-1, aosCount=0))
    assert offer.groups() == []
    assert offer.isPlottable() is False
    assert offer.refusal() == ('the %s IDS occurrence 0 holds no quantity this '
                               'tree can draw' % IDS)


def test_the_error_fields_are_left_out_and_counted(qapp):
    # `_error_` is the marker Viz_API.getChildren_ already filters on, and the
    # application draws those as bars on the curve they belong to. Left out of the
    # pages, but said: the count the user can check is never a surprise.
    offer = offerOf(makeLeaf('f', 'FLT_1D', path='time_slice[itime].profiles_1d',
                             coordinates=('psi',)),
                    makeLeaf('f_error_upper', 'FLT_1D',
                             path='time_slice[itime].profiles_1d',
                             coordinates=('psi',)),
                    makeLeaf('f_error_lower', 'FLT_1D',
                             path='time_slice[itime].profiles_1d',
                             coordinates=('psi',)))
    assert titles(offer) == [('time_slice/profiles_1d', True, 1)]
    assert offer.errorFields() == 2
    assert offer.errorFields() == 2, 'asking twice must not count twice'


def test_the_error_fields_can_be_asked_for(qapp):
    offer = offerOf(makeLeaf('f', 'FLT_1D', path='time_slice[itime].profiles_1d',
                             coordinates=('psi',)),
                    makeLeaf('f_error_upper', 'FLT_1D',
                             path='time_slice[itime].profiles_1d',
                             coordinates=('psi',)),
                    withErrors=True)
    assert titles(offer) == [('time_slice/profiles_1d', True, 2)]
    assert offer.errorFields() == 0


# --------------------------------------------------------------------------
# What is refused, and by what words
# --------------------------------------------------------------------------

def test_an_occurrence_whose_tree_was_never_built_is_refused_by_name(qapp):
    # The load is a command's job. A panel opened on an occurrence nobody loaded
    # is a panel with nothing in it and no reason given, so the reason is said.
    view = makeView(FakeBranch(kind='ids'), IDS, 0)
    with pytest.raises(ValueError) as refusal:
        QVizProfileOffer(view, 'magnetics', 2).groups()
    assert "the magnetics IDS occurrence 2 has no tree in this shot view" \
        in str(refusal.value)


def test_the_tensor_filter_is_said_as_a_fact_and_not_as_a_count(qapp):
    # The preference prunes while the tree is built, so what it took away is not
    # in the tree to be counted afterwards. A number here would be read as the
    # number of quantities the panel refused, so the answer is a fact about the
    # view and the panel names the preference.
    assert QVizProfileOffer(makeView(FakeBranch(kind='ids'), IDS, 0),
                            IDS, 0).tensorFilterIsOn() is False
    assert QVizProfileOffer(makeView(FakeBranch(kind='ids'), IDS, 0,
                                     filterOn=True), IDS, 0).tensorFilterIsOn() \
        is True
    assert not hasattr(QVizProfileOffer, 'hiddenByFilter')


# --------------------------------------------------------------------------
# The page window -- 100 at a time, nothing skipped, nothing twice
# --------------------------------------------------------------------------

def manyLeaves(count):
    return [makeLeaf('q%d' % index, 'FLT_1D',
                     path='time_slice[itime].profiles_1d',
                     coordinates=('psi',)) for index in range(count)]


def test_a_page_holds_a_hundred_and_the_last_page_holds_the_rest(qapp):
    offer = offerOf(*manyLeaves(250))
    pages = offer.groups()[0].pages(TIME)
    assert [len(page) for page in pages] == [PAGE, PAGE, 250 - 2 * PAGE]
    assert len(pages) == 3


def test_the_pages_hold_every_quantity_once_and_in_the_trees_order(qapp):
    # The defect this replaces: the two places that laid panels out each spelled
    # `tab * 100 + panels_so_far`, which double counts as soon as two tabs are
    # added at a time -- showing one quantity twice and skipping its neighbour.
    # Ten years of this case could not show it: 41 quantities, one page, and one
    # tab added per click.
    offer = offerOf(*manyLeaves(250))
    group = offer.groups()[0]
    quantities = group.following(TIME)
    pages = group.pages(TIME)
    flat = [leaf for page in pages for leaf in page]
    assert flat == quantities
    assert len({id(leaf) for leaf in flat}) == 250
    for left, right in zip(pages, pages[1:]):
        assert quantities.index(right[0]) == quantities.index(left[-1]) + 1


def test_a_quantity_this_absissa_cannot_carry_is_left_out_and_named(qapp):
    # A curve figure holds one bottom label. A quantity with two axes of its own
    # is a picture, not a curve: it is not on the pages, and `leftOut` names it,
    # because the count is the one thing the user can check.
    offer = offerOf(
        makeLeaf('f', 'FLT_1D', path='time_slice[itime].profiles_1d',
                 coordinates=('psi',)),
        makeLeaf('matrix', 'FLT_2D', path='time_slice[itime].profiles_1d',
                 coordinates=('psi', 'z')))
    group = offer.groups()[0]
    assert [leaf.getName() for leaf in group.following(TIME)] == ['f']
    assert [leaf.getName() for leaf in group.leftOut(TIME)] == ['matrix']
    assert sum(len(page) for page in group.pages(TIME)) == len(group.following(TIME))


def test_the_group_offers_its_absissae_with_the_clock_first(qapp):
    offer = offerOf(makeLeaf('f', 'FLT_1D', path='time_slice[itime].profiles_1d',
                             coordinates=('psi',)))
    group = offer.groups()[0]
    assert group.abscissae()[0] == TIME
    assert len(group.abscissae()) == 2
    # The default is the answer the figure would pick for itself, so the panel and
    # the read cannot drift apart about what a new window runs along.
    assert offer.abscissaFor(group) == choose(QVizNodePlotting(group.leaves[0]).axes)
    assert offer.abscissaFor(group) == TIME


# --------------------------------------------------------------------------
# The case: an IDS the plugin knows, and an IDS it never knew
# --------------------------------------------------------------------------

class BrowserStub:
    def getActiveUsername(self):
        return ''

    def addUserDB(self, username):
        pass


class RootWindow(QMainWindow):
    """The application's root window, named the way the application names it."""

    def __init__(self):
        super().__init__()
        self.setObjectName('IMASViz root window')
        self.MDI = QMdiArea(self)
        self.IMASdbBrowserWidget = BrowserStub()

    def getMDI(self):
        return self.MDI


class Case:
    """One shot view of the reference case, with the IDSs this file asks about.

    The view is opened the way the application opens it -- a source from the
    factory, the dictionary the case was written with, then the api building the
    view -- and each IDS is loaded through the command the menu uses, so the tree
    this module walks is the tree the user would see.
    """

    def __init__(self, qapp, root):
        self.qapp = qapp
        self.root = root
        self.api = QVizMainMenuController(root).openShotView.api
        self.view = None
        self.costs = {}

    def openCase(self, uri, ddVersion):
        source = QVizDataSourceFactory().create(uri)
        source.dd_version = ddVersion
        self.view = self.api.CreateDataTree(source).dataTreeView
        self.api.ShowDataTree(self.view)
        self.pump()

    def load(self, idsName, occurrence=0):
        self.api.LoadListOfIDSs(self.view, [idsName], occurrence)
        self.pump()
        key = '%s/%s' % (idsName, occurrence)
        assert key in getattr(self.view, 'ids_roots_occurrence', {}), \
            '%s is not among %r' % (key, sorted(self.view.ids_roots_occurrence))

    def offer(self, idsName, occurrence=0, **kw):
        t0 = time.time()
        offer = QVizProfileOffer(self.view, idsName, occurrence, **kw)
        offer.groups()
        self.costs[(idsName, occurrence)] = time.time() - t0
        return offer

    def pump(self, times=300):
        for _ in range(times):
            self.qapp.processEvents()


@pytest.fixture(scope='module')
def case(qapp):
    """One case, two IDSs loaded, shared below -- these tests read one view."""
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    # Pinned, not inherited: both preferences move the walk the trees are built
    # from, and the numbers pinned above are the numbers of this state. GGD
    # structures of this IDS cost minutes (test_53 measured 287 s for a run), and
    # the rank filter prunes the tree as it is built, so the quantities below
    # would not be in the trees at all.
    QVizPreferences.Ignore_GGD = 1
    QVizPreferences.Show_only_tensors_rank_ge_1 = 0
    root = RootWindow()
    root.show()
    qapp.processEvents()
    made = Case(qapp, root)
    made.openCase(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    made.load('equilibrium')
    made.load('magnetics')
    # The view and its api hold every node this file walks, and every frame a
    # later test may draw from them.
    ownership.keep(made)
    yield made


def test_the_case_holds_both_ids_this_file_asks(case):
    assert all(0 in case.view.occurrences.occurrencesOf(ids)
               for ids in ('equilibrium', 'magnetics'))
    assert case.view.occurrences.occurrencesOf('equilibrium') == [0, 1, 2, 3]


def test_equilibrium_answers_the_tabs_the_plugin_used_to_list_plus_the_ones_it_omitted(case):
    offer = case.offer('equilibrium')
    assert titles(offer) == EQUILIBRIUM_GROUPS
    assert offer.isPlottable()
    assert offer.refusal() is None
    assert offer.tensorFilterIsOn() is False


def test_the_error_fields_of_the_case_are_left_out_and_said(case):
    offer = case.offer('equilibrium')
    kept = sum(len(group.leaves) for group in offer.groups())
    assert (kept, offer.errorFields()) == (EQUILIBRIUM_KEPT, EQUILIBRIUM_ERRORS)
    whole = case.offer('equilibrium', withErrors=True)
    total = sum(len(group.leaves) for group in whole.groups())
    assert total == EQUILIBRIUM_WITH_ERRORS
    # The two numbers are in the same unit, so they add up: what is offered plus
    # what was refused is what the occurrence holds.
    assert kept + EQUILIBRIUM_ERRORS == total


def test_an_ids_the_plugin_never_named_is_offered_the_same_way(case):
    # `magnetics` is in none of the five lists the plugin used to carry, and
    # nothing here names it: the tree answers it. And it answers no time group,
    # because this case writes it with `homogeneous_time = 1` -- the clock is a
    # coordinate of each quantity, not the index of a dynamic array.
    offer = case.offer('magnetics')
    assert titles(offer) == MAGNETICS_GROUPS
    assert offer.timeGroups() == []
    assert [group.title() for group in offer.staticGroups()] \
        == [title for title, _moved, _count in MAGNETICS_GROUPS]


def test_a_quantity_of_a_static_array_answers_how_many_elements_it_has(case):
    # The tree holds one node per element here: 17 flux loops and 130 bpol probes
    # of this case, each holding the same handful of quantities. One entry per
    # quantity, and the extent of the index control answered apart -- a panel per
    # node would draw the same curve 130 times.
    elements = {}
    for group in case.offer('magnetics').groups():
        elements[group.title()] = {group.elementsOf(leaf) for leaf in group.leaves}
    assert elements == {'flux_loop': {MAGNETICS_ELEMENTS['flux_loop']},
                        'bpol_probe': {MAGNETICS_ELEMENTS['bpol_probe']},
                        'method': {1}, 'no array of structures': {1}}
    # Inside the dynamic array the tree keeps one node per quantity already,
    # standing on slice 0: it is the time slider that moves it, not an index.
    profiles = [one for one in case.offer('equilibrium').groups()
                if one.title() == 'time_slice/profiles_1d'][0]
    assert {profiles.elementsOf(leaf) for leaf in profiles.leaves} == {1}


def test_the_pages_of_a_real_group_hold_its_quantities_once(case):
    offer = case.offer('equilibrium')
    profiles = [one for one in offer.groups()
                if one.title() == 'time_slice/profiles_1d'][0]
    assert [len(page) for page in profiles.pages(TIME)] == [len(profiles.leaves)]
    constraints = [one for one in offer.groups()
                   if one.title() == 'time_slice/constraints'][0]
    flat = [leaf for page in constraints.pages(TIME) for leaf in page]
    assert flat == constraints.following(TIME)
    # One node per quantity path, so a page cannot hold the same quantity twice
    # under two element indices.
    assert len({leaf.getParametrizedDataPath() for leaf in flat}) == len(flat)
    assert sorted({constraints.elementsOf(leaf)
                   for leaf in constraints.leaves}) == CONSTRAINTS_ELEMENTS


def test_the_walk_costs_nothing_beside_the_load_it_reads(case):
    # Measured 0,04 s for the 191 quantities of equilibrium, against 0,6 s for
    # the load that put them in the tree. The bound is here so a later reading
    # that re-walks the dictionary instead of the tree is refused.
    for key, cost in case.costs.items():
        assert cost < 2.0, 'discovering %s cost %.2f s' % (key, cost)
