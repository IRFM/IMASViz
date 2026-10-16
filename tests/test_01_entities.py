# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""VizEntities: the array handles every plot and every data access path uses."""

import numpy as np
import pytest

from imasviz.VizEntities.QVizDataArrayHandle import (ArrayCoordinates,
                                                     QVizDataArrayHandle,
                                                     QVizTimedDataArrayHandle)

from support.fakes import make_2d_array_handle


def test_dimension_is_the_number_of_coordinates():
    handle = make_2d_array_handle()
    assert handle.getArrayDimension() == 2


def test_coordinates_are_one_based():
    handle = make_2d_array_handle(x_size=100, y_size=200)
    assert handle.getCoordinateValues(1).size == 100
    assert handle.getCoordinateValues(2).size == 200
    assert handle.getCoordinatePath(1) == 'test.x'
    assert handle.getCoordinatePath(2) == 'test.y'
    assert handle.getCoordinateLabel(1) == 'x_label'


def test_time_coordinate_is_exposed():
    handle = make_2d_array_handle(timeCoordinateDim=2)
    assert handle.getTimeCoordinateDim() == 2
    np.testing.assert_allclose(handle.getTimeCoordinateArray(),
                               handle.getCoordinateValues(2))


def test_a_handle_without_time_coordinate_has_no_time_array():
    coordinates = ArrayCoordinates(['x'], [np.arange(5.)], None, ['x_label'])
    handle = QVizDataArrayHandle(coordinates, np.arange(5.), 'n', 'l')
    assert handle.getTimeCoordinateDim() is None
    assert handle.getTimeCoordinateArray() is None


def test_name_and_label_are_kept():
    handle = make_2d_array_handle(name='ion_temperature')
    assert handle.getName() == 'ion_temperature'
    assert handle.getLabel() == 'label of ion_temperature'


def test_values_are_not_copied_nor_reordered():
    handle = make_2d_array_handle()
    assert handle.arrayValues.shape == (100, 200)
    assert handle.arrayValues.dtype == np.float64


def test_timed_handle_pairs_values_with_a_time_array():
    timeArray = np.arange(5.)
    values = np.ones((5, 3))
    handle = QVizTimedDataArrayHandle(values, timeArray)
    assert handle.timeArray is timeArray
    assert handle.arrayValues.shape == (5, 3)
