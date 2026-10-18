# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The slice controls, driven from the axes model rather than from a flag.

The point of these tests is the contract between a plot and its controls, not
their pixels: one control per fixed axis, each naming the axis and saying where
in it the numbers come from, and the values coming back as the mapping a read
takes. Nothing here opens a case or a data dictionary -- the slices are built by
hand from the model, which is also how a rank 3 quantity gets tested when no
reference case on this checkout has one filled with values.

Written as new code against QVizSlices. The slider the plot frames carry today
(QVizPlotWidget.sliderGroup) is not touched, extended or compared: it is built
before any quantity is known and offers one control picked by two flags, so
neither its count nor its wiring can describe a quantity with three axes.
"""

import pytest

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec
from imasviz.VizDataAccess.QVizSlices import slicesFor
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizSliceControls import QVizSliceControls

from support.fakes import FakeAxesNode

AOS, LEAF = 'AOS', 'LEAF'


def _rank3Axes():
    """profiles_1d[itime].ion[j].z_ion_1d: rank 3, the curve draws time."""
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    node = FakeAxesNode(ids, 'foo', 'foo.profiles_1d[itime].ion[j]', 'FLT_1D',
                        name='z_ion_1d', itimeIndex=0, coordinates=('1..N',),
                        indices={'i': '0', 'j': '1'}, lengths={'i': '2', 'j': '2'})
    return QVizAxesSpec.fromTreeNode(node)


def _slicesThePlotFixes(lengths=None):
    """The two axes a time curve leaves out: the ion array and the radial point."""
    return slicesFor(_rank3Axes(), plottedPositions=(0,),
                     lengths=lengths or {(AOS, 2): 2, (LEAF, 1): 3})


@pytest.fixture
def controls(qtbot):
    widget = QVizSliceControls()
    qtbot.addWidget(widget)
    return widget


@pytest.mark.ui
def test_one_control_per_axis_the_plot_fixes(controls):
    controls.setSlices(_slicesThePlotFixes())

    assert controls.keys() == [(AOS, 2), (LEAF, 1)]


@pytest.mark.ui
def test_a_control_says_which_axis_it_moves_and_where_in_it(controls):
    # A user comparing two plots has to be able to tell which ion the curve came
    # from. A bare handle position does not say, and neither does a control that
    # is not there at all.
    controls.setSlices(_slicesThePlotFixes())
    rows = controls.rows()

    assert [row.nameLabel.text() for row in rows] == ['ion:', 'dimension 1:']
    assert [row.indexLabel.text() for row in rows] == ['1 / 1', '0 / 2']
    assert [row.slider.maximum() for row in rows] == [1, 2]


@pytest.mark.ui
def test_the_values_come_back_as_the_mapping_a_read_takes(controls):
    controls.setSlices(_slicesThePlotFixes())

    assert controls.indices() == {(AOS, 2): 1, (LEAF, 1): 0}


@pytest.mark.ui
def test_moving_a_control_says_so_and_changes_the_mapping(controls, qtbot):
    # The plot frame redraws on the signal and reads the new index from
    # indices(); if either half were missing, the control would be decoration.
    controls.setSlices(_slicesThePlotFixes())

    with qtbot.waitSignal(controls.changed, timeout=1000):
        controls.rows()[0].slider.setValue(0)

    assert controls.indices() == {(AOS, 2): 0, (LEAF, 1): 0}
    assert controls.rows()[0].indexLabel.text() == '0 / 1'


@pytest.mark.ui
def test_a_rebuild_keeps_the_choice_for_an_axis_that_is_still_there(controls):
    # A time slice redraw calls setSlices again. Resetting the user to index 0
    # each time would move a plot they were comparing from under their hand.
    controls.setSlices(_slicesThePlotFixes())
    controls.setIndex((LEAF, 1), 2)

    controls.setSlices(_slicesThePlotFixes())

    assert controls.indices() == {(AOS, 2): 1, (LEAF, 1): 2}


@pytest.mark.ui
def test_a_kept_choice_is_clamped_when_the_axis_got_shorter(controls):
    # The usual reason a length shrinks is another quantity in the same array.
    # Keeping index 2 of a 1-value axis would hand the read an index it rejects.
    controls.setSlices(_slicesThePlotFixes())
    controls.setIndex((LEAF, 1), 2)

    controls.setSlices(_slicesThePlotFixes(lengths={(AOS, 2): 2, (LEAF, 1): 1}))

    assert controls.indices() == {(AOS, 2): 1, (LEAF, 1): 0}


@pytest.mark.ui
def test_an_axis_that_gone_away_does_not_carry_its_old_index(controls):
    # A curve then an image: (AOS, 2) is fixed for the curve and drawn for the
    # image. Carrying its index over would pin an unrelated axis with the same
    # key shape on a quantity that no longer has it.
    controls.setSlices(_slicesThePlotFixes())
    controls.setIndex((AOS, 2), 1)

    controls.setSlices(slicesFor(_rank3Axes(), plottedPositions=(0, 1),
                                 lengths={(LEAF, 1): 3}))

    assert controls.keys() == [(LEAF, 1)]
    assert controls.indices() == {(LEAF, 1): 0}


@pytest.mark.ui
def test_a_single_value_axis_is_still_named_and_not_movable(controls):
    # One ion in the array: nothing to move, but the curve still belongs to that
    # ion, and saying so is half of what the control is for.
    controls.setSlices(_slicesThePlotFixes(lengths={(AOS, 2): 1, (LEAF, 1): 3}))

    assert controls.keys() == [(AOS, 2), (LEAF, 1)]
    assert not controls.rows()[0].slider.isEnabled()
    assert controls.rows()[0].nameLabel.text() == 'ion:'


@pytest.mark.ui
def test_an_axis_of_unknown_length_offers_no_range_but_stays_visible(controls):
    controls.setSlices(_slicesThePlotFixes(lengths={(AOS, 2): None, (LEAF, 1): 3}))

    assert not controls.rows()[0].slider.isEnabled()
    # Still the index the read uses, so the plot says where it is even when
    # there is no range to move it through.
    assert controls.rows()[0].indexLabel.text() == '1'
    assert controls.indices() == {(AOS, 2): 1, (LEAF, 1): 0}


@pytest.mark.ui
def test_a_plot_that_fixes_nothing_gets_no_controls_and_no_strip(controls):
    # A 0D quantity in the dynamic array: time is drawn, nothing is pinned. The
    # widget then takes no space, rather than a frame around nothing.
    controls.setSlices([])

    assert controls.sliceCount() == 0
    assert controls.indices() == {}
    assert not controls.isVisible()


@pytest.mark.ui
def test_setting_an_index_the_axis_does_not_have_is_refused(controls):
    controls.setSlices(_slicesThePlotFixes())

    assert not controls.setIndex((LEAF, 7), 0)
    assert controls.indices() == {(AOS, 2): 1, (LEAF, 1): 0}
