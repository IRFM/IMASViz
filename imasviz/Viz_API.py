# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import os
import logging
import sys
import weakref
import numpy as np
import shiboken6

from imasviz.VizUtils import (QVizGlobalOperations, FigureTypes,
                              QVizPreferences)

from PySide6.QtWidgets import QMdiSubWindow


def getNodePath(node):
    # print("getNodePath=", node.getPath())
    return node.getParametrizedDataPath()


def titleWithCases(title, uris):
    """The window title of a registered window, with the case or cases it serves.

    `title` — the key today, or the plugin's own heading — is kept verbatim,
    and one short label follows for every case, separated by `; `. A figure
    drawn from two cases carries both; a window no case serves -- a frame
    registered without any node -- carries its heading alone, so the answer
    reads exactly `title` again instead of a trailing `— ` nobody could
    explain. The plugin windows name their one case: the Profiles panel and
    the Equilibrium chart both serve the case of the shot view they were
    opened from.

    The short label, not the URI, is what fits the one line the title bar is:
    the whole URI is where the user hovers for it, and it is `caseTooltip`.

    A case a node registered without one -- ``None``, the empty string -- is
    no case at all and drops out before the heading is read, so a list of
    nothing-that-is-named answers ``title`` again instead of raising inside
    the label read.

    :param title: (str) what the window was registered under
    :param uris  : (iterable of str) the case URIs the window serves --
                   ``casesServedBy`` for a figure, ``[uri]`` for a plugin
                   window of one case
    :returns: (str) the title to paint
    """
    uris = [uri for uri in (uris or ()) if uri]
    if not uris:
        return title
    # Imported here the way CreateDataTree imports the shot view frame: the
    # module that owns `caseLabel` is the data source, whose import chain this
    # one feeds, and the two must not look at each other at import time.
    from imasviz.VizDataSource.QVizIMASDataSource import caseLabel
    labels = []
    for uri in uris:
        label = caseLabel(uri)
        if label not in labels:
            labels.append(label)
    return title + ' — ' + '; '.join(labels)


def caseTooltip(uris):
    """What the hover over a window's title bar says: the whole URI, one per line.

    The title line carries the short labels — they are the ones guaranteed to
    fit — and the tooltip carries what a short label leaves out. A window of
    two cases names both, in the order `casesServedBy` answers them.

    :param uris: (iterable of str)
    :returns: (str) the tooltip text, or None for a window no case serves
    """
    uris = [uri for uri in (uris or ()) if uri]
    return '\n'.join(uris) if uris else None


class QVizMdiSubWindow(QMdiSubWindow):
    """The MDI window a frame is embedded in -- a figure or a case view.

    The window is what the user closes when no command is involved, so it is
    what applies the close rule to the frame it holds. PySide6 6.6 does not
    expose ``QMdiSubWindow.aboutToClose``, hence the close event.

    A case view used to be embedded in a bare ``QMdiSubWindow``, which receives
    no close event of its own: the close box hid the window and said nothing to
    anyone. It is embedded here now so that the one rule reaches all three
    families of window -- figures, case views, and the top-level windows a
    plugin draws (:class:`QVizClosableWindow`).
    """

    def __init__(self, imas_viz_api):
        super(QVizMdiSubWindow, self).__init__()
        # Held weakly, because the api reaches the frame this window is the
        # parent of: a strong reference here closes a cycle through a Qt widget,
        # and a widget freed by the cyclic collector is freed while Qt still
        # owes it a paint event. The api lives as long as the session does --
        # the menu controller that opened the case holds it.
        self.imas_viz_api = weakref.ref(imas_viz_api)

    def closeEvent(self, event):
        super(QVizMdiSubWindow, self).closeEvent(event)
        api = self.imas_viz_api()
        if api is None:
            return
        if api.closeFromTitleBar(self.widget()):
            # The frame is out of the bookkeeping: take the window with it, so
            # the MDI area does not keep a hidden window nobody can reach. The
            # hide comes first -- a hide reaches the children recursively, which
            # is how the frames nested in this one leave the paint queue before
            # Qt deletes them.
            self.hide()
            self.deleteLater()


class QVizClosableWindow:
    """The close rule for a window that is its own top level.

    A plugin panel is registered like a figure and closed like a window, but it
    is not inside the MDI area, so no :class:`QVizMdiSubWindow` sees its close
    box. A plugin that draws such a window mixes this in and answers
    ``windowApi()`` with the api it registers its window in.
    """

    def windowApi(self):
        """The api the window is registered in, or None.

        Left to the window: the framework cannot know where a plugin keeps its
        collaborator, and a window that answers nothing is a window the close
        box cannot take out of the bookkeeping.
        """
        return None

    def closeEvent(self, event):
        super().closeEvent(event)
        api = self.windowApi()
        if api is None:
            return
        api.closeFromTitleBar(self)


class QVizWindowRecord:
    """One window the user can see, as the *Windows* menu asks for it.

    The frame and the api are both held weakly. The menu hands a record to a
    QAction, and on a shot view that QAction lives in a menu bar the frame owns:
    a strong reference either way is a cycle through a Qt widget, and that is
    the shape that frees a widget on the cyclic collector while Qt still owes it
    a paint event. A record whose frame is gone answers ``None`` and the line
    does nothing -- the menu is rebuilt on every opening anyway.
    """

    def __init__(self, kindLabel, iconLabel, label, frame, figureKey, api,
                 cases=()):
        """
        Arguments:
            kindLabel (str) : the group the line is drawn in -- a case view, or
                              one of the names in ``FigureTypes.MENU_ORDER``
            iconLabel (str) : the ``GlobalIcons`` name, or None
            label     (str) : what the user reads on the line
            frame     (QWidget) : the window's content
            figureKey (str) : the key the window answers to, or None for a case
                              view -- which is addressed by its frame
            api       (Viz_API) : the bookkeeping the window lives in
            cases     (tuple) : the case URIs the window serves -- its own for
                              a case view, every origin a figure drew a curve
                              from for a figure. A window a plugin drew
                              serves the case of the shot view it was opened
                              from -- what both registered plugins carry, the
                              node of one being ``None`` because neither draws
                              a curve of its own -- and a window no case
                              serves (a frame registered without any node)
                              answers ``()``. What the *Windows* menu groups
                              by and what "isolating a case" and "closing a
                              case" act on.
        """
        self.kindLabel = kindLabel
        self.iconLabel = iconLabel
        self.label = label
        self.figureKey = figureKey
        self.cases = tuple(cases)
        self._frame = weakref.ref(frame)
        self._api = weakref.ref(api)

    def frame(self):
        """The window's content, or None once Qt has taken it away.

        A frame released with ``deleteLater`` keeps its Python wrapper as long as
        anything else holds a reference to it, and asking that wrapper anything
        then answers ``RuntimeError: Internal C++ object ... already deleted``. A
        menu line opened before another gesture closed its window is exactly that
        -- so the record answers nothing and the stale line costs nothing, which
        is what :meth:`Viz_API.DeleteFigure` does for a key nobody holds.
        """
        frame = self._frame()
        if frame is None or not shiboken6.isValid(frame):
            return None
        return frame

    def api(self):
        return self._api()

    def visible(self):
        """Whether this window is on the screen right now.

        The same question ``mdiWindowOf`` answers, because that is what hides
        and shows: a window the user took off the screen with its own close box,
        a window the *Windows* menu hid, and a window nobody embedded are three
        spellings of one state, and the line is unchecked for all three.
        """
        api, frame = self.api(), self.frame()
        if api is None or frame is None:
            return False
        window = api.mdiWindowOf(frame)
        return (window if window is not None else frame).isVisible()


class Viz_API:

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

    def GetDTVFrames(self):
        """Returns the list of shot views frames currently opened.
        There is only one frame for a given shot.
        """
        return self.DTVframeList

    def GetDataSources(self):
        """Returns the list of data sources currently opened.
        The data source is associated to one shot.

        :returns: A list of data sources (QVizIMASDataSource objects)
        """
        dataSourcesList = []
        for dtv in self.DTVlist:
            dataSourcesList.append(dtv.dataSource)
        return dataSourcesList

    def isDataSourceAlreadyOpened(self, dataSource):
        """Returns True if this data source has been already created.

        :param dataSource: a QVizIMASDataSource object
        :returns: True or False
        """
        dataSourcesList = self.GetDataSources()
        for ds in dataSourcesList:
            if dataSource.getKey() == ds.getKey():
                return True
        return False

    def GetDTVFor(self, dataSourceKey):
        """Returns the shot view frame for the given data source key.

        :param dataSourceKey: (str) The key of a data source (returned by
                                    QVizIMASDataSource.dataKey())
        :returns: a QVizDataTreeViewFrame object
        """
        for dtv in self.DTVlist:
            if dataSourceKey == dtv.dataSource.getKey():
                return dtv
        return None

    def RemoveDTVFrame(self, frame):
        """Removes the shot view frame from the list of opened frames

        and out of the bookkeeping of every window the view takes down with
        it: a plugin window parented on the view dies with it, so its key has
        to leave the registry at the same time, or the *Windows* menu keeps a
        line no gesture can act on, and the number of the next window of that
        kind skips it for ever.

        :param frame: a QVizDataTreeViewFrame object
        """
        self.DTVframeList.remove(frame)
        self.DTVlist.remove(frame.dataTreeView)
        for figureKey in self.windowsTakenDownWith(frame):
            self.ForgetFigure(figureKey)
        # The frame was the last one displaying this case: let go of the IDSs
        # that were loaded for it, as the per-source cache used to go away with
        # the source it owned.
        frame.dataTreeView.dataSource.forget_case()

    def windowsTakenDownWith(self, frame):
        """The registered windows inside this view's widget tree.

        A window a plugin draws on the shot view is a child of it (the Equi-
        librium chart parents on the tree), so closing the view takes its C++
        object down with the rest of the view -- the only windows with that
        fate, since a figure sits in the MDI area and a panel like the Profiles
        one stands on its own. Their parent chain is the answer, guarded by
        ``shiboken6.isValid`` the way :meth:`QVizWindowRecord.frame` guards
        it, because a wrapper kept alive by the registry outlives its object.
        """
        taken = []
        for figureKey, window in list(self.figureframes.items()):
            node = window
            while node is not None and shiboken6.isValid(node):
                if node is frame:
                    taken.append(figureKey)
                    break
                node = node.parent()
        return taken

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

    def CreateDataTree(self, dataSource):
        """Returns the shot view frame for the specified data source.

        :param dataSource: A QVizIMASDataSource object
        :returns:          A QVizDataTreeViewFrame object
        """
        from imasviz.VizGUI.VizTreeView import QVizDataTreeViewFrame
        frame = QVizDataTreeViewFrame(parent=None,
                                      views={},
                                      dataSource=dataSource,
                                      imas_viz_api=self)

        #frame.dataTreeView.dataSource = dataSource  # update the dataSource
        # attached to the view

        # Add created data tree view (DTV) frame to a list of DTV frames
        self.DTVframeList.append(frame)

        # Add current data tree view (DTV) frame to a list of DTVs
        self.DTVlist.append(frame.dataTreeView)

        return frame

    def ShowDataTree(self, dataTreeView):
        """Displays the specified data tree frame.
        NOTE: a QVizDataTreeView accepts QVizDataTreeViewFrame as a parent
              object.

        :param dataTreeView: (obj) A QVizDataTreeView or a
                                   QVizDataTreeViewFrame object
        """
        from imasviz.VizGUI.VizTreeView import QVizDataTreeView, QVizDataTreeViewFrame
        if isinstance(dataTreeView, QVizDataTreeViewFrame):

            # If MDI is present, add the DTV to it as a subwindow
            if self.getMDI() is not None:
                # The same window class a figure is embedded in: the close box
                # of a case view has to answer the same question it answers for
                # a figure, and a bare QMdiSubWindow receives no close event.
                subWindow = QVizMdiSubWindow(self)
                subWindow.setWidget(dataTreeView)

                self.getMDI().addSubWindow(subWindow)
                # Embedding is not showing: `addSubWindow` leaves the subwindow
                # hidden when the area is already on screen, which is the state
                # of the application whenever a case is opened. Same fix as
                # `addPlotWidgetToMDI` for figures.
                subWindow.show()
                # A window is now in the area: the moment the preferred layout
                # (a preference, one-shot) is applied to it.
                self._maybeApplyPreferredLayout()
            dataTreeView.show()
        elif isinstance(dataTreeView, QVizDataTreeView):
            frame = dataTreeView.parent
            # The frame may be hidden (a *Windows* menu line) or its window
            # the frame is not enough, since hiding the window hides everything
            # in it whether the frame is shown or not.
            window = self.mdiWindowOf(frame)
            if window is not None:
                window.show()
            frame.show()
        else:
            raise ValueError('Wrong argument type arg for ShowDataTree(arg).')

    def ShowNodesSelection(self, DTV):
        """Displays a window showing a list of all selected nodes from the
        dataTreeView object.
        NOTE: a QVizDataTreeView accepts QVizDataTreeViewFrame as a parent
              object.

        :param DTV (obj): A QVizDataTreeView or a QVizDataTreeViewFrame object
        """
        from imasviz.VizGUI.VizTreeView import QVizDataTreeViewFrame
        from imasviz.VizGUI.VizWidgets import QVizNodesSelectionWindow
        dataTreeView = DTV
        if isinstance(DTV, QVizDataTreeViewFrame):
            dataTreeView = DTV.dataTreeView
        self.nsw = QVizNodesSelectionWindow(dataTreeView)
        self.nsw.show()

    def GetSelectedNodes(self, DTV):
        """Returns the list of nodes selected by GUI or script commands.

        :param DTV: A QVizDataTreeViewFrame or QVizDataTreeView object
        :returns: (list) A list of QVizTreeNode objects.
        """
        from imasviz.VizGUI.VizTreeView import QVizDataTreeViewFrame
        dataTreeView = DTV
        if isinstance(DTV, QVizDataTreeViewFrame):
            dataTreeView = DTV.dataTreeView
        selectedNodes = []
        for key in dataTreeView.selectedSignalsDict:
            v = dataTreeView.selectedSignalsDict[key]
            vizTreeNode = v['QTreeWidgetItem']
            selectedNodes.append(vizTreeNode)
        return selectedNodes

    def GetSelectedSignalsDict(self, DTV):
        """Returns the list of signals (nodes) dictionaries selected by GUI or
        script commands.

        :param DTV: A QVizDataTreeViewFrame or QVizDataTreeView object
        :returns: (list) A list of signals (nodes) dictionaries.
        """
        from imasviz.VizGUI.VizTreeView import QVizDataTreeViewFrame
        dataTreeView = DTV
        if isinstance(DTV, QVizDataTreeViewFrame):
            dataTreeView = DTV.dataTreeView
        return dataTreeView.selectedSignalsDict

    def GetSelectedSignalsDictFromAllDTVs(self):
        """Returns the list of signals (nodes) dictionaries selected by GUI or
        script commands from all opened shot views (DTVs).

        :returns: (list) A list of signals (nodes) dictionaries
        """
        allSelectedSignals = {}
        for i in range(len(self.DTVframeList)):
            allSelectedSignals.update(
                self.DTVframeList[i].dataTreeView.selectedSignalsDict)

        return allSelectedSignals

    def ShowHideFigure(self, figureKey):
        """Shows/Hides a figure.

        The spelling the scripting API and the session commands use; the
        *Windows* menu asks :meth:`showHideWindow` of the frame it drew a line
        for. One verb between the two, because a figure, a case view and a
        window a plugin drew differ in where they live, not in what hiding one
        costs.

        :param figureKey: (str) A figure key (e.g. 'SlicesPlot1')
        """
        return self.showHideWindow(self.figureframes[figureKey])

    def showHideWindow(self, frame):
        """Take one window off the screen, or put it back.

        Whether the frame sits in a subwindow or stands alone is asked, never
        assumed -- the same question :meth:`mdiWindowOf` answers, for the same
        reason: hiding the window hides everything in it, so showing a frame
        whose window is hidden changes nothing on screen.

        :param frame: the window's content
        :returns: (bool) whether the window is on the screen afterwards
        """
        window = self.mdiWindowOf(frame)
        target = window if window is not None else frame
        if target.isVisible():
            target.hide()
        else:
            target.show()
            if window is not None:
                frame.show()
        return target.isVisible()

    SHOTVIEW_KIND = ('Shot view', 'Figure')

    def openWindows(self):
        """Every window the user can see, in the order the menus draw them.

        The one answer to "what is open". The two menu builders this replaces
        each walked half of the bookkeeping and neither could name the other's
        windows: a case view is in ``DTVframeList``, a figure is in
        ``figureframes`` under one of the prefixes of ``FigureTypes.MENU_ORDER``.
        A kind holding nothing is left out -- a group nobody can click is a group
        that should not be drawn -- and a window no key holds is not on the
        list, which is exactly what the close box used to leave behind.

        Dead registrations leave first: a record whose frame is gone is a line
        the menu would draw for ever and no gesture could act on, so asking
        "what is open" releases them and says where they went -- :meth:`
        releaseLeftBehind` -- and then lists the windows with something behind
        them. Whatever reads the windows of a run -- the menu, a gesture, the
        session save -- therefore goes through this one answer.

        :returns: (list) :class:`QVizWindowRecord` for each window, case views
                          first, then the figures in ``MENU_ORDER`` order
        """
        self.releaseLeftBehind()
        windows = []
        kindLabel, iconLabel = self.SHOTVIEW_KIND
        for frame in list(self.DTVframeList):
            label = frame.dataTreeView.dataSource.getLongLabel()
            uri = getattr(frame.dataTreeView.dataSource, 'uri', None)
            windows.append(QVizWindowRecord(kindLabel, iconLabel, label,
                                            frame, None, self,
                                            cases=(uri,) if uri else ()))
        for kindLabel, iconLabel, figureType in FigureTypes.MENU_ORDER:
            for figureKey in self.GetFiguresKeys(figureType):
                frame = self.figureframes[figureKey]
                cases = self.casesServedBy(frame)
                windows.append(QVizWindowRecord(kindLabel, iconLabel,
                                                # The same line the title bar
                                                # paints (`_renameFigure`): the
                                                # key the window is addressed
                                                # by, plus the cases it serves,
                                                # so a line outlives its window
                                                # and still says whose it was.
                                                titleWithCases(figureKey,
                                                               cases),
                                                frame,
                                                figureKey, self,
                                                cases=cases))
        return windows

    def casesServedBy(self, frame):
        """The case URIs a figure serves, read off `figToNodes`.

        A figure drawn from one case serves that one; a comparison figure serves
        every case that put a curve in it -- so "isolating" or "closing" one
        case shows the comparison while the other case it serves is still
        open. The windows a plugin drew serve the case of the shot view their
        entry ran on -- the Profiles panel and the Equilibrium chart both
        register it here, with a ``None`` node, because neither draws a curve
        of its own, and the *Windows* menu and the case gestures read this
        instead of a second record. A frame registered without any node serves
        none.
        """
        figureKey = self.GetFigureKeyOf(frame)
        if figureKey is None:
            return ()
        uris = []
        for uri, _node in self.figToNodes.get(figureKey, {}).values():
            if uri and uri not in uris:
                uris.append(uri)
        return tuple(uris)

    def setWindowVisible(self, frame, visible):
        """Put a window on or off the screen, whichever state it is in now.

        :meth:`showHideWindow` bounces, which is the answer to "toggle this
        one"; a group gesture needs a state, "these all hidden, these all
        shown", and the two share the one hiding rule: the window is what
        hides and shows (hiding it hides the frame inside), and showing a
        hidden frame whose window is left hidden changes nothing on screen.

        The show path must re-show the *frame* as well as the shell: the shell
        is the window the user sees, but the frame is its content, and a shell
        left up over a frame that is still hidden is a title bar over a blank
        body -- a window the user counts as still on screen, and one the two
        group gestures that go through here (*isolate* and *hide others*) used
        to strand across a whole run. :meth:`showHideWindow` already does this;
        here it is done whatever the shell is already doing, because the frame
        and the shell can disagree.
        """
        window = self.mdiWindowOf(frame)
        if visible:
            if window is not None:
                window.show()
                frame.show()
            else:
                frame.show()
        elif window is not None:
            window.hide()
        else:
            frame.hide()
        return (window if window is not None else frame).isVisible()

    def releaseLeftBehind(self):
        """Release the registrations whose window Qt has already taken away.

        A window killed under a live registration -- a close interrupted
        between its windows, a frame released anywhere while ``figureframes``
        or ``DTVframeList`` kept its entry -- would otherwise be a line the
        *Windows* menu draws for ever, that no gesture can act on: every one
        asks :meth:`QVizWindowRecord.frame`, which answers ``None`` for an
        object that is gone, and the number of the next window of the kind
        skips the dead key for the whole session. This is the single place
        the release happens, so the menu, the gestures and the session save
        all read the same truth: the dead entry is out of the bookkeeping,
        and the line that goes with it names the window, its key and its case.

        :returns: (int) how many registrations were released
        """
        released = 0
        for frame in list(self.DTVframeList):
            if not shiboken6.isValid(frame):
                label = frame.dataTreeView.dataSource.getLongLabel()
                uri = getattr(frame.dataTreeView.dataSource, 'uri', None)
                try:
                    self.DTVframeList.remove(frame)
                except ValueError:
                    pass
                for view in list(self.DTVlist):
                    if view is frame.dataTreeView:
                        self.DTVlist.remove(view)
                        break
                logging.getLogger('logPanel').warning(
                    'The shot view "%s" (case "%s") is no longer on the Qt '
                    'side: its entry is released from the bookkeeping.'
                    % (label, uri))
                released += 1
        for figureKey in list(self.figureframes.keys()):
            if not shiboken6.isValid(self.figureframes[figureKey]):
                cases = self.casesServedBy(self.figureframes[figureKey])
                self.ForgetFigure(figureKey)
                where = ' of case "%s"' % cases[0] if cases else ''
                logging.getLogger('logPanel').warning(
                    'The window "%s"%s is no longer on the Qt side: its '
                    'entry is released from the bookkeeping -- the line of the '
                    '*Windows* menu that held it is gone, and the number of '
                    'the next window of its kind is back.'
                    % (figureKey, where))
                released += 1
        return released

    def windowsFor(self):
        """Every window with its live frame, the records the gestures act on.

        The dead registrations are released before the list is built, because
        a gesture that skips a dead record silently would leave it on the
        screen's bookkeeping for ever -- the stuck entry of the *Windows*
        menu -- while the one that acts on it dies in the middle of its own
        list. :meth:`releaseLeftBehind` is that release and the named line.
        """
        self.releaseLeftBehind()
        for record in self.openWindows():
            frame = record.frame()
            if frame is not None:
                yield record, frame

    def isolateCase(self, uri):
        """Show one case's windows and hide the rest, shared ones shown.

        A case's window set is its own case view, every figure
        :meth:`casesServedBy` answers its URI, and the windows a plugin drew
        on it -- the Profiles panel, the Equilibrium chart -- which serve that
        one case and no other. A figure that serves this case *and* another
        is shown, not hidden: isolating a case is about getting the other
        cases off the screen, not about the figures this case still reads. A
        window that serves no case at all is left exactly where it is, since
        "this case" has nothing to say about it.
        """
        windows = list(self.windowsFor())
        for record, frame in windows:
            if not record.cases:
                continue
            action = 'shown' if uri in record.cases else 'hidden'
            try:
                self.setWindowVisible(frame, uri in record.cases)
            except Exception as error:
                self._gestureFailed(record, action, str(error))

    def hideOthers(self, exceptFrame):
        """Every window off the screen except the one named.

        The gesture for finding one figure in a tiled or cascaded pile: leave
        the one the menu line was drawn for, take the rest off the screen. A
        window already off the screen is left off it.
        """
        for record, frame in list(self.windowsFor()):
            if frame is exceptFrame:
                continue
            try:
                self.setWindowVisible(frame, False)
            except Exception as error:
                self._gestureFailed(record, 'hidden', str(error))

    def closeOthers(self, exceptFrame):
        """Every window closed for good except the one named.

        The same question as :meth:`hideOthers`, and the answer :meth:`closeWindow`
        gives instead of showing nothing: out of the bookkeeping, out of the
        session, out of the *Windows* menu. Kept to a different verb because
        what a close costs -- a figure it was redrawing is read a second time
        to come back -- is not what a hide costs.
        """
        for record, frame in list(self.windowsFor()):
            if frame is exceptFrame:
                continue
            try:
                self.closeWindow(frame)
            except Exception as error:
                self._gestureFailed(record, 'closed', str(error))

    def closeCase(self, uri):
        """Close the windows of one case for good; shared ones hidden, not closed.

        A case view and a figure that serves this case alone leave the book-
        keeping. A figure that serves this case *and* another is hidden, not
        closed: its other case still reads a live curve out of it, and closing
        it would take that curve out of a window somebody is still looking at.
        Hiding keeps the key, so the other case's *Windows* line still reaches it.
        One window that refuses in the middle of the list is named and left
        for the next pass, and the rest of the case's windows are still taken
        care of -- a gesture that raised here used to abandon the rest of the
        list with the failure, which is how the same entry kept meeting the
        same dead state on every repeated *Close this case*.
        """
        windows = list(self.windowsFor())
        for record, frame in windows:
            cases = record.cases
            if not cases or uri not in cases:
                continue
            if set(cases) == {uri}:
                try:
                    self.closeWindow(frame)
                except Exception as error:
                    self._gestureFailed(record, 'closed', str(error))
                    continue
            try:
                self.setWindowVisible(frame, False)
            except Exception as error:
                self._gestureFailed(record, 'hidden', str(error))

    def _gestureFailed(self, record, action, reason):
        """One window of a group gesture refused: name it, and go on.

        The *Windows* lines the gestures answer go over every window of the
        run, so one refusal must not cost the rest of the list -- the report
        behind :meth:`releaseLeftBehind` is a gesture dying on window two and
        leaving the windows three and on unprocessed, the same entry meeting
        the same dead state on every repeated click. The line says which
        window of which case it was, and what it refused.
        """
        where = ' of case "%s"' % record.cases[0] if record.cases else ''
        logging.getLogger('logPanel').warning(
            'The window "%s"%s could not be %s: %s. The other windows of '
            'the gesture were still taken care of.'
            % (record.label, where, action, reason))

    def mdiLayout(self, mode):
        """Lay the MDI area's windows out in `mode` and remember the choice.

        One of `QVizPreferences.LAYOUT_MODES`. *tabbed* puts every window in a
        single strip -- the big declutter when several cases are open -- and
        *tiled* / *cascaded* are the classic tidy-ups; *windowed* is the
        default pile the first case is opened into. The choice is written to
        the preference so the next start-up lays the area the way the user last
        left it.
        """
        from PySide6.QtWidgets import QMdiArea

        mdi = self.getMDI()
        if mdi is None:
            raise ValueError('No MDI area to lay out: no window is open.')
        if mode not in QVizPreferences.LAYOUT_MODES:
            raise ValueError('%r is not a view the MDI area wears: write %s'
                             % (mode, ' or '.join(
                                 repr(one) for one in
                                 QVizPreferences.LAYOUT_MODES)))
        if mode == 'tabbed':
            mdi.setViewMode(QMdiArea.TabbedView)
        else:
            mdi.setViewMode(QMdiArea.SubWindowView)
            if mode == 'tiled':
                mdi.tileSubWindows()
            elif mode == 'cascaded':
                mdi.cascadeSubWindows()
        QVizPreferences.Mdi_view_mode = mode
        return mode

    def _maybeApplyPreferredLayout(self):
        """Lay the area the way the preference says, once a window is in it.

        The area opens in windowed mode and the preference may not. This is
        called from both embed points, after a sub-window is added: the one-shot
        flag means the apply happens only when the area goes from empty to not,
        and a refusal (no MDI to lay out) resets the flag so a later embed --
        the one that actually has a window to lay out -- can still answer it.
        Windowed is the mode the area already answers, so it costs nothing.
        """
        if self._layoutApplied:
            return
        self._layoutApplied = True
        if QVizPreferences.Mdi_view_mode == 'windowed':
            return
        mdi = self.getMDI()
        if mdi is None:
            self._layoutApplied = False
            return
        try:
            self.mdiLayout(QVizPreferences.Mdi_view_mode)
        except ValueError:
            self._layoutApplied = False

    def forgetWindow(self, frame):
        """Take a frame out of the bookkeeping: its key, or its case.

        :param frame: the window's content
        :returns: (bool) whether the frame was in the bookkeeping at all
        """
        figureKey = self.GetFigureKeyOf(frame)
        if figureKey is not None:
            self.ForgetFigure(figureKey)
            return True
        if frame in self.DTVframeList:
            # The frame was the last one showing this case: the IDSs loaded for
            # it go with it, which is what makes closing a case view cost more
            # than hiding one -- and what the manual says out loud.
            self.RemoveDTVFrame(frame)
            return True
        return False

    def closeFromTitleBar(self, frame):
        """What the close box of a window costs the frame it was clicked on.

        With ``Close_button_deletes`` off -- the default -- nothing: the window
        is taken off the screen and stays where it is, so the *Windows* menu
        keeps naming it (unchecked) and clicking the line puts it back, and a
        saved session writes it hidden. Measured before the rule existed, a
        curve figure closed with its own box left ``figureframes`` empty, its
        window hidden inside the MDI area, its frame alive with no key reaching
        it, and the next curve figure of that kind took ``SlicesPlot1`` again:
        two windows under one name, one of them unreachable by any gesture.

        With it on, the frame leaves the bookkeeping and the caller releases the
        window it owns -- :class:`QVizMdiSubWindow` does, hiding it first, so
        the nested frames leave the paint queue before Qt deletes them.

        :returns: (bool) whether the window is to be released
        """
        if not QVizPreferences.Close_button_deletes:
            return False
        return self.forgetWindow(frame)

    def closeWindow(self, frame):
        """Take one window off the screen and out of the bookkeeping for good.

        The *Delete* entry of the *Windows* menu. It is the same shape as what
        the close box does when the preference says to close, so the two cannot
        disagree about what a closed window leaves behind.
        """
        window = self.mdiWindowOf(frame)
        if window is not None:
            window.hide()
            window.deleteLater()
        else:
            frame.hide()
            frame.deleteLater()
        return self.forgetWindow(frame)

    def mdiWindowOf(self, frame):
        """The MDI window a frame is embedded in, or None if it stands alone.

        A frame lives either inside a :class:`QMdiSubWindow` handed out by
        `addPlotWidgetToMDI`, or on its own. The *Windows* menu and its
        which, and the old test was the *name* of the top-level window
        ("IMASViz root window"), which only holds while the frame sits under the
        application's main window. Measured on a plain MDI area, that test fails
        and both entries then act on the frame instead of the window: a line
        hides the frame and leaves an empty window on screen, and Delete closes
        the frame and leaves the window visible. Asking what the parent *is*
        says the same thing about the application's windows and the right thing
        about every other one.
        """
        parent = frame.parent()
        return parent if isinstance(parent, QMdiSubWindow) else None

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
        """Returns the list of all figure keys.

        :returns: (list) A list of figure keys
        """
        figureKeys = []
        for key in self.figureframes.keys():
            if key.startswith(figureType):
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

    def PlotSelectedSignals(self, dataTreeFrame, figureKey=None, update=0,
                            all_DTV=False, plotAxis="TIME"):
        """Plots the current selected set of signals on a figure.

        :param plotAxis: kept for call compatibility, and no longer selects
                         anything: the frame takes its abscissa from the axes the
                         read walks along each quantity, and carries a named
                         control for every axis it leaves out.
        :param dataTreeFrame: A QVizDataTreeViewFrame object
        :param figureKey: A figure key. If None, a new figure is created.
        :param update: kept for call compatibility: adding to the figure named by
                       figureKey is what the command does, and the figure to
                       create is what a None figureKey means.
        :param all_DTV: if True, all current selected set of signals on all
                        shot views are plotted
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotAsSlices
        QVizPlotAsSlices(dataTreeView=dataTreeFrame.dataTreeView,
                         all_DTV=all_DTV,
                         intoFigureKey=figureKey).execute()

    def PlotSelectedSignalsInTablePlotViewFrame(self, dataTreeFrame,
                                                all_DTV=False,
                                                plotAxis='TIME'):
        """Plots the current selected set of signals of this shot view on a
           new table plot.

        :param plotAxis: 'TIME' reads every quantity along time; anything else
                         lets the read answer per quantity, which is what a
                         selection mixing coordinates needs -- each quantity then
                         gets a panel of its own with its own labels.
        :param dataTreeFrame: A QVizDataTreeViewFrame object
        :param all_DTV:       When True, all current selected set of signals
                              on all shot views are plotted
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotAsTable
        frame = QVizPlotAsTable(dataTreeView=dataTreeFrame.dataTreeView,
                                all_DTV=all_DTV,
                                plotAxis=plotAxis).execute()
        if frame is not None:
            self.addPlotWidgetToMDI(frame)

    # Plot the set of signals selected by the user
    def ApplyTablePlotViewConfiguration(self, dataTreeFrame, configFilePath,
                                        all_DTV=False, plotAxis='TIME'):
        """Selects a set of signals using the selection file and plots of this
        shot view on a new table plot.

        The file names the quantities by IDS path and occurrence; what it holds
        besides the paths (pen, symbols, axis ranges) is not applied, and the log
        says so.

        :param plotAxis: see PlotSelectedSignalsInTablePlotViewFrame.
        :param dataTreeFrame:  A QVizDataTreeViewFrame object
        :param configFilePath: The path to a data selection file
        :param all_DTV: kept for call compatibility: a configuration file names
                        its quantities in this shot view, so there is no other
                        view to take a selection from.
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotAsTable
        frame = QVizPlotAsTable(dataTreeView=dataTreeFrame.dataTreeView,
                                plotAxis=plotAxis,
                                configFile=configFilePath).execute()
        if frame is not None:
            self.addPlotWidgetToMDI(frame)

    def LoadMultipleIDSData(self, dataTreeFrame, IDSNamesList, occurrence=0,
                            threadingEvent=None):
        """Load multiple IDSs data for a given data tree frame and a given
        occurrence.

        :param dataTreeFrame: A QVizDataTreeViewFrame object
        :param IDSNamesList: List of the names of the IDSs
        :param occurrence: (int) Occurrence to be loaded (will be the same
                                 for all IDSs)
        :param threadingEvent: When True, data are loaded from a new Thread
        """
        for IDSName in IDSNamesList:
            self.LoadIDSData(dataTreeFrame, IDSName, occurrence,
                             threadingEvent)

    def LoadIDSData(self, dataTreeFrame, IDSName, occurrence=0,
                    threadingEvent=None):
        """Load IDS data for a given data tree frame and a given occurrence.

        :param dataTreeFrame: A QVizDataTreeViewFrame object
        :param IDSName: The name of the IDS
        :param occurrence: (int) Occurrence of the IDS
        :param threadingEvent: If True, data are loaded from a new Thread
        """
        from imasviz.VizGUI.VizTreeView import QVizDataTreeViewFrame
        from imasviz.VizGUI.VizGUICommands import QVizLoadOccurrence
        dataTreeView = dataTreeFrame.dataTreeView \
            if isinstance(dataTreeFrame, QVizDataTreeViewFrame) else dataTreeFrame
        QVizLoadOccurrence(dataTreeView=dataTreeView, idsName=IDSName,
                           occurrence=occurrence, asynch=threadingEvent).execute()

    def SelectSignals(self, DTV, paths):
        """Select the nodes these paths name in the given shot view.

        The manual spells the argument as a plain list of node paths; a script
        written against the older dictionary of two parallel lists is still
        taken. Either way the selection is left by the same command that applies
        a saved node-configuration, so a scripted selection is shaped exactly
        like one made by hand in the tree -- and, as before, an IDS whose data
        are not in the tree yet is fetched first.

        :param DTV: a QVizDataTreeViewFrame object
        :param paths: a list of node paths (e.g.
                      ['magnetics/flux_loop(0)/flux/data']), a single path, or
                      the older map with 'paths' and 'occurrences'. Occurrences
                      are optional; one occurrence applies to every path.
        :returns: how many of the named nodes were found and selected
        """
        from imasviz.VizGUI.VizConfigurations.QVizConfigurationFile import \
            QVizConfigurationFile, QVizQuantity, SELECTION
        from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectFromConfiguration import QVizSelectFromConfiguration

        pathsList = paths.get('paths') if isinstance(paths, dict) else paths
        occurrences = paths.get('occurrences') if isinstance(paths, dict) else None
        if isinstance(pathsList, str):
            pathsList = [pathsList]
        pathsList = list(pathsList or [])
        occurrences = list(occurrences or [])
        if occurrences and len(occurrences) not in (1, len(pathsList)):
            raise ValueError('The number of specified occurrences differs from '
                             'the number of specified paths.')
        if len(occurrences) == 1:
            occurrences = occurrences * len(pathsList)

        quantities = [QVizQuantity(path=path,
                                  occurrence=int(occurrences[index])
                                  if occurrences else 0,
                                  row=None, column=None, uri=None)
                      for index, path in enumerate(pathsList)]
        configuration = QVizConfigurationFile(kind=SELECTION,
                                              quantities=quantities,
                                              spellPathsAsDocumented=True)
        return QVizSelectFromConfiguration(DTV.dataTreeView,
                                          configuration).execute()

    def PlotSelectedSignalsFrom(self, dataTreeFramesList, figureKey=None,
                                all_DTV=False):
        """Plots current selected signal.

        One command per shot view in the list, each drawing that view's
        selection. With no figureKey each gets figures of its own, as before; with
        one, the selection is added to the curve figure it names.

        :param dataTreeFramesList:  A list of DTV frames
        :param figureKey: A figure key. If None, a new figure is created.
        :param all_DTV: When True, all current selected set of signals on all
                        shot views are plotted
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotAsSlices
        for f in dataTreeFramesList:
            QVizPlotAsSlices(dataTreeView=f.dataTreeView,
                             all_DTV=all_DTV,
                             intoFigureKey=figureKey).execute()

    def UnSelectAllSignals(self, dataTreeFrame, all_DTV=False):
        """Unselects all previously selected signals for the given shot view.

        :param dataTreeFrame: A QVizDataTreeViewFrame object
        :param all_DTV: When True, all selected signals from all shot views are
                        unselected
        """
        from imasviz.VizGUI.VizGUICommands import QVizSelectNodes
        QVizSelectNodes(dataTreeFrame.dataTreeView,
                        all_DTV=all_DTV).unselectAll()

    def SelectSignalsGroup(self, dataTreeFrame, occurrence, onePathInTheGroup):
        """Selects nodes for this shot view.

        :param dataTreeFrame: A QVizDataTreeViewFrame object
        :param occurrence: the occurrence of an IDS
        :param onePathInTheGroup: An IDS path to one of the node
                                      (signals), containing a data array
                                      (e.g. FLT_1D), of which all siblings
                                      in the AOS are to be selected.
                                      Example:
                                      'magnetics/flux_loop(0)/flux/data'
        """
        # The two arguments are honoured: the body used to ignore both and take
        # whatever node the tree happened to have as its current item, so the
        # group selected had nothing to do with the path and occurrence asked for.
        from imasviz.VizGUI.VizGUICommands import QVizSelectNodes
        view = dataTreeFrame.dataTreeView
        path = QVizGlobalOperations.makeIMASPath(onePathInTheGroup)
        node = next((node for node in view.signalsList
                     if node.getPath() == path and
                     node.getOccurrence() == int(occurrence)),
                    view.selectedItem)
        QVizSelectNodes(view, node).sameAos()

    def IDSDataAlreadyFetched(self, dataTreeView, IDSName, occurrence):
        key = IDSName + "/" + str(occurrence)
        if key in dataTreeView.ids_roots_occurrence:
            return True
        else:
            return False

    def GetNextOccurrenceUnloadedWithAvailableData(self, dataTreeView, node):
        """The lowest occurrence of this IDS that holds data and is not shown.

        None when there is none: the case holds no other occurrence, or every
        one it holds is already displayed.
        """
        return self.occurrences(dataTreeView).nextUnloaded(
            node.getIDSName(), dataTreeView.loadedOccurrences(node.getIDSName()))

    def GetAllOccurrencesWithAvailableData(self, node):
        """The occurrences of this IDS the opened case holds data for."""
        return self.occurrences(node.getDataTreeView()).occurrencesOf(
            node.getIDSName())

    def GetAllOccurrencesUnloadedWithAvailableData(self, dataTreeView, node):
        """The occurrences the case holds and this view has not built yet."""
        return self.occurrences(dataTreeView).unloaded(
            node.getIDSName(), dataTreeView.loadedOccurrences(node.getIDSName()))

    def occurrences(self, dataTreeView):
        """The occurrence inventory of the case this view is opened on.

        Three helpers used to answer this from the data dictionary with
        eval("imas." + idsName + "().getMaxOccurrences()"), which this IMAS
        stack does not provide; the case itself answers, in 0.10 s for all 55
        IDS names of the reference data dictionary.
        """
        return dataTreeView.occurrences

    def GetDataSource(self, dataTreeFrame):
        from imasviz.VizGUI.VizTreeView import QVizDataTreeViewFrame
        if isinstance(dataTreeFrame, QVizDataTreeViewFrame):
            return dataTreeFrame.parent.dataSource
        else:
            return dataTreeFrame.dataSource

    def GetIDSInstance(self, dataTreeFrame, occurrence):
        from imasviz.VizGUI.VizTreeView import QVizDataTreeViewFrame
        if isinstance(dataTreeFrame, QVizDataTreeViewFrame):
            return self.GetDataSource(dataTreeFrame.parent).data_entries[occurrence]
        else:
            return self.GetDataSource(dataTreeFrame).data_entries[occurrence]

    def GetSignal(self, dataTreeView, vizTreeNode, as_function_of_time=None,
                  coordinate1_index=0, time_index=None, plotWidget=None):
        from imasviz.VizDataAccess.QVizDataAccessFactory import QVizDataAccessFactory
        try:
            signalDataAccess = QVizDataAccessFactory(dataTreeView.dataSource).create()
            return signalDataAccess.GetSignal(treeNode=vizTreeNode,
                                              plotWidget=plotWidget,
                                              as_function_of_time=as_function_of_time,
                                              coordinate_index=coordinate1_index,
                                              time_index=time_index)
        except:
            raise

    def getMDI(self):
        if self.parent is not None:
            return self.parent
        return None

    def ForgetFigureOf(self, plotWidget):
        """Take a frame out of the bookkeeping under whichever key holds it.

        Kept for the scripts that close a window without going through a
        command. The close box does not call this: it calls
        :meth:`closeFromTitleBar`, which is the one that decides whether the
        window is only taken off the screen or really gone -- and a frame that
        is only hidden keeps its key, so it stays in the *Windows* menu and in
        the session, under the same name.
        """
        return self.forgetWindow(plotWidget)

    def addPlotWidgetToMDI(self, plotWidget):
        """Embeds the plotWidget inside MDI subwindow, and puts it on screen.

        Embedding is not showing: `QMdiArea.addSubWindow` leaves the subwindow
        hidden when the area is already on screen, which is the state of the
        application whenever the user plots anything. Measured on the reference
        case with the area shown, three of the four plot entries — the selected
        signals as slices, the table view and the stacked view — registered and
        embedded a window that stayed invisible: the figure was in the
        bookkeeping, named by the *Windows* menu, and never reached
        the screen. The one entry that worked did it by calling `show()` itself,
        which is why the fix lives here: whoever embeds a figure means the user
        to see it.

        It answers the subwindow it made: whoever opened the figure on the
        user's behalf can bring it to the front on top of every other window of
        the session -- the shot view is still the active window when a gesture
        opens a figure behind it, and raising it and giving it the input focus
        is what makes the click read as something. A caller that did not ask
        for the window ignores the result and works as it did.
        """
        subWindow = QVizMdiSubWindow(self)
        # `setWidget` copies the widget's title to the subwindow and leaves
        # everything else to the widget: the hover over the title bar is
        # answered by the subwindow, which is what the user hovers, so the URI
        # it carries on has to be handed over here, whatever the frame was told.
        subWindow.setWidget(plotWidget)
        subWindow.setToolTip(plotWidget.toolTip() or '')
        subWindow.resize(plotWidget.width(), plotWidget.height())
        if self.getMDI() is not None:
            self.getMDI().addSubWindow(subWindow)
        else:
            self.subWindow = subWindow
        subWindow.show()
        # A window is now in the area: the moment the preferred layout (a
        # preference, one-shot) is applied to it.
        self._maybeApplyPreferredLayout()
        return subWindow

    def LoadListOfIDSs(self, dataTreeView, namesOfIDSs, occurrence=0):
        """Load given IDSs for given occurrence.

        Arguments:
            dataTreeView (obj)   : Instance of DTV.
            namesOfIDSs  (list)  : List of IDS names (strings)
            occurrence   (int)   : IDS occurrence
        """

        for idsName in namesOfIDSs:
            if not self.IDSDataAlreadyFetched(dataTreeView=dataTreeView,
                                              IDSName=idsName,
                                              occurrence=occurrence):
                self.LoadIDSData(dataTreeView, idsName, occurrence)

    def getAll_0D_1D_Nodes(self, node, errorBars=False, str_filter=None, plotAxis=None):
        children_id, children = self.getChildren_(node, set(), [], str_filter, errorBars, plotAxis)
        children.sort(key=getNodePath)
        return children_id, children

    def getChildren_(self, item, children_id, children, str_filter, errorBars, plotAxis):
        criteria = plotAxis == 'TIME'
        for row in range(item.childCount()):
            child_item = item.child(row)
            # print("--------------> checking :", child_item.getPath(), " plotAxis=", plotAxis)
            if not child_item.isStructure() and not child_item.isArrayOfStructure() and \
                    child_item.isDynamicData() and (child_item.is1D() or criteria * child_item.is0D()) and \
                    child_item.hasAvailableData():

                if not errorBars and "_error_" not in child_item.getPath():
                    if str_filter is None or (str_filter is not None and str_filter
                                              in child_item.getPath()):
                        if not id(child_item) in children_id:
                            # print("--------------> adding :", item.getPath())
                            children_id.add(id(child_item))
                            children.append(child_item)
            elif child_item.isIDSRoot() or child_item.isStructure() or child_item.isArrayOfStructure():
                children_id, children = self.getChildren_(child_item, children_id,
                                                          children, str_filter, errorBars, plotAxis)
        return children_id, children

    def find_nearest(self, array, value):
        array = np.asarray(array)
        idx = (np.abs(array - value)).argmin()
        return array[idx], idx

    def getAllPlottable_0D_1D_Signals(self, dtv_nodes, dataTreeView, plotWidget=None,
                                      profile_center=True):
        s_list = []
        for node in dtv_nodes:
            try:
                coordinate1_index = 0
                closest_value = 0
                if node.is1D() and plotWidget.plotAxis == 'TIME' and profile_center:
                    coordinate1_values = node.coordinateValues(coordinateNumber=1, dataTreeView=node.dataTreeView)
                    # print(node.getParametrizedDataPath() + '=', len(coordinate1_values))
                    # closest_value, coordinate1_index = self.find_nearest(coordinate1_values,
                    #                                                      np.max(coordinate1_values) / 2)
                    coordinate1_index = int(coordinate1_values.size / 2)
                    # closest_value, coordinate1_index = coordinate1_values[int(coordinate1_values.size)]
                    closest_value = coordinate1_values[coordinate1_index]

                s = self.GetSignal(dataTreeView=dataTreeView,
                                   vizTreeNode=node,
                                   coordinate1_index=coordinate1_index,
                                   plotWidget=plotWidget)
                s_list.append((node, s, closest_value))
            except Exception as e:
                print(e)
                continue
        return s_list

    def updateAllPlottable_0D_1D_Signals(self, s_list, time_index, plotWidget=None, profile_center=True):
        s_new_list = []
        for s in s_list:
            try:
                node = s[0]
                coordinate1_index = 0
                #closest_value = 0
                if node.is1D() and plotWidget.plotAxis == 'TIME' and profile_center:
                    coordinate1_values = node.coordinateValues(coordinateNumber=1, dataTreeView=node.dataTreeView)
                    # print(node.getParametrizedDataPath() + '=', len(coordinate1_values))
                    coordinate1_index = int(coordinate1_values.size / 2)
                    # closest_value, coordinate1_index = coordinate1_values[int(coordinate1_values.size)]
                    closest_value = coordinate1_values[coordinate1_index]
                snew = self.GetSignal(dataTreeView=node.dataTreeView,
                                      vizTreeNode=node,
                                      time_index=time_index,
                                      coordinate1_index=coordinate1_index,
                                      plotWidget=plotWidget)
                s_new_list.append((node, snew, coordinate1_index))
            except Exception as e:
                print(e)
                continue
        return s_new_list

    def modifyTitle(self, title, ids_name, slices_aos_name):
        if ids_name is not None:
            index = title.find(ids_name)
            if index == -1:
                return title
            return title[index:]
        elif slices_aos_name is not None:
            if 'itime' in title:
                title = title.replace("itime", ":")
            slices_aos_name = QVizGlobalOperations.makeIMASPath(slices_aos_name)
            index = title.find(slices_aos_name)
            if index == -1:
                return title
            return title[index + len(slices_aos_name) + 4:]
