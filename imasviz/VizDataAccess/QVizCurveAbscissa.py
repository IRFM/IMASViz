# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Which axis a curve runs along, and whether two curves run along the same one.

A curve figure has one abscissa. So the question "may this quantity be added to
that figure?" is not about the quantity alone: it is about the abscissa the
figure already draws, and about whether this quantity can be read along it.

Three places used to answer that question separately, and none of them knew what
the figure held:

    `QVizNodePlotting.curveAxisKey()`   what the menus compared, and what
        `Viz_API.figureDrawsSameCurveAxis` compared every registered node against
    `QVizTreeNode.isPlotToPerformAlongTimeAxis`   what the read fell back on,
        through a string the frame carries
    `QVizCurvePlot.setAxisLabels`   what the bottom label ended up saying

Measured on WEST 54924 (DD 3.35.0), on the two quantities of one structure that
the manual plots together -- `equilibrium.time_slice[i].profiles_1d.f` and
`.psi`, both read along time by the read:

    key of `.f`     ('LEAF', 'equilibrium', 'time_slice(itime).profiles_1d.psi')
    key of `.psi`   ('LEAF', 'equilibrium', 'dimension 1')
    gate            False for both

so neither is offered in the other's figure. And the same probe drew `.f` against
`psi` (101 points, -7,97 ... -7,78) and then `.psi` against its index (101 points,
0 ... 100), rewriting the figure's one bottom label from `psi` to `dimension 1`
-- while the history the manual documents is 49 points, 32,13 s ... 48,55 s. One
abscissa, three answers, and the figure was not one of them.

This module answers it once, from the axes the read walks:

    an abscissa is an **identity**, not a spelling. IMAS spells the same clock
    three ways -- the dynamic array (`IDS.time`), `<aos>/time`, bare `time` --
    and which spelling a case uses follows `ids_properties.homogeneous_time`, so
    two quantities of one IDS can name their time base differently. They are one
    abscissa: `TIME`. Same for a coordinate named by the dictionary:
    `time_slice(itime).profiles_1d.psi` and the same coordinate under another
    index spelling are one abscissa.

    a quantity is offered to a figure when the figure's abscissa is one of the
    abscissae that quantity **can** be read along -- a quantity in the dynamic
    array can be read along time or along its own coordinate, which is exactly
    the pair of menu entries the manual documents.

Nothing here decides how to read: it answers an identity, and the read turns it
into walking the dynamic array or slicing at one time.
"""

import re

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxis

# The clock of a case, whichever of IMAS' three spellings this case happens to
# use. Keyed alone -- no IDS name, no nesting: `equilibrium.time` and
# `core_profiles.time` are different samplings of one physical abscissa, in
# seconds, which is what "the same abscissa" means for a curve figure. The
# manual's own example compares quantities across two IMAS databases.
TIME = ('time',)

# The loop decoration a coordinate or a parametrized path writes in front of an
# array of structures -- 'time_slice(itime)' in a coordinate, 'time_slice[itime]'
# in a path. It says which element of which array the road went through, not
# which axis the coordinate is.
LOOP_DECORATION = re.compile(r'(?:\([a-z][a-z0-9]*\)|\[[a-z][a-z0-9]*\])')

COORDINATE = 'coordinate'
DIMENSION = 'dimension'


def identityOf(axis):
    """The identity of the axis a curve would run along.

    Time first, whatever the spelling: at `homogeneous_time == 1` the base is
    `IDS.time`, at 0 it is the coordinate spelled under the element that carries
    the quantity, and the two must not be two abscissae -- otherwise a quantity
    read along one is refused from a figure drawing the other, which is the
    refusal this file exists to remove.

    A coordinate the dictionary names is keyed by that name, decoration and IDS
    prefix taken out: two quantities of one structure sampled on one grid share
    one grid, and the decoration only says which element of an enclosing array
    they were read at.

    An axis the dictionary leaves unbounded (`1..N`) names no node, so the only
    thing two such axes can share is what they are measured in.
    """
    if axis.is_time:
        return TIME
    if axis.origin == QVizAxis.LEAF and axis.coordinate:
        return (COORDINATE, normaliseCoordinate(axis.coordinate,
                                                axis.idsName))
    return (DIMENSION, axis.units or '')


def normaliseCoordinate(coordinate, idsName=None):
    """The coordinate name the dictionary means, decoration and IDS prefix out.

    The shadow tree spells a coordinate from the structure that holds it and
    marks the array element it belongs to: `time_slice(itime).profiles_1d.psi`.
    The tree node spells the same road with dots, and a coordinate read back from
    the dictionary carries the IDS root in front. The decoration names an element
    of an enclosing array, not an axis, and the IDS root is one of the two
    spellings -- neither belongs to the identity.
    """
    name = LOOP_DECORATION.sub('', str(coordinate)).replace('/', '.')
    parts = [part for part in name.split('.') if part]
    if idsName and parts and parts[0] == idsName:
        parts = parts[1:]
    return '.'.join(parts)


def abscissae(axesSpec):
    """The abscissae a curve of this quantity can run along, first one first.

    Empty when the quantity has more than one axis of its own: that is a picture,
    not a curve, and the routing that decides it is `QVizNodePlotting`'s -- asked
    of the axes, because a right click must not pay for a read.

    **Time comes first.** The manual plots **equilibrium.time_slice[0].profiles_1d.f**
    through the plain :guilabel:`New` entry and states what comes out: X is
    ``equilibrium.time``, Y is ``profiles_1d.f[0]`` over all the time slices
    (manual, *Plotting 1D arrays as a function of time*). That is the default of a
    figure asked nothing, and it was not what the code did: the frame carried
    ``plotAxis = 'DEFAULT'``, which fed ``is1DAndDynamic() -> False`` into
    ``isPlotToPerformAlongTimeAxis``, and the quantity was read along its spatial
    coordinate instead -- 101 points against ``psi`` on that very leaf, measured.
    This order is the user's second complaint, and the manual is what makes it a
    bug rather than a taste.

    A quantity held by nothing but a time base answers one abscissa, and it is
    time; a quantity of one axis and no clock answers one, and it is its own.
    """
    own = axesSpec.leafAxes()
    if len(own) > 1:
        return []

    options = []
    if any(axis.is_time for axis in axesSpec.axes):
        options.append(TIME)
    if own:
        identity = identityOf(own[0])
        if identity not in options:
            options.append(identity)
    return options


def dynamicArrayAxis(axesSpec):
    """The array of structures a curve walks when it runs along the clock.

    The read indexes that array once per point of the curve, so it is the one
    axis the abscissa draws rather than leaves out -- and no slider may be put on
    it, which is what `QVizTensorDataAccess._timeAxis` answers for the read. Asked
    here so the read, the menus and the figure cannot pick different arrays.
    """
    for axis in axesSpec.axes:
        if axis.is_time and axis.origin == QVizAxis.AOS:
            return axis
    return None


def plottedPositions(axesSpec, alongTime):
    """Which positions of the spec a curve of this quantity draws.

    One spelling of the rule for the read, the controls and the superposition
    gate: running along the clock walks the dynamic array, anything else slices
    at one element of every array and draws the leaf's own axes. It mirrors
    `QVizTensorDataAccess._plottedPositions`, which delegates here.
    """
    if alongTime:
        axis = dynamicArrayAxis(axesSpec)
        if axis is not None:
            return (axesSpec.axes.index(axis),)
    return tuple(position for position, axis in enumerate(axesSpec.axes)
                 if axis.origin == QVizAxis.LEAF)


def axesLeftOut(axesSpec, abscissa):
    """The axes a figure running along this abscissa does not draw.

    The abscissa answers which arrays are walked and which are left out, so the
    same quantity leaves out different arrays on a figure drawn against time and
    on one drawn against `psi`: `equilibrium.time_slice[i].profiles_1d.f` leaves
    out nothing along time -- the curve *is* the array -- and leaves out
    **time_slice** along `psi`, which is the slider the manual asks for there
    ("the other slices are reached through *Explore this tensor*, which puts a
    slider on time_slice"). Asking the axes without the abscissa cannot answer
    that, and answering it once per caller is what let a documented slider go
    missing.
    """
    alongTime = abscissa == TIME and dynamicArrayAxis(axesSpec) is not None
    drawn = plottedPositions(axesSpec, alongTime)
    return [axis for position, axis in enumerate(axesSpec.axes)
            if position not in drawn]


def arraysLeftOut(axesSpec, abscissa):
    """The arrays of structures a figure running along this abscissa leaves out.

    A figure's identity beside its abscissa: the arrays it puts under a slider
    are the arrays its traces leave out, and a second tensor whose sliders would
    be different arrays is not the same picture -- its sliders would move some of
    the curves and not the others, which is what "les axes soient les memes"
    refuses.
    """
    return frozenset(axis.key() for axis in axesLeftOut(axesSpec, abscissa)
                     if axis.origin == QVizAxis.AOS)


def spellArrays(keys):
    """The arrays of a key set, named as a control names them, for a refusal.

    A refusal that says "different axes" is useless; one that says *which* axes
    are the two figures' says what to change. The last part of an axis key is the
    array name for an array of structures and the coordinate for a leaf axis,
    which is what `sliceLabel` puts on the control for the same axis.
    """
    if not keys:
        return 'nothing'
    return ' and '.join(sorted(str(key[-1]) for key in keys))


def axisPhrase(abscissa):
    """What an entry naming this abscissa would say to the user."""
    if abscissa == TIME:
        return 'time axis'
    if abscissa and abscissa[0] == COORDINATE:
        return str(abscissa[1]).rsplit('.', 1)[-1]
    if abscissa and abscissa[0] == DIMENSION:
        return 'its index' + ('[%s]' % abscissa[1] if abscissa[1] else '')
    return 'nothing'


def hasNoAxisOfItsOwn(axesSpec):
    """A quantity with no axis to run along: a scalar the figure has to place.

    A 0D leaf held by an array of structures has nothing but the arrays around it,
    and those the tree stands on. Drawn on a figure that already runs along
    something, the honest reading is the same value at every point of that axis --
    which is what the table and the stacked window have always shown, and which
    the read says in the log of the case. On an empty figure there is nothing to
    spread it over, and that is a refusal.
    """
    return not axesSpec.leafAxes()


def choose(axesSpec, abscissa=None, alongTime=None):
    """The abscissa this curve must run along, or None when it cannot.

    `abscissa` is what the figure already draws. When it has one, **it decides**:
    a curve figure has one bottom label and one abscissa, so nothing a caller
    asks for can put a second one under it. `alongTime` is then read for what it
    is -- an entry asking for the history -- and stands aside rather than
    refusing a quantity the figure can show.

    On a figure that has drawn nothing yet, `alongTime` is the entry's opinion:
    True for "as a function of time", False for "not along time" -- the Profiles
    plugin has both entries, and the manual keeps them apart (*"The time slider
    appears only for plots along the 'coordinate1' axis"*). Neither is a veto: an
    IDS at `homogeneous_time == 1` has no time *axis* at all
    (`magnetics.time` on the reference case), and the entry that asks for a
    history still has to draw it.

    Answering None is a refusal, and it has to be sayable: the caller names the
    abscissa of the figure and the abscissae of the quantity, because "this
    cannot go in that figure" is only useful if it says why.
    """
    options = abscissae(axesSpec)

    if abscissa is not None:
        if abscissa in options:
            return abscissa
        if hasNoAxisOfItsOwn(axesSpec):
            # A scalar takes the abscissa of the figure it is added to: it has
            # none of its own to disagree with.
            return abscissa
        return None

    if alongTime is True and TIME in options:
        return TIME
    if alongTime is False:
        notTime = [option for option in options if option != TIME]
        options = notTime or options
    return options[0] if options else None


def labelFor(axesSpec, abscissa):
    """The bottom label of a curve figure running along this abscissa.

    Asked with the abscissa rather than with the answer to "did the read walk the
    dynamic array", because the two are not the same question: a quantity whose
    own coordinate *is* a time base (`magnetics.flux_loop[i].flux.time`, measured
    on the reference case) is sliced at one element of a static array and still
    runs along the clock. Labelling it `time[s]` is what the numbers say.
    """
    if abscissa == TIME:
        return 'time', 's'
    own = axesSpec.leafAxes()
    axis = own[0] if own else None
    if axis is None:
        return '', ''
    if axis.origin == QVizAxis.AOS:
        return axis.name or '', axis.units or ''
    if axis.coordinate:
        return normaliseCoordinate(axis.coordinate).rsplit('.', 1)[-1], \
               axis.units or ''
    return 'dimension %d' % axis.level, axis.units or ''


def describe(abscissa):
    """How to name an abscissa in a message the user reads."""
    if abscissa == TIME:
        return 'time'
    if abscissa and abscissa[0] == COORDINATE:
        return abscissa[1]
    if abscissa and abscissa[0] == DIMENSION:
        return 'its index' + ('[%s]' % abscissa[1] if abscissa[1] else '')
    return 'no abscissa'
