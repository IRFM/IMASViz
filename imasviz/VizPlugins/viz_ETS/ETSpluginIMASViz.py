#  Name   : ETSpluginIMASViz
#
#           IMASViz wrapper for ETS plugin.
#
#  Author :
#         Dejan Penko
#  E-mail :
#         dejan.penko@lecad.fs.uni-lj.si
#
# ****************************************************
#     Copyright(c) 2019- D. Penko

import sys
import os
sys.path.append(os.getenv('VIZ_HOME')+'/imasviz/VizPlugins/viz_ETS/ets-viz')

from imasviz.VizPlugins.VizPlugin import VizPlugin
from imasviz.VizPlugins.viz_ETS.ets_viz.ETSViz import ETSViz
import logging
from PyQt5.QtWidgets import QMdiSubWindow
import traceback


class ETSpluginIMASViz(VizPlugin):

    def __init__(self):
        self.ids = None
        self.IDS_parameters = {}

    def execute(self, vizAPI, pluginEntry):
        """Main plugin function.
        """

        # Get dataSource from the VizAPI (Application Program Interface)
        # Note: instance of "self.datatreeView" is provided by the VizPlugins
        # through inheritance
        dataSource = vizAPI.GetDataSource(self.dataTreeView)
        shot = dataSource.shotNumber
        run = dataSource.runNumber
        device = dataSource.imasDbName
        user = dataSource.userName
        ts = 2.0
        occurrence = 0

        # Check if the IDS data is already loaded in IMASviz. If it is not,
        # load it (LoadListOfIDSs contains this IDS check strategy)
        ids_list = ['core_profiles', 'core_sources', 'core_transport',
                    'equilibrium']
        vizAPI.LoadListOfIDSs(self.dataTreeView, ids_list, occurrence)

        # Get IDS
        self.ids = dataSource.getImasEntry(occurrence)

        self.IDS_parameters["shot"] = shot
        self.IDS_parameters["run"] = run
        self.IDS_parameters["user"] = user
        self.IDS_parameters["database"] = device

        self.ets = ETSViz(self.IDS_parameters, self.ids)
        if self.dataTreeView.window().objectName() == "IMASViz root window":

            subwindow = QMdiSubWindow()
            subwindow.setWidget(self.ets)
            self.dataTreeView.window().getMDI().addSubWindow(self.ets)

        try:
            self.ets.tabETSSummary.plot()
            self.ets.show()

        except Exception as err:
            logging.error("ERROR in ETS wrapper! (%s)" % err, exc_info=True)
            traceback.print_exc()
            logging.error(traceback.format_exc())

    def getEntries(self):
        if self.selectedTreeNode.getIDSName() == "core_profiles":
            return [0]

    def getPluginsConfiguration(self):
        return None

    def getAllEntries(self):
        """ Set a text which will be displayed in the pop-up menu.
        """
        return [(0, 'ETS plugin...')]

    def getDescription(self):
        """ Return plugin description.
        """

        return "Visualization tool for ETS6 related data. \n" \
               "This is ETSViz embedded in IMASViz as a plugin. \n" \
               "Authors: Dejan Penko (dejan.penko@lecad.fs.uni-lj.si)."

    def isEnabled(self):
        return True