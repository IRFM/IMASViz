# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A shot view and an api enough for a plot command, without a window.

The commands walk a tree view's selection and register the figures they draw in
the api's figure bookkeeping. Neither needs a case, a tree view or an MDI area to
be tested, so the tests supply just those two collaborators.
"""

from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsSlices import QVizPlotAsSlices


class FakeSource:
    def __init__(self, uri):
        self.uri = uri

    def dataKey(self, treeNode):
        return treeNode.getParametrizedDataPath()


class FakeView:
    """Enough of QVizDataTreeView for a plot command: a selection and a source."""

    def __init__(self, uri, nodes):
        self.uri = uri
        self.dataSource = FakeSource(uri)
        self.selectedItem = None
        self.selectedSignalsDict = {node.getParametrizedDataPath():
                                    {'QTreeWidgetItem': node} for node in nodes}
        self.imas_viz_api = None


class FakeApi:
    """The figure bookkeeping a command uses, without the window machinery."""

    def __init__(self, views):
        self.figureframes = {}
        self.figToNodes = {}
        self.DTVlist = list(views)
        for view in views:
            view.imas_viz_api = self

    def AddNodeToFigure(self, figureKey, key, tup):
        self.figToNodes.setdefault(figureKey, {})[key] = tup

    def DeleteFigure(self, figureKey):
        frame = self.figureframes.pop(figureKey, None)
        if frame is not None:
            frame.close()
        self.figToNodes.pop(figureKey, None)

    def GetFiguresKeys(self, figureType='Figure:'):
        return sorted(key for key in self.figureframes if key.startswith(figureType))

    def GetNextKeyForFigure(self, figureType):
        numbers = [int(key[len(figureType):])
                   for key in self.GetFiguresKeys(figureType)]
        return figureType + str(max(numbers) + 1 if numbers else 1)


# The commands the helpers hand out, kept for the session. A command is what
# holds the view, the view holds the api, and the api's `figureframes` is the
# only reference the frames of a multi-figure plot have: a helper that returns
# one frame and drops the command drops the rest, and Qt then deletes widgets a
# paint event is still queued for -- a segfault inside GraphicsView.paintEvent,
# in a test other than the one that made it happen.
_keptAlive = []


def plotCommand(*nodes, all_DTV=True, otherViews=()):
    """A command over one view holding `nodes`, plus any number of other views."""
    view = FakeView('imas:hdf5?case=1', list(nodes))
    FakeApi([view] + list(otherViews))
    command = QVizPlotAsSlices(dataTreeView=view, all_DTV=all_DTV)
    _keptAlive.append(command)
    return command


def plotted(frame, index=0):
    """The numbers of one curve on a frame, as the plot holds them."""
    x, y = frame.curves()[index].getData()
    return list(x), list(y)
