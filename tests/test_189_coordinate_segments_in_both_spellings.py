# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""Every step of a coordinate loses its loop placeholder -- in either spelling.

The tree carries a coordinate with every '/' rewritten as a '.'
(buildNamedDataElement), so a leaf nested in two arrays of structures spells
it `antenna(i1).module(i2).power_launched.time`. The dictionary spells the same
coordinate `antenna(i1)/module(i2)/power_launched/time`. Both reach
coordinateSegments, which splits at '/' and then at '.'; the tail of that
second split was added in 290d516d to un-glue the steps after a closing
parenthesis -- 'time_slice(itime).grid.dim1' -- but the pieces it produced were
not normalized, so a placeholder in any step but the first stayed glued to its
name. `_axisValues` then reached `getattr(antenna_instance, 'module(i2)')` and
the IDS refused the leaf: the one plotable leaf of the antenna-level
`power_launched` in lh_antennas 65782 was "not drawable/lisible par les outils"
because of this.

Pinned here as pure arithmetic on the helper -- no case, no Qt.
"""

from imasviz.VizDataAccess.QVizIDSViewParser import coordinateSegments


def test_a_dot_spelled_coordinate_with_two_loop_placeholders():
    # The shape the lh_antennas module-level leaves actually carry -- the leaf
    # that died with "IDS structure 'antenna[0]' has no attribute 'module(i2)'".
    assert coordinateSegments('antenna(i1).module(i2).power_launched.time') == \
        ['antenna', 'module', 'power_launched', 'time']


def test_the_same_coordinate_slash_spelled():
    assert coordinateSegments('antenna(i1)/module(i2)/power_launched/time') == \
        ['antenna', 'module', 'power_launched', 'time']


def test_a_placeholder_in_the_last_step_is_dropped_too():
    assert coordinateSegments('antenna(i1).module(i2).data') == \
        ['antenna', 'module', 'data']


def test_a_placeholder_in_a_mid_step_of_a_long_path():
    assert coordinateSegments('time_slice(itime)/grid/dim1') == \
        ['time_slice', 'grid', 'dim1']


def test_a_plain_coordinate_is_left_alone():
    assert coordinateSegments('equilibrium/time_slice(itime)/grid') == \
        ['equilibrium', 'time_slice', 'grid']


def test_the_no_parentheses_plain_form():
    assert coordinateSegments('time') == ['time']
    assert coordinateSegments('antenna/module/data') == ['antenna', 'module', 'data']
