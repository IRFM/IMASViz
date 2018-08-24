
import os
import sys
from imasviz.data_source.DataSourceFactory import DataSourceFactory
from imasviz.Browser_API import Browser_API
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.util.GlobalValues import GlobalValues
from imasviz.data_source.IMASDataSource import IMASDataSource
from PyQt5.QtWidgets import QTabWidget, QWidget, QFormLayout, QApplication, QLineEdit, \
    QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout, QRadioButton, QLabel, QGridLayout
from imasviz.view.WxDataTreeView import TextCtrlLogger


class GUIFrame(QTabWidget):
    def __init__(self, parent):
        super(GUIFrame, self).__init__(parent)
        self.setGeometry(300,300,600,400)
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()

        self.addTab(self.tab1, "Local data source")
        self.addTab(self.tab2, "Experiment data source")
        self.addTab(self.tab3, "Scripting")

        self.tabOne()
        #self.tabTwo()
        #self.tabThree()
        title = "IMAS_VIZ (version " + str(GlobalValues.IMAS_VIZ_VERSION) + ")"
        self.setWindowTitle(title)

        # self.Bind(wx.EVT_CLOSE, self.onClose)
        self.handlerValue = 0
        self.dataSourceName = GlobalValues.IMAS_NATIVE  # default value
        self.shell = None
        # self.GUIFrameSingleton = GUIFrameSingleton

    # def onClose(self, event):
    #     if GlobalOperations.YesNo(self, "Exit IMAS_VIZ ?", "Please confirm"):
    #         sys.exit(0)

    def tabOne(self):

        self.dataSource = None
        layout = QVBoxLayout()

        vboxLayout = QFormLayout()
        """Set static text for each GUI box (left from the box itself) """
        self.userName = QLineEdit()
        vboxLayout.addRow('User name', self.userName)
        self.imasDbName = QLineEdit()
        vboxLayout.addRow('IMAS database name', self.imasDbName)
        self.shotNumber = QLineEdit()
        vboxLayout.addRow('Shot number', self.shotNumber)
        self.runNumber = QLineEdit()
        vboxLayout.addRow('Run number', self.runNumber)
        self.button_open = QPushButton('Open', self)
        #vboxLayout.addWidget(self.button_open)
        #layout.addRow('', vboxLayout)
        #layout.addRow('', self.button_open)
        layout.addLayout(vboxLayout)

        vboxLayout2 = QVBoxLayout()
        vboxLayout2.addWidget(self.button_open)

        layout.addLayout(vboxLayout2)

        vboxLayout3 = QVBoxLayout()
        qlabel = QLabel('Log window')
        vboxLayout3.addWidget(qlabel)
        self.logWindow = QTextEdit("Welcome to IMAS_VIZ!")
        vboxLayout3.addWidget(self.logWindow)
        layout.addLayout(vboxLayout3)
        self.log = TextCtrlLogger(self.logWindow)
        self.tab1.setLayout(layout)

        # logging
    def CheckInputs(self):
        """Get IDS parameters from the GUI widgets"""
        userName = self.userName.text()
        imasDbName = self.imasDbName.text()
        shotnumbertext = self.shotNumber.text()
        runnumbertext = self.runNumber.text()

        """Display warning message if the required parameter was not specified"""
        if userName == '':
            raise ValueError("'User name' field is empty.")

        if imasDbName == '':
            raise ValueError("'IMAS database name' field is empty.")

        if shotnumbertext == '' or runnumbertext == '':
            raise ValueError("'Shot number' or 'run number' field is empty.")

        """Check if data source is available"""
        GlobalOperations.check(self.dataSourceName, int(shotnumbertext))

    # def Open(self, evt):
    #     try:
    #
    #         from imasviz.view.HandlerName import HandlerName
    #
    #         """ Check if all required IDS parameters were specified"""
    #         self.CheckInputs()
    #
    #         """ Get API handler name ('api_...')"""
    #         apiHandlerName = HandlerName.getAPIHandler(0)
    #         if  self.GUIFrameSingleton.handlerValue == 0:
    #             """IMAS-VIZ shell: Print"""
    #             self.shell.run(apiHandlerName + " = Browser_API()")
    #
    #         """IDS database check"""
    #         if self.dataSourceName == GlobalValues.IMAS_NATIVE:
    #
    #             """Try to open the specified IDS database """
    #             IMASDataSource.try_to_open(self.imasDbName.GetValue(),
    #                                        self.userName.GetValue(),
    #                                        int(self.shotNumber.GetValue()),
    #                                        int(self.runNumber.GetValue()))
    #
    #             for i in range(0, 10):
    #                 vname = "MDSPLUS_TREE_BASE_" + str(i)
    #                 mds = os.environ['HOME']  + "/public/imasdb/" \
    #                       + self.imasDbName.GetValue() + "/3/" + str(i)
    #                 os.environ[vname] = mds
    #
    #         """Get data source factory handler name ('dsf_...')"""
    #         dataSourceFactoryHandlerName = HandlerName  \
    #             .getDataSourceFactoryHandler(self.GUIFrameSingleton.handlerValue)
    #
    #         """IMAS-VIZ shell: Print"""
    #         self.shell.run(dataSourceFactoryHandlerName
    #             + " = DataSourceFactory()")
    #
    #         """Get data source handler name ('ds_...')"""
    #         dataSourceHandlerName = HandlerName.getDataSourceHandler(
    #             self.GUIFrameSingleton.handlerValue)
    #
    #         """IMAS-VIZ shell: Print"""
    #         self.shell.run(dataSourceHandlerName + " = "
    #             + dataSourceFactoryHandlerName + ".create("
    #             + self.shotNumber.GetValue() + ","
    #             + self.runNumber.GetValue() + ",'"
    #             + self.userName.GetValue() + "','"
    #             + self.imasDbName.GetValue() + "','"
    #             + self.dataSourceName + "')")
    #
    #         """Get view handler name ('dtv_...')"""
    #         viewhandlerName = HandlerName.getWxDataTreeViewHandler(
    #             self.GUIFrameSingleton.handlerValue)
    #         """IMAS-VIZ shell: Print"""
    #         self.shell.run(viewhandlerName + " = " + apiHandlerName
    #             + ".CreateDataTree(" + dataSourceHandlerName + ")")
    #         """IMAS-VIZ shell: Execute"""
    #         self.shell.push(apiHandlerName + ".ShowDataTree("
    #             + viewhandlerName + ")")
    #         """IMAS-VIZ shell: Execute"""
    #         self.shell.push(viewhandlerName + ".Center()")
    #
    #         """Set GUI Frame handler value (0 by default)"""
    #         self.GUIFrameSingleton.handlerValue += 1
    #
    #     except ValueError as e:
    #         self.log.error(str(e))


# class tabTwo(self):
#     wx.Panel.__init__(self,parent)
#     wx.StaticText(self,-1,"Scripting ",(20,20))
#     vbox = wx.BoxSizer(wx.VERTICAL)
#     self.shell = wx.py.shell.Shell(self, -1)
#     vbox.Add(self.shell, 1, wx.EXPAND | wx.TOP | wx.RIGHT | wx.LEFT, 15)
#     self.SetSizer(vbox)

    def tabThree(self):

        layout = QFormLayout()

        """Set static text for each GUI box (left from the box itself) """
        self.shotNumber = QLineEdit()
        layout.addRow('Shot number', self.shotNumber)
        self.runNumber = QLineEdit()
        layout.addRow('Run number', self.runNumber)

        self.button_open = QPushButton('Open', self)

        #hboxRadioButtons = QHBoxLayout()
        #hboxRadioButtons.addWidget(QRadioButton("Unified Data Access"))
        #hboxRadioButtons.addWidget(QRadioButton("Tore Supra"))
        #layout.addRow(QLabel(""), hboxRadioButtons)


        if 'UDA_LOG' in os.environ:
            publicDatabases = ['WEST', 'TCV', 'JET', 'AUG']
        else:
            publicDatabases = ['WEST']

        # self.machineName = wx.Choice(self, choices=publicDatabases,
        #                                  style=wx.CB_READONLY)
        #     self.machineName.SetSelection(0)
        #
        #     button_open = wx.Button(self, 1, 'Open')
        #
        #     self.logWindow = wx.TextCtrl(self,
        #                         wx.ID_ANY,"Welcome to the IMAS data browser !\n",
        #                         size=(500, 150),
        #                         style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
        #
        #     # Radio buttons
        #     hboxRadioButtons.Add(self.rb1, 1, wx.EXPAND | wx.ALL, 5)
        #     hboxRadioButtons.Add(self.rb2, 1, wx.EXPAND | wx.ALL, 5)
        #
        #     self.gridSizer_native.Add(self.machineName, 0, wx.LEFT, 10)
        #     self.gridSizer_native.Add(self.blankText, 0, wx.LEFT, 10)
        #     self.gridSizer_native.Add(self.shotNumberStaticText, 0, wx.LEFT, 10)
        #     self.gridSizer_native.Add(self.shotNumber, 0, wx.LEFT, 10)
        #     self.gridSizer_native.Add(self.runNumberStaticText, 0, wx.LEFT, 10)
        #     self.gridSizer_native.Add(self.runNumber, 0, wx.LEFT, 10)
        #
        #     self.gridSizer_tore_supra.Add(self.shotNumberStaticTextTS, 0, wx.LEFT, 10)
        #     self.gridSizer_tore_supra.Add(self.shotNumberTS, 0, wx.LEFT, 10)
        #     self.gridSizer_tore_supra.Add(self.runNumberStaticTextTS, 0, wx.LEFT, 10)
        #     self.gridSizer_tore_supra.Add(self.runNumberTS, 0, wx.LEFT, 10)
        #
        #     self.vbox.Add(hboxRadioButtons, 0, wx.TOP, 10)
        #     self.vbox.Add(self.gridSizer_native, 0, wx.TOP, 10)
        #     self.vbox.Add(self.gridSizer_tore_supra, 0, wx.TOP, 10)
        #     self.vbox.Add(button_open, 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 60)
        #     self.vbox.Add(self.logWindow, 1, wx.ALL|wx.EXPAND, 5)
        #
        #     self.Bind(wx.EVT_RADIOBUTTON, self.SwitcherNative, id=self.rb1.GetId())
        #     self.Bind(wx.EVT_RADIOBUTTON, self.SwitcherTS, id=self.rb2.GetId())
        #
        #     self.Bind(wx.EVT_BUTTON, self.Open, id=1)
        #
        #     self.SetSizer(self.vbox)
        #
        #     self.dataSourceName = GlobalValues.IMAS_UDA  # default value
        #
        #     self.rb1.SetValue(True)
        #     self.rb2.Enable(False)
        #
        #     self.shell = None
        #
        #     self.GUIFrameSingleton = GUIFrameSingleton
        #
        #     from imasviz.view.WxDataTreeView import TextCtrlLogger
        #
        #     self.log = TextCtrlLogger(self.logWindow)
        #
        #     self.vbox.Hide(2)
        #     self.vbox.Show(1)
        #
        #     self.runNumber.SetEditable(True)
        self.button_open = QPushButton('Open', self)

        """Set and display Welcome Text in the log window"""
        self.logWindow = QTextEdit()
        layout.addRow('Log window', self.button_open)
        self.log = TextCtrlLogger(self.logWindow)
        self.tab2.setLayout(layout)


    # def SwitcherTS(self, evt):
    #     self.dataSourceName = GlobalValues.TORE_SUPRA
    #     self.vbox.Hide(1)
    #     self.vbox.Show(2)
    #     self.Layout()
    #     self.runNumberTS.SetValue('0')
    #     self.runNumberTS.SetEditable(False)
    #
    #
    # def SwitcherNative(self, evt):
    #     self.dataSourceName = GlobalValues.IMAS_NATIVE
    #     self.vbox.Hide(2)
    #     self.vbox.Show(1)
    #     self.Layout()

    def CheckInputs(self):

        if self.rb1.GetValue():

            machineName = \
                self.machineName.GetString(self.machineName.GetSelection())
            shotnumbertext = self.shotNumber.GetValue()
            runnumbertext = self.runNumber.GetValue()

            if machineName == '':
                raise ValueError("'UDA name' field is empty.")

            if shotnumbertext == '':
                raise ValueError("'Shot number' field is empty.")

            if runnumbertext == '':
                raise ValueError("'Run number' field is empty.")

        # else:
        #     shotnumbertext = self.shotNumberTS.GetValue()
        #     runnumbertext =  self.runNumberTS.GetValue()
        #
        #     if shotnumbertext == '' or runnumbertext == '' :
        #         raise ValueError("'Shot number' or 'run number' field is empty.")

        GlobalOperations.check(self.dataSourceName, int(shotnumbertext))


    # def Open(self, evt):
    #
    #     try:
    #
    #         from imasviz.view.HandlerName import HandlerName
    #
    #         self.CheckInputs()
    #
    #         apiHandlerName = HandlerName.getAPIHandler(0)
    #         if  self.GUIFrameSingleton.handlerValue == 0:
    #             self.shell.run(apiHandlerName + " = Browser_API()")
    #
    #         if self.dataSourceName == GlobalValues.IMAS_UDA:
    #             IMASDataSource.try_to_open_uda_datasource(
    #                 self.machineName.GetString(self.machineName.GetSelection()),
    #                 int(self.shotNumber.GetValue()),
    #                 int(self.runNumber.GetValue()))
    #
    #         dataSourceFactoryHandlerName = HandlerName\
    #             .getDataSourceFactoryHandler(self.GUIFrameSingleton.handlerValue)
    #         self.shell.run(dataSourceFactoryHandlerName
    #                        + " = DataSourceFactory()")
    #
    #         dataSourceHandlerName = HandlerName.getDataSourceHandler(
    #             self.GUIFrameSingleton.handlerValue)
    #
    #         if self.rb1.GetValue():
    #             self.shell.run(dataSourceHandlerName + " = "
    #                            + dataSourceFactoryHandlerName
    #                            + ".createUDADatasource("
    #                            + self.shotNumber.GetValue() + ","
    #                            + self.runNumber.GetValue() + ",'"
    #                            + self.machineName.GetString(self
    #                                                         .machineName
    #                                                         .GetSelection())
    #                            + "')")
    #         else:
    #             self.shell.run(
    #                 dataSourceHandlerName + " = "
    #                 + dataSourceFactoryHandlerName + ".create("
    #                 + self.shotNumberTS.GetValue() +
    #                 "," + self.runNumberTS.GetValue() + ",None, None,'"
    #                 + self.dataSourceName + "')")
    #
    #         viewhandlerName = HandlerName\
    #             .getWxDataTreeViewHandler(self.GUIFrameSingleton.handlerValue)
    #         self.shell.run(viewhandlerName + " = " + apiHandlerName
    #                        + ".CreateDataTree(" + dataSourceHandlerName + ")")
    #         self.shell.push(apiHandlerName + ".ShowDataTree("
    #                         + viewhandlerName + ")")
    #         self.shell.push(viewhandlerName + ".Center()")
    #
    #         self.GUIFrameSingleton.handlerValue += 1
    #
    #     except ValueError as e:
    #         self.log.error(str(e))



# class MyApp(wx.App):
#
#     def OnInit(self):
#         GlobalOperations.checkEnvSettings()
#         label = "IMAS_VIZ (version " + str(GlobalValues.IMAS_VIZ_VERSION) + ")"
#         frm = GUIFrame(None, -1, label)
#         frm.Centre()
#         frm.Show(True)
#         return True
#
# if __name__ == "__main__":
#     app = MyApp(0)
#     app.MainLoop()


def main():
    app = QApplication(sys.argv)
    ex = GUIFrame(None)
    ex.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
