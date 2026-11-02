# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The strip a real shot offered as a picture, and the cuts it cannot answer.

Reported on WEST 54924 with `soft_x_rays`: "dragging the vertical marker leaves
the cut drawn in the bottom window unchanged". The leaf,
`channel(0).brightness.data`, is **one energy band by 6356 time samples** -- a
strip laid over a plane. Two windows were posed on it and read as swapped:

* the horizontal line stood on the energy band, so its interval was ``(0, 0)``
  and no drag moved it -- the window under it never changed, which is what the
  report is about;
* the vertical line stood on time and cut a single element, so its window held
  one point.

The ordering answers the swap: the window whose abscissa is the picture's own
horizontal axis goes directly under the pictures. The first cut of the *rule* went
further and asked the test of both halves of a line's question at once -- an
element to choose on the axis it stands on **and** one to draw along the axis its
cut runs along -- and because that test is symmetric, a strip lost **both**
windows. Which is the second report: « les fenetres montrant les slices x et y des
images ont disparu ». The refusal threw the answer away with the degeneracy -- the
line standing on the single band has nowhere to move, but the cut it takes is the
whole trace along time, exactly the curve the strip is worth drawing. A window is
therefore refused for what it holds (a cut of one point answers nothing), not for
whether its line can be dragged.

`test_34` pins the rule on a stub; this is the shot that produced both reports, so
the shape behind them is pinned too.

Skipped when the shot's pulse files are not mounted.
"""

import numpy as np
import pyqtgraph as pg
import pytest

from conftest import CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip

from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot

from support.caseTrees import (elementByTreePath, loadCaseTrees,
                               nodeAsTheBuilderBuildsIt)
from support.fakes import FakeTreeView

IDS_NAME = 'soft_x_rays'
# The road as the shot view walks it: an occurrence of the channel array carries
# its index, the leaf text stops at the structure.
PATH = 'soft_x_rays/channel(0)/brightness/data'
BANDS, SAMPLES = 1, 6356


@pytest.fixture(scope='module')
def case(qapp, request):
    """The shadow tree and the runtime IDS, walked once for all tests."""
    uri = case_uri_or_skip()
    if uri is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    return loadCaseTrees(qapp, (IDS_NAME,), uri=uri,
                         dd_version=CASE_DATA_DICTIONARY_VERSION,
                         label='west 54924', request=request)


@pytest.fixture
def brightness(qapp, case):
    """The leaf as the tree builder would put it on the screen."""
    view = FakeTreeView(uri=case['uri'])
    view.dataSource = QVizIMASDataSource('west 54924', case['uri'])
    element, path = elementByTreePath(case['trees'][IDS_NAME], IDS_NAME, PATH)
    return nodeAsTheBuilderBuildsIt(element, IDS_NAME, case['runtime'][IDS_NAME],
                                    view, path=path)


@pytest.mark.case
def test_the_shot_offers_a_picture_one_element_wide(case):
    """The shape the report came from, pinned so this file cannot drift."""
    data = np.asarray(case['runtime'][IDS_NAME].channel[0].brightness.data,
                      dtype=float)

    assert data.shape == (BANDS, SAMPLES), (
        'the strip is what makes the cuts below impossible; if the shot stopped '
        'being one, this file is asking about the wrong quantity')


@pytest.mark.case
def test_a_strip_keeps_the_window_holding_the_trace(qapp, brightness, case):
    """The window the disappearance report is about, on the shot that reported it.

    One line stands, and it is the one whose cut is a curve: the trace of the
    single band along the 6356 samples, laid out with its abscissa under the
    pictures' own horizontal scale.
    """
    frame = QVizImagePlot(title='Image:54924')
    try:
        frame.plot(brightness)

        assert frame.sliceLines.sides() == ['left']
        assert frame.sliceLines.isPosed()
        assert frame.sliceAxisLabel('left') == ('time', 's')
        x, y = frame.sliceNumbers('left')
        assert len(y) == SAMPLES
        expected = np.asarray(case['runtime'][IDS_NAME].channel[0].brightness.data,
                              dtype=float).flatten()
        np.testing.assert_allclose(np.asarray(y), expected)
        assert frame.sliceButtons.isVisibleTo(frame)
    finally:
        frame.close()


@pytest.mark.case
def test_the_window_that_would_hold_one_point_is_refused(qapp, brightness):
    frame = QVizImagePlot(title='Image:54924')
    try:
        frame.plot(brightness)

        assert 'bottom' not in frame.sliceLines.sides()
        with pytest.raises(KeyError):
            frame.slicePlot('bottom')
        # A `ColorBarItem` is a `PlotItem` (measured on 0.13.7), so what is left
        # on the figure has to be taken out by identity to say anything.
        left = [item for item in frame.pgPlotWidget.ci.items
                if isinstance(item, pg.PlotItem)
                and item is not frame.colorBar
                and all(item is not plot for plot in frame.plotItems())]
        assert frame.imageCount() >= 1
        assert left == [frame.slicePlot('left')], (
            'one line, one window -- and the window that is refused is the one '
            'holding a single value, not the trace')
        # The command row of the refused line goes with it.
        assert not frame._sliceLabels['bottom'].isVisibleTo(frame)
    finally:
        frame.close()


@pytest.mark.case
def test_the_line_on_the_single_band_has_one_place_to_stand(qapp, brightness):
    frame = QVizImagePlot(title='Image:54924')
    try:
        frame.plot(brightness)
        line = frame.sliceLines.line('left')

        line.setPos(SAMPLES)

        assert len(frame.sliceNumbers('left')[1]) == SAMPLES, (
            'the window is not stuck: it shows the only cut the strip has')
    finally:
        frame.close()


@pytest.mark.case
def test_the_strip_is_still_drawn(qapp, brightness):
    # Refusing half the cuts is not refusing the picture: the window still shows
    # it and still paints it with the colour scale of the figure.
    frame = QVizImagePlot(title='Image:54924')
    try:
        frame.plot(brightness)

        assert frame.isDrawing()
        assert frame.imageCount() >= 1
        assert frame.colourLevels() is not None
    finally:
        frame.close()
