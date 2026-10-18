# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The coordinates a structure declares, carried down to the arrays it holds.

The dictionary writes a coordinate twice over. hard_x_rays.channel[i1].radiance
declares coordinate1 = channel(i1)/energy_band and coordinate2 =
channel(i1)/radiance/time, and the array inside it spells the same two
dimensions 1..N and channel(i1)/radiance/time: the leaf names the axis it shares
and leaves the other one anonymous. Walking only what the leaf itself spells --
which is what the parser did -- loses the first dimension of 1 570 of the
dimensions the dictionary actually names in version 3.35.0, and an axis that
names nothing is drawn as 'dimension 1'.

Inheriting by dimension number is what breaks it, because a structure holds
arrays of several ranks: radiance declares two coordinates and holds both a 2D
'data' and a 1D 'time', so 'time' would be handed 'energy_band' as its axis. The
guard below is the one the recensement supports -- a declaration describes an
array with as many dimensions as it spells -- and it rejects the 7 556 dimensions
whose ranks disagree.

These tests walk stubs, because the rule is arithmetic on the dictionary, not
something a case adds. tests/test_28_radiance_case.py shows the same rule on the
dictionary written by someone else.
"""

import xml.etree.ElementTree as ET

import pytest

from imasviz.VizDataAccess.QVizAxesSpec import (QVizAxesSpec, isUnboundedCoordinate)
from imasviz.VizDataAccess.QVizIDSViewParser import (inheritCoordinates,
                                                     structureCoordinates)

BAND = 'channel(i1)/energy_band'
RADIANCE_TIME = 'channel(i1)/radiance/time'


class StubMetaData:
    """Enough of IDSMetadata for the two helpers: a name and coordinateN fields.

    The real object leaves .coordinates empty for a structure and answers
    coordinate1 / coordinate2 instead -- which is the whole reason this
    inheritance exists -- so the stub keeps both spellings apart.
    """

    def __init__(self, name, coordinates=(), attributes=()):
        self.name = name
        self.coordinates = list(coordinates)
        for number, spelling in enumerate(attributes, start=1):
            setattr(self, 'coordinate%d' % number, spelling)


# ---------------------------------------------------------------- the reading

def test_a_structure_declares_its_coordinates_on_attributes_not_the_list():
    radiance = StubMetaData('radiance',
                            attributes=(BAND, RADIANCE_TIME))

    assert structureCoordinates(radiance) == [BAND, RADIANCE_TIME]


def test_a_structure_that_declares_nothing_gives_nothing():
    assert structureCoordinates(StubMetaData('gap')) == []
    assert structureCoordinates(StubMetaData('gap', attributes=(''))) == []


def test_a_rank_range_spelling_names_no_axis():
    # The dictionary also spells an axis 1..9 when it counts the elements without
    # naming a node: inheriting it would label the axis '9'.
    assert isUnboundedCoordinate('1...N')
    assert isUnboundedCoordinate('1///N')
    assert isUnboundedCoordinate('1...9')
    assert not isUnboundedCoordinate(BAND)


def test_an_axis_named_by_a_rank_range_stays_an_axis_of_ranks():
    element = ET.Element('data')
    element.text = 'foo.data'
    element.set('data_type', 'FLT_1D')
    element.set('aos_parents_count', '0')
    element.set('parametrizedPath', 'foo')
    element.set('itime_index', '-1')
    element.set('coordinate1', '1///9')
    axis = QVizAxesSpec.fromShadowElement(element, idsName='foo').axes[0]

    assert axis.isUnbounded()


# ---------------------------------------------------------------- the guard

def test_an_anonymous_dimension_takes_the_declaration_of_the_structure_it_sits_in():
    own = ['1...N', RADIANCE_TIME]

    assert inheritCoordinates(own, [[BAND, RADIANCE_TIME]]) == [BAND, RADIANCE_TIME]


def test_a_dimension_the_leaf_names_himself_is_not_replaced():
    own = ['channel(i1)/radiance/wavelengths', RADIANCE_TIME]

    assert inheritCoordinates(own, [[BAND, 'something_else']]) == own


def test_a_declaration_of_another_rank_names_nothing():
    # radiance declares two coordinates and holds a 1D 'time' as well as a 2D
    # 'data': handing 'time' the first of the two calls a time axis an energy
    # band, and a picture labelled that way is worse than one labelled nothing.
    assert inheritCoordinates(['1...N'], [[BAND, RADIANCE_TIME]]) == ['1...N']


def test_the_declaration_of_the_closest_structure_is_the_one_that_applies():
    own = ['1...N', '1...N']
    nearest = ['channel(i1)/radiance/time', BAND]
    further = ['equilibrium.time', 'something']

    assert inheritCoordinates(own, [nearest, further]) == nearest


def test_a_further_structure_names_what_the_closest_one_leaves_unnamed():
    own = ['1...N', '1...N']
    nearest = [RADIANCE_TIME, '']
    further = ['foo.wavelength', '']

    assert inheritCoordinates(own, [nearest, further]) == [RADIANCE_TIME, '1...N']


def test_an_anonymous_declaration_names_nothing():
    own = ['1...N', '1...N']

    assert inheritCoordinates(own, [['1...9', RADIANCE_TIME]]) == ['1...9', RADIANCE_TIME]


def test_nothing_is_invented_when_no_structure_declares_anything():
    own = ['1...N', '1...N']

    assert inheritCoordinates(own, []) == own
