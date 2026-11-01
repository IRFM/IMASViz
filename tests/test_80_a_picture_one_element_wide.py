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
strip laid over a plane. Two windows were posed on it and neither could answer:

* the horizontal line stood on the energy band, so its interval was ``(0, 0)``
  and no drag moved it -- the window under it never changed, which is what the
  report is about;
* the vertical line stood on time and cut a single element, so its window held
  one point.

The two read as swapped windows; they are one degenerate picture. A line is worth
posing only when both halves of its question can be asked -- more than one
element to choose on the axis it stands on, more than one to draw along the axis
its cut runs along -- and that test is symmetric, so a strip poses no line at all.
`test_34` pins the rule on a stub; this is the shot that reported it, so the shape
that produced the report is pinned too.

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
def test_a_strip_poses_no_line_and_no_window(qapp, brightness):
    frame = QVizImagePlot(title='Image:54924')
    try:
        frame.plot(brightness)

        assert frame.sliceLines.sides() == []
        assert not frame.sliceLines.isPosed()
        # A `ColorBarItem` is a `PlotItem` (measured on 0.13.7), so what is left
        # on the figure has to be taken out by identity to say anything.
        left = [item for item in frame.pgPlotWidget.ci.items
                if isinstance(item, pg.PlotItem)
                and item is not frame.colorBar
                and all(item is not plot for plot in frame.plotItems())]
        assert frame.imageCount() >= 1
        assert left == [], (
            'a window under a line nobody can drag answers nothing')
        assert not frame.sliceButtons.isVisibleTo(frame), (
            'a bar of slice commands with no slice to keep is a strip of grey')
    finally:
        frame.close()


@pytest.mark.case
def test_the_strip_is_still_drawn(qapp, brightness):
    # Refusing the cut is not refusing the picture: the window still shows it and
    # still paints it with the colour scale of the figure.
    frame = QVizImagePlot(title='Image:54924')
    try:
        frame.plot(brightness)

        assert frame.isDrawing()
        assert frame.imageCount() >= 1
        assert frame.colourLevels() is not None
    finally:
        frame.close()
