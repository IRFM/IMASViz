# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Where a time coordinate gets its values, decided by homogeneous_time.

A leaf coordinate whose spelling ends in 'time' is a time base like any other,
and which one applies is set by ids_properties.homogeneous_time:

  homogeneous_time == 1  the base is IDS.time, for every dynamic quantity of
                         the IDS -- even when the coordinate spells a .time of
                         its own, and even when that array is empty.
  homogeneous_time == 0  the base is the spelled coordinate, which sits under
                         the element that carries the quantity:
                         b_field_tor_vacuum_r/time, ic/antenna(i1)/power/
                         reference/time. Nothing else may stand in for it.

The second case is where the old code went wrong: when the spelled time held no
values it fell back to IDS.time, which draws a curve against a clock the values
were never taken on. These tests hold a runtime object in memory rather than
opening a case, because the case at hand has no IDS where both halves of the
rule can be seen at once -- and the wrong half is exactly the one no real case
here exercises.
"""

import numpy as np
import pytest

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxis, QVizAxesSpec
from imasviz.VizDataAccess.QVizTensorExtractor import QVizTensorExtractor


def makeIds(homogeneousTime, idsTime, ownTime):
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = homogeneousTime
    ids.time = idsTime
    ids.bar = type(str('Bar'), (), {})()
    ids.bar.data = [10., 11., 12.]
    ids.bar.time = ownTime
    return ids


def leafSpec(coordinate='bar/time'):
    return QVizAxesSpec(
        [QVizAxis(origin=QVizAxis.LEAF, level=1, coordinate=coordinate,
                  units='s', is_time=True)],
        idsName='foo', dataPath='foo.bar.data', dataType='FLOAT_1D')


def test_a_time_coordinate_of_its_own_when_the_ids_is_not_homogeneous():
    ids = makeIds(0, [0., 1., 2.], [100., 101., 102.])
    tensor = QVizTensorExtractor(ids).extract(leafSpec())
    np.testing.assert_allclose(tensor.axesValues[0], [100., 101., 102.])


def test_a_time_coordinate_of_its_own_is_not_replaced_by_the_ids_time():
    # The point of the rule: the values under foo.bar.data were taken on the
    # clock in bar.time. Substituting IDS.time draws them against another one
    # and looks entirely normal while doing so.
    ids = makeIds(0, [0., 1., 2.], [100., 101., 102.])
    tensor = QVizTensorExtractor(ids).extract(leafSpec())
    assert not np.array_equal(tensor.axesValues[0], np.asarray(ids.time))


def test_an_empty_time_coordinate_of_its_own_stays_empty():
    # Nothing to plot on that axis. IDS.time is not a substitute when
    # homogeneous_time is 0, so the honest answer is that the axis has no
    # values -- not a borrowed clock.
    ids = makeIds(0, [0., 1., 2.], [])
    tensor = QVizTensorExtractor(ids).extract(leafSpec())
    assert tensor.axesValues[0] is None


def test_the_values_are_read_even_when_the_time_coordinate_is_empty():
    ids = makeIds(0, [0., 1., 2.], [])
    tensor = QVizTensorExtractor(ids).extract(leafSpec())
    np.testing.assert_allclose(tensor.values, [10., 11., 12.])


def test_a_homogeneous_ids_takes_the_ids_time_whatever_the_coordinate_spells():
    # This is what the reference case does: tf.b_field_tor_vacuum_r.time holds
    # no values there while IDS.time holds 17 344, and IDS.time is the right
    # answer because homogeneous_time is 1.
    ids = makeIds(1, [0., 1., 2.], [])
    tensor = QVizTensorExtractor(ids).extract(leafSpec())
    np.testing.assert_allclose(tensor.axesValues[0], [0., 1., 2.])


def test_a_homogeneous_ids_still_takes_the_ids_time_when_its_own_is_filled():
    ids = makeIds(1, [0., 1., 2.], [100., 101., 102.])
    tensor = QVizTensorExtractor(ids).extract(leafSpec())
    np.testing.assert_allclose(tensor.axesValues[0], [0., 1., 2.])


def makeIdsInDynamicArray(homogeneousTime, idsTime, arrayTimes):
    """A quantity directly under the dynamic array: one element per time."""
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = homogeneousTime
    ids.time = idsTime
    ids.slice = [type(str('Element'), (), {})() for _ in arrayTimes]
    for element, time in zip(ids.slice, arrayTimes):
        element.time = time
        element.value = 1.
    return ids


def dynamicArraySpec():
    """One axis, the dynamic array of structures -- spelled as the view spells it.

    The parametrized path names the dynamic level [itime] while the data path
    names the same level by its loop letter ([i]): that is what
    QVizIDSViewParser.buildLeaf does, replacing the letter of the time level
    with 'itime'. Comparing the two spellings to find the time level therefore
    never matches, and the array's own times go unread.
    """
    return QVizAxesSpec(
        [QVizAxis(origin=QVizAxis.AOS, level=1, placeholder='itime',
                  coordinate='foo.slice/time', units='s', length=3, is_time=True)],
        idsName='foo', dataPath='foo.slice[i].value', dataType='FLT_0D')


def test_the_dynamic_array_times_of_its_own_when_the_ids_is_not_homogeneous():
    # The other half of the rule: with homogeneous_time 0 the base of a
    # quantity held by the dynamic array is that array's own <aos>[i].time.
    ids = makeIdsInDynamicArray(0, [0., 1., 2.], [100., 101., 102.])
    tensor = QVizTensorExtractor(ids).extract(dynamicArraySpec())
    np.testing.assert_allclose(tensor.timeAxisValues(), [100., 101., 102.])


def test_a_homogeneous_array_of_structures_takes_the_ids_time():
    ids = makeIdsInDynamicArray(1, [0., 1., 2.], [100., 101., 102.])
    tensor = QVizTensorExtractor(ids).extract(dynamicArraySpec())
    np.testing.assert_allclose(tensor.timeAxisValues(), [0., 1., 2.])
