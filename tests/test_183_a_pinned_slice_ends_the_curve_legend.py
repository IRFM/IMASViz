# Copyright holders: Commissariat à l'Energie Atomique et aux Energies
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

"""The legend of a curve says the value its ask pinned.

The second half of the report: « ce serait bien que le libellé de chaque
courbe soit complété par la valeur de psi: (psi=30) par exemple a la fin de
chaque legende ». Measured on the reference case (WEST 54924 run 0, DD 3.35.0)
for the four-curve figure of « la pression pour psi=0, 30 60 et 100 », the four
legend entries were one and the same string,
`equilibrium.time_slice[itime].profiles_1d.pressure`: the four curves were four
different elements and the window said nothing to tell them apart.

`elementLabel` spells an index when nothing else on the figure says it. An
array of structures is spelled into the path (an element never has a control
for the arrays the tree stands on); a coordinate the caller pinned is now
appended after the path, `(psi=30)`, for the same reason -- the pinned
coordinate has no control at all since `test_182`. A coordinate the figure
carries on a control is not appended: the row of that control carries its index
on screen, and that is also why the legends of a tensor, whose axes are all
under sliders, stay as they were (`test_60`, `test_64`), except for a curve
*kept* under them -- frozen, and its whole index set is in its label.

The index is spelled, not the value of the coordinate: the psi grid of this
case belongs to a time slice, and the four curves of the ask share one slice
only by the path they were named with. A Wb figure taken from one slice and
printed on the four would be a lie for three of them.
"""

import pytest

from mcp_server.core import McpGuiCore

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)

IDS_NAME = 'equilibrium'
PRESSURE = 'equilibrium.time_slice[0].profiles_1d.pressure'
JTOR = 'equilibrium.time_slice[0].profiles_1d.j_tor'
SLICES = (0, 30, 60, 100)

pytestmark = [pytest.mark.case, pytest.mark.ui]


@pytest.fixture(scope='module')
def core(qapp, tmp_path_factory):
    """One self-contained session: the case open and equilibrium loaded."""
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('legendPinsValueHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    session = McpGuiCore()
    session.open_case(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    session.load_ids(CASE_URI, IDS_NAME, 0)
    try:
        yield session
    finally:
        for key in list(getattr(session.api, 'figureframes', []) or {}):
            try:
                session.close_window(key)
            except Exception:
                pass
        patch.undo()


def _legend(frame):
    """The legend texts of a curve figure, in the order the curves were drawn."""
    return [trace.legend.text for trace in frame.traces()
            if trace.legend is not None]


def _figure(core, *asks):
    """One figure, drawn by a sequence of `plot_one` asks. Only the first one
    opens it; the rest join it by key."""
    key = None
    for indices in asks:
        answer = core.plot_one(CASE_URI, PRESSURE, indices=indices,
                               into_figure_key=key)
        key = answer['figure']
    return core.api.figureframes[key]


def test_each_pinned_slice_ends_its_own_legend(core):
    """The ask itself: four psi slices, four legends, each ending on the index
    its own curve was pinned at."""
    frame = _figure(core, *({'psi': psi} for psi in SLICES))
    labels = _legend(frame)
    assert len(labels) == len(SLICES), labels
    for label, psi in zip(labels, SLICES):
        assert label.endswith('(psi=%d)' % psi), label
        assert label.startswith('equilibrium.time_slice'), label
    # The point of the suffix: the four curves are four elements, and before
    # this the window could not say which line was which.
    assert len(set(labels)) == len(SLICES), labels


def test_the_pinned_index_survives_a_refresh(core):
    """A legend is rewritten when a control moves a curve; a pinned row is not
    moved, and keeps the index it was named at."""
    frame = _figure(core, {'psi': 0}, {'psi': 100})
    before = _legend(frame)
    frame.refresh()
    assert _legend(frame) == before
    assert before == [
        'equilibrium.time_slice[itime].profiles_1d.pressure (psi=0)',
        'equilibrium.time_slice[itime].profiles_1d.pressure (psi=100)']


def test_a_coordinate_under_a_control_is_not_spelled_a_second_time(core):
    """The other half of the rule: what a control says is not put in the label.

    Nobody named psi here, so the figure sweeps it: one row under the figure
    carries the index, and the legend stays the path alone. That is the state
    the tree's element and a tensor are drawn in, and their legends are pinned
    bare by `test_60` and `test_64`.
    """
    answer = core.plot_one(CASE_URI, PRESSURE)
    frame = core.api.figureframes[answer['figure']]
    assert frame.sliceControls.sliceCount() == 1
    assert 'psi' in frame.sliceControls.summaryText()
    assert [label for label in _legend(frame)] == [
        'equilibrium.time_slice[itime].profiles_1d.pressure']
    key = list(frame.sliceControls.keys())[0]
    frame.sliceControls.setIndex(key, 40)
    assert _legend(frame) == [
        'equilibrium.time_slice[itime].profiles_1d.pressure'], _legend(frame)
    # The element the figure drew did move, and the row says where.
    assert '40' in frame.sliceControls.summaryText()


def test_two_quantities_pinned_at_one_index_each_say_their_own(core):
    """Two leaves of one structure pinned at the same index: the suffix names
    the element each curve is, so it appears on both and tells nothing apart
    that the path does not already say."""
    first = core.plot_one(CASE_URI, PRESSURE, indices={'psi': 20})
    second = core.plot_one(CASE_URI, JTOR, indices={'psi': 20},
                           into_figure_key=first['figure'])
    assert second['figure'] == first['figure']
    frame = core.api.figureframes[first['figure']]
    labels = _legend(frame)
    assert len(labels) == 2, labels
    assert all(label.endswith('(psi=20)') for label in labels), labels
    assert len(set(labels)) == 2, labels


def test_a_panel_spells_its_band_rather_than_a_suffix(core):
    """A panel of a stacked window pins its coordinate on a control it shows,
    so its legend stays the path with its array index -- no suffix, and the
    band row answers which slice the panel holds.

    The rule is one reading, not two: `elementLabel` appends what has no
    control, and a panel's coordinate has one.
    """
    from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPanel import QVizPanel
    answer = core.plot_stacked(CASE_URI, [PRESSURE], plot_axis='TIME')
    frame = core.api.figureframes[answer['figure']]
    panels = frame.findChildren(QVizPanel)
    assert panels, 'the stacked window drew no panel'
    for panel in panels:
        legend = panel.pgPlotWidget.getPlotItem().legend
        texts = [item.text for _, item in legend.items] if legend else []
        assert texts, 'a stacked panel draws a labelled curve'
        for text in texts:
            assert '(psi=' not in text, text
        assert panel.sliceControls.sliceCount() >= 1, \
            'the coordinate a panel pins is under a control it shows'
