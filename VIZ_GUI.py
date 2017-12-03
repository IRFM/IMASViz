import wx.py
import os
import sys
from imasviz.data_source.DataSourceFactory import DataSourceFactory
from imasviz.Browser_API import Browser_API
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.util.GlobalValues import GlobalValues
from imasviz.data_source.IMASDataSource import IMASDataSource


class TabOne(wx.Panel):
    def __init__(self,parent, GUIFrameSingleton):
        wx.Panel.__init__(self,parent)

        self.dataSource = None

        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.gridSizer_native = wx.GridSizer(rows=5, cols=2, hgap=5, vgap=5)

        self.userNameStaticText = wx.StaticText(self, -1, 'User name  ')
        self.imasDbNameStaticText = wx.StaticText(self, -1, 'IMAS database name  ')
        self.shotNumberStaticText = wx.StaticText(self, -1, 'Shot number  ')
        self.runNumberStaticText = wx.StaticText(self, -1, 'Run number')

        self.userName = wx.TextCtrl(self, -1, os.environ["USER"], size=(150, -1))
        self.imasDbName = wx.TextCtrl(self, -1,  size=(150, -1))

        self.shotNumber= wx.TextCtrl(self, -1, size=(150, -1))
        self.runNumber = wx.TextCtrl(self, -1, '0', size=(150, -1))

        button_open = wx.Button(self, 1, 'Open')

        self.logWindow = wx.TextCtrl(self, wx.ID_ANY,"Welcome to the IMAS data browser !\n", size=(500, 100), style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)

        self.gridSizer_native.Add(self.userNameStaticText, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.userName, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.imasDbNameStaticText, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.imasDbName, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.shotNumberStaticText, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.shotNumber, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.runNumberStaticText, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.runNumber, 0, wx.LEFT, 10)

        self.vbox.Add(self.gridSizer_native, 0, wx.TOP, 10)
        self.vbox.Add(button_open, 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 60)
        self.vbox.Add(self.logWindow, 1, wx.ALL|wx.EXPAND, 5)

        self.Bind(wx.EVT_BUTTON, self.Open, id=1)

        self.SetSizer(self.vbox)
        self.dataSourceName = GlobalValues.IMAS_NATIVE  # default value
        self.shell = None
        self.GUIFrameSingleton = GUIFrameSingleton

        from imasviz.view.WxDataTreeView import TextCtrlLogger

        self.log = TextCtrlLogger(self.logWindow)

        # logging
    def CheckInputs(self):

        userName = self.userName.GetValue()
        imasDbName = self.imasDbName.GetValue()
        shotnumbertext = self.shotNumber.GetValue()
        runnumbertext = self.runNumber.GetValue()

        if userName == '':
            raise ValueError("'User name' field is empty.")

        if imasDbName == '':
            raise ValueError("'IMAS database name' field is empty.")

        if shotnumbertext == '' or runnumbertext == '':
            raise ValueError("'Shot number' or 'run number' field is empty.")

        GlobalOperations.check(self.dataSourceName, int(shotnumbertext))


    def Open(self, evt):

        try:

            from imasviz.view.HandlerName import HandlerName

            self.CheckInputs()

            apiHandlerName = HandlerName.getAPIHandler(0)
            if  self.GUIFrameSingleton.handlerValue == 0:
                self.shell.run(apiHandlerName + " = Browser_API()")

            if self.dataSourceName == GlobalValues.IMAS_NATIVE:

                IMASDataSource.try_to_open(self.imasDbName.GetValue(), self.userName.GetValue(), int(self.shotNumber.GetValue()), int(self.runNumber.GetValue()))

                for i in xrange(0, 10):
                    vname = "MDSPLUS_TREE_BASE_" + str(i)
                    mds = os.environ['HOME']  + "/public/imasdb/" + self.imasDbName.GetValue() + "/3/" + str(i)
                    os.environ[vname] = mds


            dataSourceFactoryHandlerName = HandlerName.getDataSourceFactoryHandler(self.GUIFrameSingleton.handlerValue)
            self.shell.run(dataSourceFactoryHandlerName + " = DataSourceFactory()")

            dataSourceHandlerName = HandlerName.getDataSourceHandler(self.GUIFrameSingleton.handlerValue)

            self.shell.run(dataSourceHandlerName + " = " + dataSourceFactoryHandlerName + ".create(" +
                           self.shotNumber.GetValue() + ","  + self.runNumber.GetValue() + ",'" +
                           self.userName.GetValue() + "','" + self.imasDbName.GetValue() + "','" + self.dataSourceName + "')")

            viewhandlerName = HandlerName.getWxDataTreeViewHandler(self.GUIFrameSingleton.handlerValue)
            self.shell.run(viewhandlerName + " = " + apiHandlerName + ".CreateDataTree(" + dataSourceHandlerName + ")")
            self.shell.push(apiHandlerName + ".ShowDataTree(" + viewhandlerName + ")")
            self.shell.push(viewhandlerName + ".Center()")

            self.GUIFrameSingleton.handlerValue += 1

        except ValueError as e:
            self.log.error(str(e))


class TabTwo(wx.Panel):
    def __init__(self,parent):
        wx.Panel.__init__(self,parent)
        wx.StaticText(self,-1,"Scripting ",(20,20))
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.shell = wx.py.shell.Shell(self, -1)
        vbox.Add(self.shell, 1, wx.EXPAND | wx.TOP | wx.RIGHT | wx.LEFT, 15)
        self.SetSizer(vbox)

class TabThree(wx.Panel):
    def __init__(self,parent, GUIFrameSingleton):
        wx.Panel.__init__(self,parent)

        self.dataSource = None

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        hboxRadioButtons = wx.BoxSizer(wx.HORIZONTAL)

        self.gridSizer_native = wx.GridSizer(rows=4, cols=2, hgap=5, vgap=5)
        self.gridSizer_tore_supra = wx.GridSizer(rows=2, cols=2, hgap=5, vgap=5)

        self.rb1 = wx.RadioButton(self, -1, 'Unified Data Access')
        self.rb2 = wx.RadioButton(self, -1, 'Tore Supra')

        self.shotNumberStaticText = wx.StaticText(self, -1, 'Shot number  ')
        self.runNumberStaticText = wx.StaticText(self, -1, 'Run number')
        self.blankText = wx.StaticText(self, -1, '')

        self.shotNumberStaticTextTS = wx.StaticText(self, -1, 'Shot number  ')
        self.runNumberStaticTextTS = wx.StaticText(self, -1, 'Run number')

        self.shotNumber= wx.TextCtrl(self, -1, size=(150, -1))
        self.runNumber = wx.TextCtrl(self, -1, '0', size=(150, -1))


        self.shotNumberTS = wx.TextCtrl(self, -1, size=(150, -1))
        self.runNumberTS = wx.TextCtrl(self, -1, '0', size=(150, -1))

        publicDatabases = ['WEST']
        self.machineName = wx.Choice(self, choices=publicDatabases, style=wx.CB_READONLY)
        self.machineName.SetSelection(0)

        button_open = wx.Button(self, 1, 'Open')

        self.logWindow = wx.TextCtrl(self, wx.ID_ANY,"Welcome to the IMAS data browser !\n", size=(500, 150), style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)

        # Radio buttons
        hboxRadioButtons.Add(self.rb1, 1, wx.EXPAND | wx.ALL, 5)
        hboxRadioButtons.Add(self.rb2, 1, wx.EXPAND | wx.ALL, 5)

        self.gridSizer_native.Add(self.machineName, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.blankText, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.shotNumberStaticText, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.shotNumber, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.runNumberStaticText, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.runNumber, 0, wx.LEFT, 10)

        self.gridSizer_tore_supra.Add(self.shotNumberStaticTextTS, 0, wx.LEFT, 10)
        self.gridSizer_tore_supra.Add(self.shotNumberTS, 0, wx.LEFT, 10)
        self.gridSizer_tore_supra.Add(self.runNumberStaticTextTS, 0, wx.LEFT, 10)
        self.gridSizer_tore_supra.Add(self.runNumberTS, 0, wx.LEFT, 10)

        self.vbox.Add(hboxRadioButtons, 0, wx.TOP, 10)
        self.vbox.Add(self.gridSizer_native, 0, wx.TOP, 10)
        self.vbox.Add(self.gridSizer_tore_supra, 0, wx.TOP, 10)
        self.vbox.Add(button_open, 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 60)
        self.vbox.Add(self.logWindow, 1, wx.ALL|wx.EXPAND, 5)

        self.Bind(wx.EVT_RADIOBUTTON, self.SwitcherNative, id=self.rb1.GetId())
        self.Bind(wx.EVT_RADIOBUTTON, self.SwitcherTS, id=self.rb2.GetId())

        self.Bind(wx.EVT_BUTTON, self.Open, id=1)

        self.SetSizer(self.vbox)

        self.dataSourceName = GlobalValues.IMAS_UDA  # default value

        self.rb1.SetValue(True)

        self.shell = None

        self.GUIFrameSingleton = GUIFrameSingleton

        from imasviz.view.WxDataTreeView import TextCtrlLogger

        self.log = TextCtrlLogger(self.logWindow)

        self.vbox.Hide(2)
        self.vbox.Show(1)

        self.runNumber.SetEditable(False)


    def SwitcherTS(self, evt):
        self.dataSourceName = GlobalValues.TORE_SUPRA
        self.vbox.Hide(1)
        self.vbox.Show(2)
        self.Layout()
        self.runNumberTS.SetValue('0')
        self.runNumberTS.SetEditable(False)


    def SwitcherNative(self, evt):
        self.dataSourceName = GlobalValues.IMAS_NATIVE
        self.vbox.Hide(2)
        self.vbox.Show(1)
        self.Layout()

    def CheckInputs(self):

        if self.rb1.GetValue() :

            machineName = self.machineName.GetString(self.machineName.GetSelection())
            shotnumbertext = self.shotNumber.GetValue()
            runnumbertext = self.runNumber.GetValue()

            if machineName == '':
                raise ValueError("'UDA name' field is empty.")

            if shotnumbertext == '':
                raise ValueError("'Shot number' field is empty.")

            if runnumbertext == '':
                raise ValueError("'Run number' field is empty.")

        else:
            shotnumbertext = self.shotNumberTS.GetValue()
            runnumbertext =  self.runNumberTS.GetValue()

            if shotnumbertext == '' or runnumbertext == '' :
                raise ValueError("'Shot number' or 'run number' field is empty.")

        GlobalOperations.check(self.dataSourceName, int(shotnumbertext))


    def Open(self, evt):

        try:

            from imasviz.view.HandlerName import HandlerName

            self.CheckInputs()

            apiHandlerName = HandlerName.getAPIHandler(0)
            if  self.GUIFrameSingleton.handlerValue == 0:
                self.shell.run(apiHandlerName + " = Browser_API()")

            if self.dataSourceName == GlobalValues.IMAS_UDA:
                IMASDataSource.try_to_open_uda_datasource(self.machineName.GetString(self.machineName.GetSelection()), int(self.shotNumber.GetValue()), int(self.runNumber.GetValue()))

            dataSourceFactoryHandlerName = HandlerName.getDataSourceFactoryHandler(self.GUIFrameSingleton.handlerValue)
            self.shell.run(dataSourceFactoryHandlerName + " = DataSourceFactory()")

            dataSourceHandlerName = HandlerName.getDataSourceHandler(self.GUIFrameSingleton.handlerValue)

            if self.rb1.GetValue():
                self.shell.run(dataSourceHandlerName + " = " + dataSourceFactoryHandlerName + ".createUDADatasource(" +
                               self.shotNumber.GetValue() + "," + self.runNumber.GetValue() + ",'" +
                               self.machineName.GetString(self.machineName.GetSelection()) + "')")
            else:
                self.shell.run(
                    dataSourceHandlerName + " = " + dataSourceFactoryHandlerName + ".create(" + self.shotNumberTS.GetValue() +
                    "," + self.runNumberTS.GetValue() + ",None, None,'" + self.dataSourceName + "')")

            viewhandlerName = HandlerName.getWxDataTreeViewHandler(self.GUIFrameSingleton.handlerValue)
            self.shell.run(viewhandlerName + " = " + apiHandlerName + ".CreateDataTree(" + dataSourceHandlerName + ")")
            self.shell.push(apiHandlerName + ".ShowDataTree(" + viewhandlerName + ")")
            self.shell.push(viewhandlerName + ".Center()")

            self.GUIFrameSingleton.handlerValue += 1

        except ValueError as e:
            self.log.error(str(e))


class GUIFrame(wx.Frame):
    def __init__(self,parent,wxid,title):
        wx.Frame.__init__(self,parent,wxid,title, wx.DefaultPosition, (500, 500))
        self.InitUI()
        self.Centre
        self.Show(True)
        self.handlerValue = 0

    def InitUI(self):
        nb = wx.Notebook(self)
        tab1 = TabOne(nb, self)
        tab2 = TabTwo(nb)
        tab3 = TabThree(nb, self)
        tab1.shell = tab2.shell
        tab3.shell = tab2.shell
        nb.AddPage(tab1,"Local data source")
        nb.AddPage(tab3, "Experiment data source")
        nb.AddPage(tab2, "Scripting ")
        self.Bind(wx.EVT_CLOSE, self.onClose)

    def onClose(self, event):
        if GlobalOperations.YesNo(self, "Exit IMAS_VIZ ?", "Please confirm"):
            sys.exit(0)

class MyApp(wx.App):

    def OnInit(self):
        GlobalOperations.checkEnvSettings()
        frm = GUIFrame(None, -1, "IMAS_VIZ (version 1.0)")
        frm.Centre()
        frm.Show(True)
        return True

if __name__ == "__main__":
    app = MyApp(0)
    app.MainLoop()



