# This example demonstrates the use of IMASViz QtDataTreeView.py to construct
# the imasviz treeview
# GateWay: The next modules are required (written 25. July 2018):
# module load itm-python/3.6
# module load itm-qt/5.8.0

# Simple PyQt5 treeview example:
# https://joekuan.wordpress.com/2016/02/11/pyqt-how-to-hide-top-level-nodes-in-tree-view/

from imasviz.pyqt5.src.VizGUI.VizTreeView.QVizDataTreeView import QVizDataTreeViewFrame
from PyQt5.QtWidgets import QApplication
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.data_source.DataSourceFactory import DataSourceFactory
import os, sys

from imasviz.Browser_API import Browser_API

if __name__ == '__main__':

    # Set global environment variables and settings
    GlobalOperations.checkEnvSettings()

    # Set API (Application Programing Interface) object
    api = Browser_API()

    # Get IDS data source
    dataSource = DataSourceFactory().create(dataSourceName=GlobalValues.IMAS_NATIVE,
                                            shotNumber=52344,
                                            runNumber=1,
                                            userName='g2penkod',
                                            imasDbName='test')


    # Create application
    app = QApplication(sys.argv)

    # Get IDSDefFile
    # IDSDefFile = GlobalOperations.getIDSDefFile(os.environ['IMAS_VERSION'])

    # OPTION 1:
    # Create Data Tree View directly using QVizDataTreeViewFrame class
    # w = QVizDataTreeViewFrame(parent=None,
    #                           views={},
    #                           dataSource=dataSource,
    #                           IDSDefFile=IDSDefFile)

    # OPTION 2:
    # Create Data Tree View using API function
    w = api.QCreateDataTree(dataSource=dataSource)

    w.show()
    sys.exit(app.exec_())