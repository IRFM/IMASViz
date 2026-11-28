# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The shot views of a run.

One frame per opened case -- the agent opens it, the *Windows* menu lists
it, closing it frees the case. State lives on the api: ``DTVframeList``,
``DTVlist`` and the per-view ``dataSource``.
"""

import shiboken6

from imasviz.Viz_API_chrome import QVizMdiSubWindow


class QVizShotViewsMixin:
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

