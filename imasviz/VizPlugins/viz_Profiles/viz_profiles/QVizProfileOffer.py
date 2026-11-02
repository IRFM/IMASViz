# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What one IDS of one opened case can be plotted as, read off the tree it holds.

The panel used to be told what to draw. Each of the five IDSs it knew carried its
own lists -- the array of structures to slice, the paths to keep, the label of
each tab, and the static index for `source(i1)` and `model(i1)` -- about a hundred
and twenty literals in the plugin's own file. That is why the plugin knew five
IDSs and no more: an IDS with no list has no tab to open, and the sixth had to be
written by hand before anyone could look at it. `magnetics`, `ion_cy_hjt`,
`wall`, `kinetic_profile` -- every one of them holds quantities the application
already draws elsewhere, and none of them was offered here.

The tree the case already built answers the same questions, and it answers them
for every IDS the case holds. `QVizNodePlotting` (VizDataAccess/QVizNodePlotting.py)
says of any node whether it is a data leaf, whether it is text, whether anything
can be drawn of it and along which abscissae; `QVizAxesSpec` names the arrays of
structures that hold it and says which of them carries the time base. So a group
is derived, never declared: the quantities of one occurrence, held by the same
array of structures, and a name that comes from the dictionary.

Measured on the reference case (WEST 54924 run 0, written at DD 3.35.0), with the
GGD walk off and the rank filter off: `equilibrium` occurrence 0 answers **10
groups in 0,04 s** over **191 quantities** -- no array of structures (3),
`time_slice/boundary` (27), `/boundary_separatrix` (28),
`/boundary_secondary_separatrix` (4), `/constraints` (30), `/global_quantities`
(26), `/profiles_1d` (50), `/coordinate_system` (21), `/convergence` (1), and
`time_slice` itself (1). Those are the seven tabs the hand-written lists spelled,
plus the two separatrices those lists omitted. `magnetics`, which no list ever
named, answers 4 groups in 0,08 s (`flux_loop` 7, `bpol_probe` 10, `method`
2, no array 2) and `wall` 4 in 0,00 s. The walk costs nothing beside the load that
precedes it (0,6 s for `equilibrium`), so nothing is cached behind it.

Those counts are **quantities**, not tree nodes. The same case answers 945 leaves
for `equilibrium` and 1 423 for `magnetics`, because the tree keeps one node per
*element* of a static array -- 130 `bpol_probe` holding 10 quantities. What a panel
draws is a quantity at an index, so the index is a control and the group answers
`elementsOf` to say how far that control reaches. Measured on that case, no path of
`signalsList` is shared by two nodes: the 130 probes answer 130 different paths
(`magnetics/flux_loop(0)/flux/data`, `flux_loop(1)/…`), so a page names the element
it draws and the command that resolves the path has nothing to guess.

Two things this deliberately does **not** do:

* It does not walk the data dictionary again. It walks the nodes of this view, so
  what the panel offers is what the tree holds -- including what the user set on
  a node (an array index picked in the tree, a coordinate changed from the menu),
  which lives on the node and nowhere else. A second walk would be a second
  truth, and the two diverge the moment a user touches one of them.
* It does not decide alone what is worth drawing. `QVizPreferences
  .Show_only_tensors_rank_ge_1` prunes the tree as it is built
  (QVizDataTreeViewBuilder._flattenToNonEmptyTensors), so a scalar the preference
  hid is not a node this view holds. This module says which view has that
  preference on (`tensorFilterIsOn`) rather than reaching around it: drawing a
  quantity the user chose to hide from the tree, through a path no node answers,
  is how a panel ends up showing a quantity that cannot be selected, named or
  clicked anywhere else.
"""

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxis
from imasviz.VizDataAccess.QVizCurveAbscissa import TIME, abscissae, choose
from imasviz.VizDataAccess.QVizNodePlotting import QVizNodePlotting


# How many panels one page of the panel holds. The number the plugin already used
# for ten years; it stays because it is what fits a page of the table window, not
# because the old code computed it.
PAGE = 100

# The marker the dictionary puts on an error field, and the one the application
# already filters on where it walks a tree for quantities (Viz_API.getChildren_).
# Spelled once here so the panel and that walk cannot disagree about what an
# error field is.
ERROR_FIELD = '_error_'

# The panel's other strategy: **not** an abscissa identity, but the request "each
# quantity along whatever axis it has of its own, along the clock only when it has
# none". It is spelled here rather than in the panel because it is the same request
# the Table Plot View answers with `plotAxis` left out -- and two spellings of one
# request is how a tab came to list quantities its own window then refused.
OWN_AXIS = 'own axis'


class QVizProfileGroup:
    """The quantities of one array of structures, and what they can be read along.

    Arguments:
        label (str) : the array of structures, spelled as the dictionary names it
            ('time_slice', 'profiles_1d', 'flux_loop'). None for a quantity no
            array of structures holds -- then the group is the IDS itself.
        alongTime (bool) : whether that array is the one carrying the time base,
            which is what decides whether a time slider means anything here.
        leaves (list) : one tree node per **quantity**, in the order the tree
            holds them. They are the view's own nodes, so a plot built from one is
            the same node the user can select and click.
        elements (dict) : how many nodes of this array the tree holds for each
            quantity path, keyed by that path. See `elementsOf`.
    """

    def __init__(self, label, alongTime, leaves, elements=None):
        self.label = label
        self.alongTime = alongTime
        self.leaves = leaves
        self._elements = elements or {}

    def title(self):
        """What the tab says. A quantity outside any array has no array to name."""
        return self.label if self.label else 'no array of structures'

    def elementsOf(self, leaf):
        """How many elements of its array the tree holds for this quantity.

        One node per element, because that is how the tree is built for a **static**
        array of structures: measured on the reference case, `magnetics.bpol_probe`
        holds 130 elements of 10 quantities, so the walk meets 1 300 leaves. They are
        not 1 300 things to draw -- an entry draws an *element*, pinned to the index
        its node carries, and the index is a control, not a quantity. So the group
        answers one node per quantity (the one the tree stands on) and this answers
        how far the index control has to reach. Inside a **dynamic** array the tree
        keeps one node per quantity already, standing on slice 0, which is why the
        answer there is 1 and the time slider is what moves it.
        """
        return self._elements.get(leaf.getParametrizedDataPath(), 1)

    def elementCount(self):
        """The largest `elementsOf` this group answers, for a tab that has to say.

        One number per tab, because a tab is one array: measured on the reference
        case `flux_loop` answers 17 and `bpol_probe` 130, and the sentence the panel
        writes names the array the reader is looking at rather than a count that
        belongs to another tab.
        """
        return max([self.elementsOf(leaf) for leaf in self.leaves] or [1])

    def abscissae(self):
        """Every abscissa some quantity of this group can run along, TIME first.

        Asked of the axes, so no data is read: the panel shows this before the
        user chooses, and choosing must not pay for a read of the case.
        """
        known = []
        for leaf in self.leaves:
            for abscissa in abscissae(QVizNodePlotting(leaf).axes):
                if abscissa not in known:
                    known.append(abscissa)
        if TIME in known:
            known.remove(TIME)
            known.insert(0, TIME)
        return known

    def following(self, abscissa):
        """The quantities this abscissa can carry.

        `abscissa` is an identity from `abscissae()`, or `OWN_AXIS` for the panel's
        other strategy: each quantity along the axis it has of its own, and along
        the clock only when it has none. `QVizCurveAbscissa.choose` is asked that
        same question, so the list on the tab and the panels the window draws
        answer for the same quantities.
        """
        if abscissa == OWN_AXIS:
            return [leaf for leaf in self.leaves
                    if choose(QVizNodePlotting(leaf).axes,
                              alongTime=False) is not None]
        return [leaf for leaf in self.leaves
                if abscissa in abscissae(QVizNodePlotting(leaf).axes)]

    def leftOut(self, abscissa):
        """The quantities this abscissa cannot carry, so they can be named.

        A quantity with two axes of its own is a picture and not a curve: a curve
        figure holds one bottom label. Saying so is the whole of the answer -- the
        panel must not quietly draw fewer panels than the group holds, because the
        count is the one thing the user can check.
        """
        return [leaf for leaf in self.leaves if leaf not in self.following(abscissa)]

    def pages(self, abscissa):
        """[[leaf, ...]] along this abscissa, PAGE at a time, nothing skipped.

        One function for the page window because the two places that used to lay
        panels out spelled the same arithmetic separately, and the two spellings
        were not the same once more than one page was added at a time.
        """
        quantities = self.following(abscissa)
        return [quantities[start:start + PAGE]
                for start in range(0, len(quantities), PAGE)]


class QVizProfileOffer:
    """What can be drawn of one IDS, at one occurrence, in this view.

    Arguments:
        dataTreeView : the shot view the plugin was offered on. Its
            `ids_roots_occurrence` holds the tree built for this IDS and this
            occurrence, which is the only walk this module does.
        idsName, occurrence : what was chosen. The occurrence is the view's
            answer -- `occurrences.occurrencesOf` -- never a count read off the
            data dictionary, which is the mistake that made this plugin's
            occurrence question impossible to answer on this IMAS stack.
    """

    def __init__(self, dataTreeView, idsName, occurrence, withErrors=False):
        """
        Arguments:
            withErrors (bool) : whether the error fields of the dictionary are
                quantities of their own here. Left out, as the plugin always had
                them: `equilibrium` occurrence 0 of the reference case holds 3 368
                plottable leaves, answering 727 quantities, and **536** of those
                quantities are `measured_error_upper`, `measured_error_lower` and
                friends -- 2 423 leaves, 1 950 of them in `time_slice/constraints`
                alone. A panel per one piles up three panels for every curve, saying
                the same thing. The application draws those as **bars on the curve
                they belong to** (`QVizCurveErrors`), which is what they are. They
                stay reachable: the tree still offers them, and `errorFields` says
                how many were left out, so the count the user can check is never a
                surprise.
        """
        self.view = dataTreeView
        self.idsName = idsName
        self.occurrence = occurrence
        self.withErrors = withErrors
        self._groups = None

    def root(self):
        """The tree node standing for this IDS at this occurrence.

        Refused by name when it is not there: the loads are a command's job
        (`QVizLoadOccurrence`, which this plugin already calls), and a panel
        opened on an occurrence whose tree was never built is a panel with
        nothing in it and no reason given.
        """
        key = '%s/%s' % (self.idsName, self.occurrence)
        root = getattr(self.view, 'ids_roots_occurrence', {}).get(key)
        if root is None:
            raise ValueError(
                'the %s IDS occurrence %s has no tree in this shot view: it has '
                'to be loaded before anything of it can be plotted.'
                % (self.idsName, self.occurrence))
        return root

    def groups(self):
        """[QVizProfileGroup], in the order the tree holds its quantities.

        One group per array of structures, holding one node per quantity. The two
        families the panel shows apart -- a quantity of a dynamic array has a time
        index to move, and one outside it has nothing of the sort, so a slider over
        it would ask for a value no axis answers -- are `timeGroups` and
        `staticGroups`; the order here stays the tree's, because that is the order
        the user reads the folders in.
        """
        if self._groups is None:
            byLabel = {}
            order = []
            for node in self._leaves():
                plotting = QVizNodePlotting(node)
                label, alongTime = self._heldBy(plotting)
                key = (label, alongTime)
                if key not in byLabel:
                    byLabel[key] = {}
                    order.append(key)
                # One entry per quantity path: the tree keeps one node per *element*
                # of a static array, and its parametrized path spells the element
                # with a placeholder (`bpol_probe[i].field.data`), so the 130 probes
                # of this case answer the same path 130 times. See elementsOf.
                byLabel[key].setdefault(node.getParametrizedDataPath(),
                                        []).append(node)
            self._groups = []
            for (label, alongTime) in order:
                quantities = {}
                counts = {}
                for path, nodes in byLabel[(label, alongTime)].items():
                    quantities[path] = nodes[0]
                    counts[path] = len(nodes)
                self._groups.append(
                    QVizProfileGroup(label, alongTime,
                                     list(quantities.values()), counts))
        return self._groups

    def timeGroups(self):
        return [group for group in self.groups() if group.alongTime]

    def staticGroups(self):
        return [group for group in self.groups() if not group.alongTime]

    def isPlottable(self):
        return bool(self.groups())

    def refusal(self):
        """Why there is nothing to draw, or None when there is something.

        Said rather than left to an empty window: this occurrence may hold the
        IDS with every array empty, which is a fact about the pulse and not a bug
        in the panel, and the user reading a blank window cannot tell them apart.
        """
        if self.groups():
            return None
        return ('the %s IDS occurrence %s holds no quantity this tree can draw'
                % (self.idsName, self.occurrence))

    def tensorFilterIsOn(self):
        """Whether this view prunes its tree as it is built, and what says so.

        Answered as a fact about the view, never as a count. The preference prunes
        while the tree is built, so what it took away is not in the tree to be
        counted afterwards: this walk sees the pruned tree, and a number invented
        here would be read as the number of quantities the panel refused. The panel
        names the preference that commands it and draws what the view holds.
        """
        return bool(getattr(self.view, 'showOnlyTensorsRankGe1', False))

    def quantityCount(self):
        """How many quantities the tabs hold, in the unit the tabs count in."""
        return sum(len(group.leaves) for group in self.groups())

    def timeBases(self):
        """The dynamic arrays the tabs stand on, as the panels key their sliders.

        One entry per time base, and the axis object itself, so the key a cursor
        answers with is the key the panels' own rows are keyed by -- which is the
        only way a cursor on this panel can move a slider in a window this panel
        did not build. The length comes off the tree, so answering needs no read of
        the case: measured, `equilibrium` answers one base (`time_slice`, 49
        elements) and `magnetics` answers none, because that IDS is written at
        `homogeneous_time = 1` and has no dynamic array to move.
        """
        bases = {}
        for group in self.timeGroups():
            if not group.leaves:
                continue
            for axis in QVizNodePlotting(group.leaves[0]).axes.axes:
                if axis.origin == QVizAxis.AOS and axis.is_time:
                    bases.setdefault(axis.key(), axis)
        return list(bases.values())

    def abscissae(self, group=None):
        """The abscissae to offer, TIME first, for one group or for all of them."""
        if group is not None:
            return group.abscissae()
        known = []
        for one in self.groups():
            for abscissa in one.abscissae():
                if abscissa not in known:
                    known.append(abscissa)
        if TIME in known:
            known.remove(TIME)
            known.insert(0, TIME)
        return known

    def abscissaFor(self, group):
        """The abscissa a group would pick for itself, the one the read would pick.

        `QVizCurveAbscissa.choose` is the application's answer to "along what",
        asked the way a figure asks it -- so the panel's default and the figure's
        default cannot drift apart.
        """
        leaves = group.leaves
        if not leaves:
            return None
        return choose(QVizNodePlotting(leaves[0]).axes)

    def errorFields(self):
        """How many quantities were left out for being error fields.

        Counted in the same unit as the groups, so the two numbers add up to what
        the tree holds: `equilibrium` occurrence 0 answers 191 quantities and
        refuses **536** error quantities here (2 423 leaves, because the 110
        `bpol_probe` of one quantity are one quantity).
        """
        self.groups()
        return len(self._errors)

    def _leaves(self):
        """The nodes of this occurrence worth drawing, in the tree's own order."""
        found = []
        self._errors = set()
        self._walk(self.root(), found)
        return found

    def _walk(self, node, found):
        for row in range(node.childCount()):
            child = node.child(row)
            if child.isIDSRoot() or child.isStructure() or child.isArrayOfStructure():
                self._walk(child, found)
            elif QVizNodePlotting(child).isPlottable():
                if self.withErrors or ERROR_FIELD not in (child.getPath() or ''):
                    found.append(child)
                else:
                    # The path, not the node: 110 elements of one error field are
                    # one quantity left out, which is the unit groups() answers in.
                    self._errors.add(child.getParametrizedDataPath())

    def _heldBy(self, plotting):
        """(what the tab should say, does a time slider move it) for one quantity.

        The array that **drives** the quantity, not the innermost one. Measured on
        the reference case the tree spells `time_slice[itime].constraints.
        bpol_probe[j].measured` with both arrays in the path, so the innermost
        answer is `bpol_probe` -- and a quantity of the dynamic array would then
        land in the family that has no time base and no slider to move it, while
        2 310 of the 3 368 quantities of `equilibrium` occurrence 0 would answer
        under an array no tab names. The time-carrying array is the one the slider
        moves, so it is the group, and the first structure under it names the tab
        -- which is what the hand-written list used to spell by hand:
        `time_slice/boundary` (its `x_point` and `strike_point` inside it),
        `time_slice/constraints` (its `bpol_probe` and `flux_loop` inside it),
        `time_slice/profiles_1d`, `time_slice/global_quantities`.

        Outside a dynamic array there is no driver to follow, and the outermost
        array is the one the tree opens a folder for: `flux_loop`, `bpol_probe`.
        """
        arrays = [axis for axis in plotting.axes.axes
                  if axis.origin == QVizAxis.AOS]
        if not arrays:
            return None, False
        driving = [axis for axis in arrays if axis.is_time]
        if driving:
            name = driving[0].name
            under = self._firstUnder(plotting.treeNode, name)
            return ('%s/%s' % (name, under) if under else name), True
        return arrays[0].name, False

    @staticmethod
    def _firstUnder(treeNode, driver):
        """The first structure below the driving array, in the tree's own spelling.

        Read off the parametrized path because that is the spelling the tree
        carries, indices included: `equilibrium.time_slice[itime].boundary.
        x_point[j].r` answers `boundary`, and a quantity hanging straight off the
        array answers None -- the tab named by the array alone.
        """
        steps = (treeNode.getParametrizedDataPath() or '').split('.')
        for position, step in enumerate(steps):
            if step.split('[')[0] != driver:
                continue
            if position + 1 >= len(steps):
                return None
            name = steps[position + 1].split('[')[0]
            return None if name == treeNode.getName() else name
        return None
