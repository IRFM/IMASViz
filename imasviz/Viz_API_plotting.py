# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The plotting side of the api.

Everything that puts a window on the screen: the plot commands, the
embedding, the loads, the signal read, and the 0D/1D node walk the
legacy window still uses.
"""

import numpy as np

from imasviz.VizUtils import QVizGlobalOperations
from imasviz.Viz_API_chrome import (DEFAULT_FIGURE_SIZE,
                                   QVizMdiSubWindow, getNodePath)


class QVizPlottingMixin:
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

    def GetSignal(self, dataTreeView, vizTreeNode, as_function_of_time=None,
                  coordinate1_index=0, time_index=None, plotWidget=None,
                  slices=None, abscissa=None):
        from imasviz.VizDataAccess.QVizDataAccessFactory import QVizDataAccessFactory
        try:
            signalDataAccess = QVizDataAccessFactory(dataTreeView.dataSource).create()
            return signalDataAccess.GetSignal(treeNode=vizTreeNode,
                                              plotWidget=plotWidget,
                                              as_function_of_time=as_function_of_time,
                                              coordinate_index=coordinate1_index,
                                              time_index=time_index,
                                              slices=slices,
                                              abscissa=abscissa)
        except:
            raise

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

        The subwindow settles on the size hint of the frame it holds, and a
        content widget that carries none -- a bare one, or a container whose
        layout does not propagate its children -- settles to 120x28 whatever
        it was told before the show: `QWidget.grab()` takes the screenshot at
        that size, which is the unreadable picture the user reported. The rule
        judges the floor from the size the subwindow *settles to* and hands it
        ``DEFAULT_FIGURE_SIZE`` when that is below 300 on a side, leaving alone
        the frames that already answer a readable size (a pyqtgraph figure
        settles to its own 600x480). A session's saved geometry is applied
        *after* this embed, over the rule, and ``DEFAULT_FIGURE_SIZE`` is the
        same constant ``focus_window`` (``imasviz.VizAgent.core``) puts a
        window back to.
        """
        subWindow = QVizMdiSubWindow(self)
        # `setWidget` copies the widget's title to the subwindow and leaves
        # everything else to the widget: the hover over the title bar is
        # answered by the subwindow, which is what the user hovers, so the URI
        # it carries on has to be handed over here, whatever the frame was told.
        subWindow.setWidget(plotWidget)
        subWindow.setToolTip(plotWidget.toolTip() or '')
        if self.getMDI() is not None:
            self.getMDI().addSubWindow(subWindow)
        else:
            self.subWindow = subWindow
        subWindow.show()
        # The subwindow settles on the size hint of the frame it holds, not on
        # the size the frame was told before the show: a bare content widget
        # settles to 120x28 whatever it was resized to, and a pyqtgraph figure
        # settles to its own 600x480. Judged on the size the frame *was told*,
        # the floor reaches neither -- the 120x28 screenshot answers 640x480
        # before the show, so the floor would skip it, and the already-readable
        # figure answers 640x480 too, so it would be resized into the default
        # for no reason. Judged on the size the subwindow *settles to*, the
        # floor reaches exactly the windows too small for `QWidget.grab()` to
        # make a readable screenshot and leaves the ones that are not:
        # measured, a bare frame settles to 120x28 (the floor hands it
        # DEFAULT_FIGURE_SIZE) and a pyqtgraph figure settles to 608x508 (the
        # floor leaves it).
        width, height = subWindow.width(), subWindow.height()
        if width < 300 and height < 300:
            # A resize done before the show survives nothing -- the first show
            # settles the subwindow on the size hint -- so the default is
            # re-asserted after it, where it answers for itself. The frame it
            # carries follows, in the client area the shell leaves it: the
            # picture a `QWidget.grab()` takes is DEFAULT_FIGURE_SIZE minus the
            # shell's own chrome, and that is the size the page serves.
            subWindow.resize(*DEFAULT_FIGURE_SIZE)
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

