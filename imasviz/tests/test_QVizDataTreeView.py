# This example demonstrates the use of PyQt5 to construct
# the imasviz treeview
# GateWay: The next modules are required (written 25. July 2018):
# module load itm-python/3.6
# module load itm-qt/5.8.0

import sys

from PyQt5.QtWidgets import QApplication

from imasviz.Browser_API import Browser_API
from imasviz.pyqt5.VizDataSource.QVizDataSourceFactory import DataSourceFactory
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.util.GlobalValues import GlobalValues

if __name__ == '__main__':

    # Set global environment variables and settings
    GlobalOperations.checkEnvSettings()

    # Set API (Application Programing Interface) object
    api = Browser_API()

    # Get IDS data source
    dataSource = DataSourceFactory().create(dataSourceName=GlobalValues.IMAS_NATIVE,
                                            shotNumber=52702,
                                            runNumber=1,
                                            userName='imas_public',
                                            imasDbName='west')

    # Create application
    app = QApplication(sys.argv)
    app.processEvents()

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
    w = api.CreateDataTree(dataSource=dataSource)

    w.show()
    sys.exit(app.exec_())