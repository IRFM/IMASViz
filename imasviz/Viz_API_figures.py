# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The registry of the figures of a run.

One record per window -- key, frame, the cases it serves and the node
the window was registered under -- and the keys the menu asks for. The
state lives on the api: ``figureframes`` and ``figToNodes``.
"""

import os

from imasviz.VizUtils import FigureTypes
from imasviz.Viz_API_chrome import titleWithCases, caseTooltip


class QVizFigureRegistryMixin:
    def AddNodeToFigure(self, figureKey, key, tup):
        """Adds an entry to the figToNodes[figureKey] dictionary.

        Every curve that enters a figure goes through this, so it is also the
        one place that figure's title — the key plus the cases it serves, the
        whole URI behind the hover — is rewritten: a curve from a second case
        is another pass, and a restored session replays this very call, which
        is why a window comes back titled the way it was closed and no extra
        step owns that.

        :param figureKey: (str) figure key
        :param key: (str)    dtv.dataSource.dataKey(vizTreeNode)
        :param tup: (tuple) (dtv.dataSource.uri, vizTreeNode)
        """
        if figureKey not in self.figToNodes:
            self.figToNodes[figureKey] = {}
        dic = self.figToNodes[figureKey]
        dic[key] = tup
        self._renameFigure(figureKey)

    def _renameFigure(self, figureKey):
        """Title, and hover text, of the window registered under `figureKey`.

        A key nobody registered is left alone: the registration may come one
        line later, as the Profiles panel does it.
        """
        frame = self.figureframes.get(figureKey)
        if frame is None:
            return
        uris = self.casesServedBy(frame)
        title = titleWithCases(figureKey, uris)
        if frame.windowTitle() != title:
            frame.setWindowTitle(title)
        tip = caseTooltip(uris)
        text = tip or ''
        if frame.toolTip() != text:
            frame.setToolTip(tip)
        # The title bar belongs to the subwindow, which does not inherit the
        # widget's tooltip: the hover must be answered there for the line the
        # user actually hovers.
        sub = self.mdiWindowOf(frame)
        if sub is not None and sub.toolTip() != text:
            sub.setToolTip(tip)

    def GetPlotConfigurationPath(self, configurationName):
        """Get the path to plot configuration file (.pcfg extension).
        """
        return os.environ['HOME'] + "/.imasviz/" + configurationName + ".pcfg"

    def GetFiguresCount(self, figureType):
        """How many figures of one kind are open.

        The kind is spelled by the caller: a default here would be a prefix the
        caller never chose, and a prefix nothing produces any more is a count
        that reads zero for ever.

        :param figureType: (str) a FigureTypes prefix
        :returns: (int)
        """
        return len(self.GetFiguresKeys(figureType))

    def GetTablePlotViewsCount(self):
        """Returns the next table plot number available for plotting.

        :returns: (int) The number of the next table plot
        """
        return self.GetFiguresCount(FigureTypes.TABLEPLOTTYPE)

    def GetStackedPlotViewsCount(self):
        """Returns the next table plot number available for plotting.

        :returns: (int) The number of the next table plot
        """
        return self.GetFiguresCount(FigureTypes.STACKEDPLOTTYPE)

    def GetProfilesPlotViewsCount(self):
        """Returns the next plots table number available.

        :returns: (int) The number of the next plots table
        """
        return self.GetFiguresCount(FigureTypes.PROFILESPLOTTYPE)

    def GetNextKeyForFigure(self, figureType):
        """The key of the next figure of one kind: one past the highest number
        still in use.

        Counting the open figures instead -- what this did when every kind had
        its own accessor -- hands back a number that is already taken as soon as
        one of the lower figures was deleted. Two figures then share a key, and
        the key is how the *Windows* menu and its *Delete* lines address a
        becomes unreachable.

        :param figureType: (str) a FigureTypes prefix
        :returns: (str) the key of the next figure of that kind
        """
        numbers = [self.getFigureKeyNum(key, figureType)
                   for key in self.GetFiguresKeys(figureType)]
        return figureType + str(max(numbers) + 1 if numbers else 1)

    def FigureKeyFor(self, figureType, figureKey=None):
        """The key a figure being opened now is to carry.

        Left free, that is the next key of the kind. Named, it is the key a
        session file recorded -- and the reason a restoring command may name one
        is that a key is not a label but the identity a menu addresses:
        delete and "add this quantity to that figure" all read `figureframes` by
        it, so replaying the gestures of a session without its keys would put the
        same windows under other names (measured: `SlicesPlot1` came back as
        `SlicesPlot2`) and the file would stop describing the screen.

        A named key already held by a live window is refused rather than shared:
        two frames under one key make one of them unreachable, which is the
        failure `GetNextKeyForFigure` above was rewritten to avoid.
        """
        if figureKey is None:
            return self.GetNextKeyForFigure(figureType)
        if figureKey in self.figureframes:
            raise ValueError('A figure named "%s" is already open: the session '
                             'cannot open another window under that key.'
                             % figureKey)
        return figureKey

    def GetNextKeyForTablePlotView(self):
        """Returns the key of the next table plot (e.g. if 'TablePlot i' is the
        latest table plot on the list of existing table plots, value
        'TablePlot i+1' is returned).

        :returns: (str) The key of the next table plot
        """
        return self.GetNextKeyForFigure(FigureTypes.TABLEPLOTTYPE)

    def GetNextKeyForStackedPlotView(self):
        """Returns the key of the next stacked plot (e.g. if 'StackedPlot i'
        is the latest stacked plot on the list of existing stacked plots,
        value 'StackedPlot i+1' is returned).

        :returns: (str) The key of the next stacked plot
        """
        return self.GetNextKeyForFigure(FigureTypes.STACKEDPLOTTYPE)

    def GetNextKeyForProfilesPlotView(self):
        """Returns the key of the next table of profiles plot
        :returns: (str) The key of the next plots table
        """
        return self.GetNextKeyForFigure(FigureTypes.PROFILESPLOTTYPE)

    def GetFiguresKeys(self, figureType):
        """Returns the list of all figure keys of the given type.

        A key is ``<type><number>`` and the number is all digits, so a
        key of one type does not sneak into another's list: ``Plot1``
        is the ``Plot`` group, not ``PlotView:1``'s.

        :returns: (list) A list of figure keys
        """
        figureKeys = []
        for key in self.figureframes.keys():
            if (key.startswith(figureType)
                    and key[len(figureType):].isdigit()):
                figureKeys.append(key)
        return sorted(figureKeys)

    def ForgetFigure(self, figureKey):
        """Take a figure out of the bookkeeping, leaving its window alone.

        The window is already going away: this is what the user closing it does.
        A frame left registered stays in the *Windows* menu as a
        figure that is not there, and keeps a number the next figure of that kind
        is then not entitled to.

        :param figureKey: A figure key (e.g. 'Figure:1')
        """
        self.figureframes.pop(figureKey, None)
        self.figToNodes.pop(figureKey, None)

    def GetFigureKeyOf(self, frame):
        """The key a frame is registered under, or None if it is not registered.

        The kind of a figure is spelled in its key rather than carried on the
        frame, so a caller holding the widget and needing the key has to ask the
        registry.
        """
        for figureKey, registered in self.figureframes.items():
            if registered is frame:
                return figureKey
        return None

    def openWindowOfPluginEntry(self, uri, plugin, entry, occurrence, time=None,
                                ids_name=None):
        """The open window that plugin entry already drew, or None.

        A plugin window is stamped when it is drawn (`VizPlugins/VizPlugin.py`
        `QVizPluginWindow`), which is what a session reads to put it back; the
        same stamp answers "is this thing already on the screen?". It matters
        because the stamp is the only place saying *which* entry drew a window:
        the key says the kind, the registry says the case, and nothing says the
        entry. So the second call of one entry can be drawn into the window that
        stands instead of opening a second one over it.

        `time` narrows to the instant the entry answered, because an entry that
        draws one instant per window answers a different window per instant:
        asked for `None`, the search takes an entry's window at any instant.
        `ids_name` narrows to the branch the entry was asked on, because one
        entry can be offered on several IDS roots and answer one window each:
        the Profiles line earns a panel per IDS, all of them stamped with the
        same plugin, entry and occurrence, so a call asking for the `equilibrium`
        panel would otherwise redraw the `magnetics` one.
        A window whose Qt side is gone is forgotten on the way, like the
        *Windows* menu does (`releaseLeftBehind`), so a close interrupted
        between its windows cannot hold the search off a new window.
        """
        self.releaseLeftBehind()
        for figureKey, frame in self.figureframes.items():
            stamp = getattr(frame, 'pluginWindow', None)
            if stamp is None:
                continue
            if (stamp.uri == uri and stamp.plugin == plugin
                    and stamp.entry == entry
                    and stamp.occurrence == occurrence
                    and (ids_name is None or stamp.ids == ids_name)
                    and (time is None or getattr(stamp, 'time', None) == time)):
                return figureKey
        return None

    def DeleteFigure(self, figureKey):
        """Take a figure out of the run: its window and its key both go.

        The relay the plot commands use when the read refuses what they were
        about to show -- they started the window, and it is theirs to take back.
        The *Windows* menu asks :meth:`closeWindow` of the frame it drew a line
        for; both go through it, so a deleted figure leaves the same thing behind
        whichever gesture asked for it.

        :param figureKey: A figure key (e.g. 'SlicesPlot1')
        :returns: (bool) whether that key held a figure at all
        """
        if figureKey not in self.figureframes:
            return False
        self.closeWindow(self.figureframes[figureKey])
        return True

    def GetFigureKey(self, userKey, figureType):
        """Get the figure key.

        :param userKey: (str) figure number
        :param figureType: a FigureTypes prefix
        :returns: (str) a figure key
        """
        return figureType + userKey

    def getFigureKeyNum(self, figureKey, figureType):
        """Extract figure number from a figure key (e.g. 'SlicesPlot2' -> 2).

        :param figureKey: A figure key (e.g. 'SlicesPlot2')
        :param figureType: the prefix that kind of figure is registered under
        :returns: (str) a figure key
        """
        numFig = int(figureKey[len(figureType):])
        return numFig

    def figureDrawsSameCurveAxis(self, figureKey, treeNode, tensor=False):
        """Whether this quantity can be drawn in that figure -- asked of the figure.

        A curve figure has one abscissa, and the first curve settled it. So the
        question is what that figure draws and whether this quantity can be read
        along it; both are asked rather than derived, the figure answering for
        itself because those are the numbers its label stands over.

        The rule used to be spelled twice, and the two spellings disagreed. The
        menus took a key off the quantity's axes and compared it against the same
        key recomputed for every node the figure had registered. Measured on the
        two quantities of one `profiles_1d` structure -- `.f` and `.psi`, both
        read along time by the read -- the keys were `('LEAF', 'equilibrium',
        'time_slice(itime).profiles_1d.psi')` and `('LEAF', 'equilibrium',
        'dimension 1')`, and the gate answered **False** for both: neither was
        offered in the other's figure, and no gesture could put them side by side.

        `tensor` does not add to the question any more: the sliders are per
        array, one per array of structures, and a slider moves only the curves of
        the array it names. A tensor of another array therefore joins the figure
        with its own band beside the ones already there, and an element asked of
        a such a figure is frozen on the arrays it stands on -- the rule
        `QVizCurvePlot` applies per trace, and the only refusal the figure
        answers is an abscissa the quantity cannot run along. The parameter
        stays in the signature because the callers name the representation; the
        figure does not need it to answer.

        :param figureKey: A figure key (e.g. 'SlicesPlot1')
        :param treeNode: The node a menu is offering to draw there
        :param tensor: Drawn as a tensor (or as one element): kept for the
                       callers that name it, the figure answers either way
        :returns: (bool)
        """
        from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec
        from imasviz.VizDataAccess.QVizCurveAbscissa import choose

        frame = self.figureframes.get(figureKey)
        accepts = getattr(frame, 'accepts', None)
        if accepts is not None:
            return accepts(treeNode, tensor)
        return choose(QVizAxesSpec.fromTreeNode(treeNode),
                      getattr(frame, 'abscissa', None)) is not None

    # def getFigureFrame(self, figureKey):
    #     if figureKey in self.figureframes:
    #         return self.figureframes[figureKey]
    #     else:
    #         print("No frame found with key: " + str(figureKey))

