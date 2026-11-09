# Copyright holders : Commissariat à l'Energie Atomique et aux Energies
# Alternatives (CEA), France; and Laboratory for Engineering Design - LECAD,
# University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C
# open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted
# upon downloading the software and/or exercising any of the rights granted
# under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The one addressing of a quantity: which axis it runs along, and which index
each other axis is fixed at.

Before this, the read and the figure each answered the question on their own:
`get_signal` read a leaf at one `coordinate_index`, `plot_one` drew it at the
index the tree happened to carry, and a figure and its numbers could disagree
about the very same element. Measured on WEST 54924: `get_signal` answered
`equilibrium.time_slice[0].profiles_1d.j_tor` at `psi[50]` (49 points, min
158 618 A/m²) while `plot_one` opened its slider at `psi[0]` and reported the
`psi[50]` numbers underneath it.

`axesAddressing` is the shared answer: given the axes of the quantity
(`QVizAxesSpec`), the axis the quantity runs along (`along`), and the index
each other axis is fixed at (`indices`), it returns the `abscissa` identity,
the `as_function_of_time` flag and the `slices` mapping the read already
consumes (`QVizTensorDataAccess.GetSignal`). Both the read (`get_signal`) and
the figure (`plot_one`) route through this, so they cannot name one element
and draw another.

It is a read of the axes only: no case open, no data read, no Qt. The extent
checks it can do use the length the tree carries for an array of structures;
a leaf axis the dictionary leaves unbounded is left for the read to validate
against the values.
"""

import xml.etree.ElementTree as ET

import pytest

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec, QVizAxis
from imasviz.VizDataAccess.QVizCurveAbscissa import TIME
from imasviz.VizAgent.core import axesAddressing

# The walk's loop letters and extents, spelled out: the AOS axes take their
# length from the same attributes `QVizAxesSpec.fromShadowElement` reads.
_INDICES = {1: 'i', 2: 'j', 3: 'k', 4: 'l', 5: 'q', 6: 'r', 7: 't'}
_MAX = {1: 'N', 2: 'M', 3: 'K', 4: 'L', 5: 'Q', 6: 'R', 7: 'T'}


def leaf(dataType, parametrizedPath, aosParents=0, timeLevel=0, timeLength=7,
         coordinate=None, text='x.y'):
    """A shadow tree leaf as `QVizIDSViewParser.buildLeaf` leaves it."""
    element = ET.Element('name')
    element.text = text
    element.set('data_type', dataType)
    element.set('aos_parents_count', str(aosParents))
    element.set('parametrizedPath', parametrizedPath)
    if timeLevel:
        element.set('itime_index', str(timeLevel - 1))
    else:
        element.set('itime_index', '-1')
    if coordinate is not None:
        element.set('coordinate1', coordinate)
    for level in range(1, aosParents + 1):
        element.set(_INDICES[level], '0')
        if level == timeLevel:
            element.set(_MAX[level], str(timeLength))
        else:
            element.set(_MAX[level], '7')
    return element


def spec(**kwargs):
    return QVizAxesSpec.fromShadowElement(leaf(**kwargs), idsName='equilibrium')


# A 1D profile held by the dynamic array: one axis to run along (the clock,
# the `time_slice` array), one axis to fix (the leaf's own coordinate, `psi`).
# This is the shape of `equilibrium.time_slice[i].profiles_1d.j_tor`.
def jtor():
    return spec(
        dataType='FLT_1D',
        parametrizedPath='equilibrium.time_slice[itime].profiles_1d',
        aosParents=1,
        timeLevel=1,
        timeLength=7,
        coordinate='equilibrium.time_slice[0].profiles_1d.psi',
        text='equilibrium.time_slice[i].profiles_1d.j_tor')


def _psiAxis(s):
    return [a for a in s.axes if a.origin == QVizAxis.LEAF][0]


def test_drawn_along_time_fixes_the_leaf_at_the_index_named(qapp):
    """`j_tor` along time at `psi[50]`: the clock is drawn, `psi` is fixed at 50."""
    s = jtor()
    abscissa, as_function_of_time, slices = axesAddressing(s, along=None,
                                                            indices={'psi': 50})
    assert abscissa == TIME
    assert as_function_of_time is True
    # The leaf axis is fixed at 50; the dynamic array is the abscissa, not a
    # slice, so it is not in the mapping.
    assert slices[_psiAxis(s).key()] == 50
    assert len(slices) == 1


def test_along_is_a_spelling_not_the_leaf(qapp):
    """Naming the clock by any of its spellings settles on the same abscissa."""
    s = jtor()
    for along in (None, 'time', 'temps', 'time_slice'):
        abscissa, as_function_of_time, slices = axesAddressing(s, along=along,
                                                               indices={'psi': 3})
        assert abscissa == TIME
        assert as_function_of_time is True
        assert slices[_psiAxis(s).key()] == 3


def test_drawn_along_a_coordinate_pins_the_dynamic_array(qapp):
    """`j_tor` along `psi`, at `time_slice[2]`: the leaf is drawn, the array
    is fixed at 2, and it runs along a coordinate, not the clock."""
    s = jtor()
    abscissa, as_function_of_time, slices = axesAddressing(s, along='psi',
                                                           indices=None)
    assert abscissa != TIME
    assert as_function_of_time is False
    # The dynamic array is the one sliced; the leaf is the abscissa, so it is
    # not in the mapping.
    timeAxis = [a for a in s.axes if a.origin == QVizAxis.AOS][0]
    assert slices[timeAxis.key()] == 0
    assert _psiAxis(s).key() not in slices


def test_nested_arrays_are_each_fixed_by_index(qapp):
    """`equilibrium.time_slice[i].profiles_1d[k]...`: a quantity in the dynamic
    array AND a static array of structures AND a leaves's own coordinate fixes
    every non-drawn axis by name at its own index."""
    s = spec(
        dataType='FLT_1D',
        parametrizedPath='equilibrium.time_slice[itime].profiles_1d[i].ion[j]',
        aosParents=3,
        timeLevel=1,
        timeLength=7,
        coordinate='equilibrium.time_slice[0].profiles_1d[0].ion[0].f',
        text='equilibrium.time_slice[i].profiles_1d[k].ion[j].f')
    abscissa, as_function_of_time, slices = axesAddressing(
        s, along=None, indices={'ion': 4, 'f': 2})
    assert abscissa == TIME
    assert as_function_of_time is True
    # Every axis but the dynamic array is in the mapping. The two the user
    # named hold their own index; the static array `profiles_1d`, neither named
    # nor drawn, holds its own index 0.
    leafKey = [a.key() for a in s.axes if a.origin == QVizAxis.LEAF][0]
    ionKey = [a.key() for a in s.axes
              if a.origin == QVizAxis.AOS and not a.is_time
              and str(getattr(a, 'name', '')) == 'ion'][0]
    assert slices[leafKey] == 2
    assert slices[ionKey] == 4
    notDrawn = {a.key() for a in s.axes
                if a.origin == QVizAxis.AOS and not a.is_time}
    assert notDrawn.issubset(slices) and notDrawn, (notDrawn, slices)


@pytest.mark.parametrize('call', [
    # `along` names an axis the quantity cannot run along.
    dict(along='magnetic_field', indices=None),
    # An `indices` key names an axis the quantity does not hold.
    dict(along=None, indices={'flux_loop': 0}),
    # An index out of the extent of an array of structures.
    dict(along=None, indices={'ion': 9}),
])
def test_refusals_are_named(qapp, call):
    s = spec(
        dataType='FLT_1D',
        parametrizedPath='equilibrium.time_slice[itime].profiles_1d[i].ion[j]',
        aosParents=3,
        timeLevel=1,
        timeLength=7,
        coordinate='equilibrium.time_slice[0].profiles_1d[0].ion[0].f',
        text='equilibrium.time_slice[i].profiles_1d[k].ion[j].f')
    with pytest.raises(ValueError) as exc:
        axesAddressing(s, call['along'], indices=call.get('indices'))
    message = str(exc.value)
    # A refusal must say why: name the axis, the option, or the extent, not a
    # bare traceback.
    assert message, 'the refusal must say why in words'
    if call['along'] == 'magnetic_field':
        assert 'magnetic_field' in message
    if call.get('indices') == {'flux_loop': 0}:
        assert 'flux_loop' in message
    if call.get('indices') == {'ion': 9}:
        # The out-of-range refusal names the extent it failed against.
        assert '9' in message


def test_pinning_the_axis_a_curve_runs_on_is_refused(qapp):
    """A curve is drawn along one axis and pins the rest; pinning the abscissa
    itself is a contradiction the resolver must name, not a silent no-op."""
    s = jtor()
    # Along time, pinning `time_slice` (the array the curve walks) is refused.
    with pytest.raises(ValueError) as exc:
        axesAddressing(s, along=None, indices={'time_slice': 1})
    assert 'time_slice' in str(exc.value)
    # Along the leaf, pinning the leaf itself is refused.
    with pytest.raises(ValueError) as exc:
        axesAddressing(s, along='psi', indices={'psi': 1})
    assert 'psi' in str(exc.value)


def test_a_scalar_has_nothing_to_run_along(qapp):
    """A 0D leaf has no abscissa: the refusal names it, it does not invent one."""
    s = spec(dataType='FLT_0D', parametrizedPath='magnetics.bpol_probe[i]',
             aosParents=1)
    with pytest.raises(ValueError) as exc:
        axesAddressing(s, along=None, indices=None)
    assert '0D' in str(exc.value) or 'scalar' in str(exc.value).lower()
