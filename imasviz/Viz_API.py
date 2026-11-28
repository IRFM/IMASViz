# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The session api: every window of a run, every figure, every view.

The class itself is an assembly of mixins -- one per responsibility --
that the framework reads and writes through the same object. Only state
and construction live here; the behaviour lives in the mixins.
"""

from imasviz.VizUtils import QVizPreferences
from imasviz.Viz_API_chrome import (getNodePath, figureDisplayHeading,
                                   titleWithCases, caseTooltip,
                                   DEFAULT_FIGURE_SIZE, QVizMdiSubWindow,
                                   QVizClosableWindow, QVizWindowRecord)
from imasviz.Viz_API_windows import QVizWindowBookkeepingMixin
from imasviz.Viz_API_figures import QVizFigureRegistryMixin
from imasviz.Viz_API_views import QVizShotViewsMixin
from imasviz.Viz_API_selection import QVizSelectionMixin
from imasviz.Viz_API_plotting import QVizPlottingMixin


class Viz_API(QVizWindowBookkeepingMixin, QVizFigureRegistryMixin,
              QVizShotViewsMixin, QVizSelectionMixin, QVizPlottingMixin):

    def __init__(self, parent=None):

        self.parent = parent

        self.figToNodes = {}  # key = figure, values = list of selected nodes
        # figureframes contains all plotting frames
        self.figureframes = {}  # key = FigureType + FigureKey,
        # example: FigureType="Figure:", FigureKey="1"
        self.DTVframeList = []
        self.DTVlist = []
        # The MDI area opens in windowed mode. If the preference says otherwise,
        # the first window a case opens into is the moment it is applied:
        # `mdiLayout` writes it back, the flag keeps the apply one-shot, and the
        # reset it does when no MDI answers means the next embed is another chance.
        self._layoutApplied = False

        QVizPreferences().build()

