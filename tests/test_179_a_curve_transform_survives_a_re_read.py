# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A transform a hand put on a curve is part of the figure, not of one item.

The curve transforms -- `scale_curve`, `shift_curve`, `normalize_curve` and their
inverse `reset_curve`, reached from the tool surface as
`transform_curve(operation=...)` -- were painted on the pyqtgraph item:
`item.setData(x, y * factor)`, and for the inverse the previous (x, y) stashed on
the item under a private marker. Nothing in the figure knew a value had been
touched.

That is enough for the gestures that only *add* -- and it was measured to be
enough, on this case: a normalised `magnetics/flux_loop(0)/flux/data` keeps its
`(max, min) = (1.0, -0.5371)` when a second quantity joins the same window,
whether it joins through `plot(mode="into")` or through the tree's *Plot this
node to* entry on that figure (`QVizPlotOneNode(intoFigureKey=...)`).

It is not enough for the gestures that *re-read*. `QVizCurvePlot.refresh` re-reads
every curve that follows a control and hands what it read straight to `setData`,
so any index move -- a hand dragging a slider, `set_slice_index`, or
`plot(mode="into", indices=...)` posing a row there -- drew the window back at
its raw scale. Measured before this change, on the tensor figure of that same
flux (one row, `flux_loop`, 17 elements): normalised to `(1.0, -0.5371)`, then
the row posed at index 2, and the curve answered `(8.2487, -4.3935)` -- the
values the case holds, the hand's division forgotten and nothing said about it.
The only curve that kept its scale was one frozen by *Keep this curve*, because
a frozen curve is not re-read at all.

So the transform moves onto the trace: the figure keeps the values it read and
the (factor, offset) a hand laid on them, and every re-read goes back through
them. Two consequences the tests below pin, both of them the meaning of a factor:

* the factor is settled when the hand asks, and stays. Move the row and the
  curve is the element it is now, multiplied by the same factor -- not
  re-normalised to its own new peak, which would make the picture answer a
  question nobody asked;
* the transform belongs to the trace it was asked on. A quantity that joins the
  window afterwards is drawn as the case holds it.

What stays open, and is not fixed here: a saved session has no element for a
transform (a `<Figure>` holds `<Style>`, `<ColourScale>`, `<View>`, `<Cursors>`,
`<Errors>`), so a window put back from a `.vsess` comes at its raw scale.
"""

import pytest

import numpy as np

from mcp_server.core import McpGuiCore

from conftest import CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip
from support import ownership

IDS_NAME = 'magnetics'
FLUX0 = 'magnetics.flux_loop[0].flux.data'
BPOLO = 'magnetics.bpol_probe[0].field.data'
# The array of structures the tensor figure of that flux puts under a slider:
# 17 elements on the reference case. It is the row the gesture moves.
ROW = 'flux_loop'
MOVED_TO = 3

pytestmark = [pytest.mark.case, pytest.mark.ui]


@pytest.fixture(scope='module')
def core(qapp, tmp_path_factory):
    """One agent session on the reference case, $HOME patched apart.

    The same pattern as `test_137`: these transforms write nothing, but the
    session they belong to must not reach the real `~/.imasviz` either.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('transformHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    session = McpGuiCore()
    try:
        yield session
    finally:
        patch.undo()


def drawn(frame, index=0):
    """The values one curve of the window is drawn with, as pyqtgraph holds them."""
    _x, y = frame._curves[index].curve.getData()
    return np.asarray(y, dtype=float)


def rowOf(frame, word=ROW):
    """The row of the band that answers to that axis word, as the gesture does."""
    for row in frame.sliceControls.rows():
        if word in (str(row.label).lower(), str(row.key).lower()):
            return row
    raise AssertionError('the window holds no row "%s": %s'
                         % (word, [r.label for r in frame.sliceControls.rows()]))


def tensorFigure(session, path=FLUX0):
    """The figure of *Explore this tensor* -- one curve, and a row to move.

    A plain element of `magnetics` read along time holds no control at all
    (measured: no rows), so it cannot show what a re-read costs. The tensor
    entry is the one that puts the array of structures under a slider, and it
    is the window the report was made on.
    """
    from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
        import QVizPlotOneNode

    view = next(iter(session.api.DTVlist))
    node = session._nodeForPath(view, path)
    frame = QVizPlotOneNode(dataTreeView=view, treeNode=node,
                            tensor=True).execute()
    assert frame is not None, 'the tensor entry drew nothing for %s' % path
    ownership.keep(frame)
    return frame, session.api.GetFigureKeyOf(frame)


# =================================================================== a re-read


def test_the_tensor_figure_opens_with_a_row_to_move(core):
    session = core
    session.open_case(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    session.load_ids(CASE_URI, IDS_NAME, 0)
    frame, _key = tensorFigure(session)
    row = rowOf(frame)
    assert row.length == 17, row
    assert row.index() == 0, row


def test_a_scaled_curve_keeps_its_factor_across_a_row_move(core):
    """The scale is the trace's factor, not a coat of paint on one read."""
    session = core
    frame, key = tensorFigure(session)
    session.scale_curve(key, 2.0, curve=0)
    scaled = drawn(frame)
    session.set_slice_index(key, ROW, MOVED_TO)
    moved = drawn(frame)
    # The re-read really happened: another element of the array, other numbers.
    assert not np.allclose(moved, scaled), 'the row move re-read nothing'
    session.reset_curve(key, curve=0)
    raw = drawn(frame)
    assert not np.allclose(raw, scaled), 'reset restored the scaled values'
    assert np.allclose(moved, 2.0 * raw), \
        'the factor was lost when the row moved: %s against 2 x %s' \
        % (moved[:3], raw[:3])


def test_a_normalised_curve_keeps_its_reference_across_a_row_move(core):
    """The reference was read off the curve as it stood; the element under it
    may change, the division does not."""
    session = core
    frame, key = tensorFigure(session)
    reference = session.normalize_curve(key, mode='max', curve=0)['reference']
    assert abs(drawn(frame).max() - 1.0) < 1e-12, 'not normalised at the start'
    session.set_slice_index(key, ROW, MOVED_TO)
    moved = drawn(frame)
    session.reset_curve(key, curve=0)
    raw = drawn(frame)
    assert np.allclose(moved * reference, raw), \
        'the division by %g was forgotten when the row moved' % reference


def test_a_shift_survives_a_row_move_too(core):
    session = core
    frame, key = tensorFigure(session)
    session.shift_curve(key, 25.0, curve=0)
    shifted = drawn(frame)
    session.set_slice_index(key, ROW, MOVED_TO)
    moved = drawn(frame)
    session.reset_curve(key, curve=0)
    raw = drawn(frame)
    assert np.allclose(moved, raw + 25.0), \
        'the shift was forgotten when the row moved'
    assert not np.allclose(shifted, moved)


def test_a_scale_and_a_shift_compose_across_a_row_move(core):
    """Scale then shift is one (factor, offset), and a re-read applies it once."""
    session = core
    frame, key = tensorFigure(session)
    session.scale_curve(key, 3.0, curve=0)
    session.shift_curve(key, 10.0, curve=0)
    session.set_slice_index(key, ROW, MOVED_TO)
    moved = drawn(frame)
    session.reset_curve(key, curve=0)
    raw = drawn(frame)
    assert np.allclose(moved, 3.0 * raw + 10.0), \
        'the composed transform was not re-applied to the values just read'


# ================================================== what the fix must not change


def test_a_curve_added_after_a_transform_is_drawn_as_the_case_holds_it(core):
    """The transform is the trace's, not the window's: a quantity that joins
    afterwards is not divided by the first one's peak."""
    session = core
    frame, key = tensorFigure(session)
    session.normalize_curve(key, mode='max', curve=0)
    session.plot_one(CASE_URI, BPOLO, along_time=True, into_figure_key=key)
    assert frame.curveCount() == 2, frame.curveCount()
    assert abs(drawn(frame, 0).max() - 1.0) < 1e-12, \
        'the normalised curve lost its scale when a curve joined'
    assert abs(drawn(frame, 1).max() - 1.0) > 1e-9, \
        'the curve that joined came back normalised too'


def test_a_normalised_curve_survives_a_curve_joining(core):
    """The gesture the report named, measured: adding a curve never re-reads
    the ones already on the window -- the two entries that join one."""
    from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
        import QVizPlotOneNode

    session = core
    key = session.plot_one(CASE_URI, FLUX0, along_time=True)['figure']
    frame = session.api.figureframes[key]
    session.normalize_curve(key, mode='max', curve=0)
    session.plot_one(CASE_URI, BPOLO, along_time=True, into_figure_key=key)
    assert abs(drawn(frame, 0).max() - 1.0) < 1e-12, \
        'plot(mode="into") re-read the normalised curve'

    view = next(iter(session.api.DTVlist))
    leaf = session._nodeForPath(view, 'magnetics.flux_loop[5].flux.data')
    ownership.keep(QVizPlotOneNode(dataTreeView=view, treeNode=leaf,
                                   intoFigureKey=key,
                                   alongTime=True).execute())
    assert frame.curveCount() == 3, frame.curveCount()
    assert abs(drawn(frame, 0).max() - 1.0) < 1e-12, \
        'the tree entry that joins a figure re-read the normalised curve'


def test_reset_after_a_row_move_gives_the_new_element_back(core):
    """`reset_curve` takes the transform off the values the window holds *now*:
    the element the row is posed at, not the one the hand started on."""
    session = core
    frame, key = tensorFigure(session)
    before = drawn(frame).copy()
    session.scale_curve(key, 4.0, curve=0)
    session.set_slice_index(key, ROW, MOVED_TO)
    session.reset_curve(key, curve=0)
    after = drawn(frame)
    assert not np.allclose(after, before), 'the re-read did not move the element'
    assert not np.allclose(after, before * 4.0), 'reset left the factor on'
